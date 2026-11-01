"""
backend/routers/__init__.py
Evidentia AI Modular Router Package.
"""

from routers.auth import router as auth_router
from routers.cases import router as cases_router
from routers.evidence import router as evidence_router
from routers.hypotheses import router as hypotheses_router
from routers.scoring import router as scoring_router
from routers.history import router as history_router
from routers.evaluation import router as evaluation_router
from routers.reports import router as reports_router
from routers.jobs import router as jobs_router
from routers.collaboration import router as collaboration_router
from routers.alerts import router as alerts_router
from routers.chargesheet import router as chargesheet_router
from routers.interviews import router as interviews_router
from routers.cross_case import router as cross_case_router
from routers.telecom_financial import router as telecom_financial_router
from routers.multilingual import router as multilingual_router
from routers.decision_quality import router as decision_quality_router
from routers.security_admin import router as security_admin_router
from routers.connectors import router as connectors_router
from routers.situation_board import router as situation_board_router
from routers.geospatial_timeline import router as geospatial_timeline_router
from routers.watchlists import router as watchlists_router
from routers.voice_notes import router as voice_notes_router
from routers.system_health import router as system_health_router
from routers.search import router as search_router
from routers.priorities import router as priorities_router
from routers.case_file import router as case_file_router
from routers.physical_evidence import router as physical_evidence_router
from routers.alibi import router as alibi_router
from routers.intake import router as intake_router
from routers.legal_glossary import router as legal_glossary_router
from routers.sync import router as sync_router

__all__ = [
    "auth_router",
    "cases_router",
    "evidence_router",
    "hypotheses_router",
    "scoring_router",
    "history_router",
    "evaluation_router",
    "reports_router",
    "jobs_router",
    "collaboration_router",
    "alerts_router",
    "chargesheet_router",
    "case_file_router",
    "interviews_router",
    "cross_case_router",
    "telecom_financial_router",
    "multilingual_router",
    "decision_quality_router",
    "security_admin_router",
    "connectors_router",
    "situation_board_router",
    "geospatial_timeline_router",
    "watchlists_router",
    "voice_notes_router",
    "system_health_router",
    "search_router",
    "priorities_router",
    "physical_evidence_router",
    "alibi_router",
    "intake_router",
    "legal_glossary_router",
    "sync_router",
]

