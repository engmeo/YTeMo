"""Robotics policy kept outside the universal Planning Core."""
from dataclasses import dataclass
from ...contracts import DomainPolicy

@dataclass(frozen=True)
class RoboticsDomainAdapter:
    domain_id: str = "robotics"
    def get_policy(self) -> DomainPolicy:
        return DomainPolicy(self.domain_id)
