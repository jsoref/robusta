import logging
import uuid
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from pydantic import BaseModel

from ...integrations.scheduled.playbook_scheduler import PlaybooksScheduler
from ..reporting.base import Finding, BaseBlock


class EventType(Enum):
    KUBERNETES_TOPOLOGY_CHANGE = 1
    PROMETHEUS = 2
    MANUAL_TRIGGER = 3
    SCHEDULED_TRIGGER = 4


class ExecutionEventBaseParams(BaseModel):
    named_sinks: Optional[List[str]] = None


# Right now:
# 1. this is a dataclass but we need to make all fields optional in subclasses because of https://stackoverflow.com/questions/51575931/
# 2. this can't be a pydantic BaseModel because of various pydantic bugs (see https://github.com/samuelcolvin/pydantic/pull/2557)
# once the pydantic PR that addresses those issues is merged, this should be a pydantic class
# (note that we need to integrate with dataclasses because of hikaru)
@dataclass
class ExecutionBaseEvent:
    findings: List[Finding] = field(default_factory=lambda: [])
    named_sinks: Optional[List[str]] = None
    response: Dict[
        str, Any
    ] = None  # Response returned to caller. For admission or manual triggers for example
    stop_processing: bool = False
    _scheduler: Optional[PlaybooksScheduler] = None

    def set_scheduler(self, scheduler: PlaybooksScheduler):
        self._scheduler = scheduler

    def get_scheduler(self) -> PlaybooksScheduler:
        return self._scheduler

    def create_default_finding(self) -> Finding:
        """Create finding default fields according to the event type"""
        return Finding(
            title="Robusta notification", aggregation_key="Generic finding key"
        )

    def add_enrichment(
        self,
        enrichment_blocks: List[BaseBlock],
        annotations=None,
    ):

        if len(self.findings) == 0:
            self.findings.append(self.create_default_finding())

        self.findings[0].add_enrichment(enrichment_blocks, annotations)

    def add_finding(self, finding: Finding):
        if len(self.findings) > 0:
            logging.warning(f"Overriding active finding. new finding: {finding}")

        self.findings.insert(0, finding)

    @staticmethod
    def from_params(params: ExecutionEventBaseParams) -> Optional["ExecutionBaseEvent"]:
        return ExecutionBaseEvent(named_sinks=params.named_sinks)
