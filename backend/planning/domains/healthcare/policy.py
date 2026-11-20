"""Healthcare policy kept outside the universal Planning Core."""
from dataclasses import dataclass
from ...contracts import DomainPolicy
from ...models import StepRisk

@dataclass(frozen=True)
class HealthcareDomainAdapter:
    domain_id: str = "healthcare"
    def get_policy(self) -> DomainPolicy:
        return DomainPolicy(self.domain_id, frozenset({StepRisk.HIGH, StepRisk.CRITICAL}))
