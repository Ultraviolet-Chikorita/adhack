from __future__ import annotations

from collections import defaultdict
from itertools import count

from guardrailbidder.models import (
    ApprovalItem,
    ApprovalStatus,
    BidDecision,
    CreativeJudgement,
    CreativeVariant,
    PlacementMetrics,
    TraceEvent,
)


class AppState:
    def __init__(self) -> None:
        self._id_counter = count(1)
        self.trace_events: list[TraceEvent] = []
        self.bids: list[BidDecision] = []
        self.creatives: dict[str, CreativeVariant] = {}
        self.judgements: dict[str, CreativeJudgement] = {}
        self.approvals: dict[str, ApprovalItem] = {}
        self.placements: dict[str, PlacementMetrics] = defaultdict(
            lambda: PlacementMetrics(placement_id="unknown")
        )

    def next_id(self, prefix: str) -> str:
        return f"{prefix}-{next(self._id_counter)}"

    def reset(self) -> None:
        self._id_counter = count(1)
        self.trace_events = []
        self.bids = []
        self.creatives = {}
        self.judgements = {}
        self.approvals = {}
        self.placements = defaultdict(lambda: PlacementMetrics(placement_id="unknown"))

    def add_trace(self, event_type: str, message: str, payload: dict) -> TraceEvent:
        event = TraceEvent(
            id=self.next_id("trace"),
            event_type=event_type,
            message=message,
            payload=payload,
        )
        self.trace_events.append(event)
        return event

    def add_approval(self, item: ApprovalItem) -> None:
        self.approvals[item.id] = item

    def pending_approvals(self) -> list[ApprovalItem]:
        return [a for a in self.approvals.values() if a.status == ApprovalStatus.PENDING]

    def get_or_create_placement(self, placement_id: str) -> PlacementMetrics:
        existing = self.placements.get(placement_id)
        if existing is not None:
            return existing
        placement = PlacementMetrics(placement_id=placement_id)
        self.placements[placement_id] = placement
        return placement


app_state = AppState()
