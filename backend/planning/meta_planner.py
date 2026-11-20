"""Adaptive inference-time compute allocation."""
from dataclasses import dataclass
from math import isfinite
from typing import Mapping

@dataclass(frozen=True)
class PlanningContext:
    branching_factor: int
    estimated_depth: int
    risk_level: float = 0.0
    compute_budget: int = 100
    def __post_init__(self):
        for name in ("branching_factor","estimated_depth","compute_budget"):
            v=getattr(self,name); minimum=0 if name in ("estimated_depth", "compute_budget") else 1
            if isinstance(v,bool) or not isinstance(v,int) or v<minimum:
                raise ValueError(f"{name} invalid")
        if isinstance(self.risk_level,bool) or not isinstance(self.risk_level,(int,float)) or not isfinite(self.risk_level) or not 0<=self.risk_level<=1:
            raise ValueError("risk_level must be between 0 and 1")

@dataclass(frozen=True)
class ComputeAllocation:
    strategy: str
    budget: int
    rationale: tuple[str,...]

def allocate_planning_compute(context: PlanningContext) -> ComputeAllocation:
    if not isinstance(context,PlanningContext): raise ValueError("context must be PlanningContext")
    if context.compute_budget==0: return ComputeAllocation("greedy",0,("No compute budget available",))
    complexity=context.branching_factor*max(1,context.estimated_depth)
    if context.risk_level>=.75: strategy,reason="mcts","Elevated risk warrants broader tree exploration"
    elif complexity>=100 and context.compute_budget>=20: strategy,reason="beam","Large search space warrants bounded-width search"
    elif context.branching_factor>=2 and context.compute_budget>=10: strategy,reason="best_of_n","Multiple alternatives warrant comparison"
    else: strategy,reason="greedy","Small search space or limited budget"
    return ComputeAllocation(strategy,min(context.compute_budget,max(1,complexity),1000),(reason,))

def compare_planning_strategies(scores: Mapping[str,float]) -> str:
    if not scores: raise ValueError("scores must be non-empty")
    checked={}
    for name,val in scores.items():
        if not isinstance(name,str) or not name.strip() or isinstance(val,bool) or not isinstance(val,(int,float)) or not isfinite(val):
            raise ValueError("strategy names and finite scores required")
        checked[name]=float(val)
    return max(checked,key=lambda n:(checked[n],n))
