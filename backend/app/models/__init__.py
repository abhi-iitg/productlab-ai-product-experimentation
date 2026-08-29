"""SQLAlchemy domain models.

Importing this package registers every model's table on `Base.metadata`,
which Alembic autogeneration and `Base.metadata.create_all()` both rely on.
"""

from app.models.decision_memo import DecisionMemo, Recommendation
from app.models.evidence_item import EvidenceItem, EvidenceType
from app.models.experiment import Experiment, ExperimentStatus, experiment_personas
from app.models.human_feedback import HumanFeedback, HumanFeedbackSourceMethod
from app.models.insight import Insight, InsightCategory, VariantScope
from app.models.persona import ConfidenceLevel, Persona
from app.models.project import Project, ProjectStatus
from app.models.simulation_run import FailureType, SimulationRun, SimulationRunStatus, TaskOutcome
from app.models.variant import Variant, VariantKey

__all__ = [
    "ConfidenceLevel",
    "DecisionMemo",
    "EvidenceItem",
    "EvidenceType",
    "Experiment",
    "ExperimentStatus",
    "FailureType",
    "HumanFeedback",
    "HumanFeedbackSourceMethod",
    "Insight",
    "InsightCategory",
    "Persona",
    "Project",
    "ProjectStatus",
    "Recommendation",
    "SimulationRun",
    "SimulationRunStatus",
    "TaskOutcome",
    "Variant",
    "VariantKey",
    "VariantScope",
    "experiment_personas",
]
