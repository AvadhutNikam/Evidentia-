"""
backend/worker.py
=================
Standalone Background Worker Process for Evidentia-AI.
Polls the job queue, claims queued jobs atomically, executes the 7-stage forensic pipeline,
sweeps abandoned/stuck jobs, and manages concurrency and graceful shutdown.

Usage:
    python backend/worker.py
"""

import sys
import time
import signal
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from jobs.queue import claim_next_job, recover_stuck_jobs
from jobs.pipeline import execute_evidence_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (Worker) %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("evidentia.worker")

# Worker Configuration
POLL_INTERVAL_SECONDS = 1.5
STUCK_CHECK_INTERVAL_SECONDS = 30.0
MAX_CONCURRENT_JOBS = 2

# Global shutdown flag
_SHUTDOWN_REQUESTED = False


def _signal_handler(signum, frame):
    global _SHUTDOWN_REQUESTED
    logger.info("Termination signal received. Gracefully finishing in-flight jobs...")
    _SHUTDOWN_REQUESTED = True


def _run_single_job(job_id: int):
    """Executes a single job in its own isolated database session."""
    db = SessionLocal()
    try:
        logger.info(f"Starting execution of Job #{job_id}")
        success = execute_evidence_pipeline(job_id, db)
        if success:
            logger.info(f"Job #{job_id} completed successfully.")
        else:
            logger.warning(f"Job #{job_id} terminated without success (cancelled or failed).")
    except Exception as e:
        logger.error(f"Unhandled exception while processing Job #{job_id}: {e}", exc_info=True)
    finally:
        db.close()


def run_worker_loop(
    max_workers: int = MAX_CONCURRENT_JOBS,
    stop_event=None,
    register_signals: bool = True
):
    """Main worker process loop."""
    global _SHUTDOWN_REQUESTED
    if register_signals:
        try:
            import threading
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGINT, _signal_handler)
                signal.signal(signal.SIGTERM, _signal_handler)
        except (ValueError, AttributeError):
            pass

    logger.info(f"Evidentia-AI Background Worker started. Concurrency: {max_workers} jobs.")
    executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="JobWorker")

    last_stuck_sweep = 0.0
    last_alert_sweep = 0.0

    try:
        # Run startup check to catch any missed overnight checks immediately
        startup_db = SessionLocal()
        try:
            from alerts_engine import run_scheduled_alert_checks
            logger.info("Running initial startup statutory deadline and alert checks...")
            run_scheduled_alert_checks(startup_db)
        except Exception as e:
            logger.warning(f"Startup alert check notice: {e}")
        finally:
            startup_db.close()

        while not _SHUTDOWN_REQUESTED and not (stop_event and stop_event.is_set()):
            now_ts = time.time()

            # Periodic statutory deadlines and alert rules sweep (every 60s)
            if now_ts - last_alert_sweep > 60.0:
                alert_db = SessionLocal()
                try:
                    from alerts_engine import run_scheduled_alert_checks, process_alert_emails
                    run_scheduled_alert_checks(alert_db)
                    process_alert_emails(alert_db)
                except Exception as e:
                    logger.error(f"Error during periodic alerts sweep: {e}")
                finally:
                    alert_db.close()
                last_alert_sweep = now_ts

            # Sweep for stuck/abandoned jobs periodically
            if now_ts - last_stuck_sweep > STUCK_CHECK_INTERVAL_SECONDS:
                sweep_db = SessionLocal()
                try:
                    recovered = recover_stuck_jobs(sweep_db, timeout_seconds=120)
                    if recovered > 0:
                        logger.info(f"Recovered {recovered} stuck/abandoned job(s).")
                except Exception as e:
                    logger.error(f"Error during stuck job sweep: {e}")
                finally:
                    sweep_db.close()
                last_stuck_sweep = now_ts

            # Attempt to claim next job
            claim_db = SessionLocal()
            claimed_job = None
            try:
                claimed_job = claim_next_job(claim_db)
            except Exception as e:
                logger.error(f"Error checking job queue: {e}")
            finally:
                claim_db.close()

            if claimed_job:
                # Dispatch to thread pool
                executor.submit(_run_single_job, claimed_job.id)
            else:
                # Queue empty, wait before polling again
                time.sleep(POLL_INTERVAL_SECONDS)

    finally:
        logger.info("Worker shutting down. Waiting for active jobs to finish...")
        executor.shutdown(wait=True)
        logger.info("Worker shutdown complete. Clean exit.")


def start_embedded_worker(max_workers: int = 1):
    """
    Starts an embedded background worker thread within the ASGI process as a fail-safe.
    Ensures queued forensic processing jobs never hang when running in single-process mode.
    Returns (thread, stop_event).
    """
    import threading
    stop_event = threading.Event()
    worker_thread = threading.Thread(
        target=run_worker_loop,
        kwargs={"max_workers": max_workers, "stop_event": stop_event, "register_signals": False},
        daemon=True,
        name="EmbeddedEvidentiaWorker"
    )
    worker_thread.start()
    return worker_thread, stop_event


if __name__ == "__main__":
    run_worker_loop()

