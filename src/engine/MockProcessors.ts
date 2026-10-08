/**
 * DEPRECATED: Mock processors have been removed and replaced with the Real AI Intelligence Pipeline.
 * Pipeline Architecture: React -> FastAPI -> Gemini -> PostgreSQL -> Real analysis results.
 * All forensic operations are processed by backend AI models (Gemini) and committed to the PostgreSQL database.
 */

import { Evidence, Entity, Contradiction, InvestigationTask } from '../types';
import { CaseStateEngine } from './CaseStateEngine';

export class MockProcessors {
  /**
   * @deprecated Replaced by IntelligencePipeline.processNewEvidence via FastAPI & Gemini.
   */
  static extractEntities(_evidence: Evidence): Entity[] {
    console.warn('[MockProcessors.extractEntities] Deprecated. Use IntelligencePipeline.processNewEvidence()');
    return [];
  }

  /**
   * @deprecated Replaced by IntelligencePipeline.processNewEvidence via FastAPI & Gemini.
   */
  static detectContradictions(_evidence: Evidence, _engine: CaseStateEngine): Contradiction[] {
    console.warn('[MockProcessors.detectContradictions] Deprecated. Use IntelligencePipeline.processNewEvidence()');
    return [];
  }

  /**
   * @deprecated Replaced by IntelligencePipeline.processNewEvidence via FastAPI & Gemini.
   */
  static generateTasks(_contradictions: Contradiction[], _evidence: Evidence): InvestigationTask[] {
    console.warn('[MockProcessors.generateTasks] Deprecated. Use IntelligencePipeline.processNewEvidence()');
    return [];
  }

  /**
   * @deprecated Replaced by IntelligencePipeline.processNewEvidence via FastAPI & Gemini.
   */
  static recalculateHypotheses(_evidence: Evidence, _engine: CaseStateEngine): void {
    console.warn('[MockProcessors.recalculateHypotheses] Deprecated. Use IntelligencePipeline.processNewEvidence()');
  }
}
