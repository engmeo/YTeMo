"""Domain-neutral inference-time search algorithms."""
from dataclasses import dataclass, field
from math import isfinite, log, sqrt
from types import MappingProxyType
from typing import Callable, Iterable, Mapping, Sequence

@dataclass(frozen=True)
class SearchCandidate:
    candidate_id: str
    actions: tuple[str, ...]
    score: float
    metadata: Mapping[str, object] = field(default_factory=dict)
    def __post_init__(self):
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise ValueError("candidate_id must be non-empty")
        if not isinstance(self.actions, tuple) or any(not isinstance(a, str) or not a for a in self.actions):
            raise ValueError("actions must be a tuple of non-empty strings")
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)) or not isfinite(self.score):
            raise ValueError("score must be finite")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be a mapping")
        object.__setattr__(self, "score", float(self.score))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

@dataclass(frozen=True)
class SearchResult:
    candidates: tuple[SearchCandidate, ...]
    expanded_nodes: int
    truncated: bool

def best_of_n(candidates: Iterable[SearchCandidate], n: int) -> SearchResult:
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be positive")
    items = list(candidates)
    if any(not isinstance(c, SearchCandidate) for c in items):
        raise ValueError("all candidates must be SearchCandidate")
    ranked = sorted(items, key=lambda c: (-c.score, c.candidate_id))
    return SearchResult(tuple(ranked[:n]), len(items), len(items) > n)

def beam_search(initial_state: str, expand: Callable, score: Callable, *, beam_width=4, max_depth=8) -> SearchResult:
    if not isinstance(initial_state, str) or not initial_state:
        raise ValueError("initial_state must be non-empty")
    if isinstance(beam_width, bool) or not isinstance(beam_width, int) or beam_width < 1:
        raise ValueError("beam_width must be positive")
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    beam, found, expanded, truncated = [(initial_state, (), 0.0)], [], 0, False
    for depth in range(max_depth + 1):
        next_items = []
        for state, actions, cost in beam:
            value = score(state)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError("score callback must return finite number")
            found.append(SearchCandidate(f"beam-{depth}-{'-'.join(actions) or 'root'}", actions,
                float(value)-cost, {"state": state, "depth": depth, "path_cost": cost}))
            if depth == max_depth:
                continue
            expanded += 1
            for edge in expand(state):
                if not isinstance(edge, (tuple, list)) or len(edge) != 3:
                    raise ValueError("edge must be (action, next_state, cost)")
                action, nxt, edge_cost = edge
                if not isinstance(action, str) or not action or not isinstance(nxt, str) or not nxt:
                    raise ValueError("action and next_state must be non-empty")
                if isinstance(edge_cost, bool) or not isinstance(edge_cost, (int, float)) or not isfinite(edge_cost) or edge_cost < 0:
                    raise ValueError("edge cost must be finite and non-negative")
                next_items.append((nxt, actions+(action,), cost+float(edge_cost)))
        next_items.sort(key=lambda x: (-(float(score(x[0]))-x[2]), x[1], x[0]))
        truncated = truncated or len(next_items) > beam_width
        beam = next_items[:beam_width]
        if not beam:
            break
    unique = {}
    for c in found:
        key = (c.actions, c.metadata["state"])
        if key not in unique or c.score > unique[key].score:
            unique[key] = c
    ranked = sorted(unique.values(), key=lambda c: (-c.score, c.candidate_id))
    return SearchResult(tuple(ranked[:beam_width]), expanded, truncated)

@dataclass
class _Node:
    state: str
    parent: object = None
    action: str = ""
    visits: int = 0
    value: float = 0.0
    children: list = field(default_factory=list)
    untried: list = field(default_factory=list)

def monte_carlo_tree_search(initial_state: str, transitions: Mapping[str, Sequence],
                            terminal_utilities: Mapping[str, float], *, iterations=100,
                            exploration=1.41421356237, max_depth=20) -> SearchResult:
    if not isinstance(initial_state, str) or not initial_state:
        raise ValueError("initial_state must be non-empty")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 1:
        raise ValueError("iterations must be positive")
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 1:
        raise ValueError("max_depth must be positive")
    if isinstance(exploration, bool) or not isinstance(exploration, (int,float)) or not isfinite(exploration) or exploration < 0:
        raise ValueError("exploration must be finite and non-negative")
    utilities = {}
    for state, val in terminal_utilities.items():
        if not isinstance(state, str) or not state or isinstance(val, bool) or not isinstance(val,(int,float)) or not isfinite(val):
            raise ValueError("terminal utilities must be finite")
        utilities[state] = float(val)
    def edges(state):
        result = list(transitions.get(state, ()))
        for e in result:
            if not isinstance(e,(tuple,list)) or len(e)!=3:
                raise ValueError("transition must be (action,next_state,cost)")
            a,n,c=e
            if not isinstance(a,str) or not a or not isinstance(n,str) or not n or isinstance(c,bool) or not isinstance(c,(int,float)) or not isfinite(c) or c<0:
                raise ValueError("invalid transition")
        return result
    root = _Node(initial_state, untried=edges(initial_state))
    for _ in range(iterations):
        node, cost, depth = root, 0.0, 0
        while node.children and not node.untried and depth < max_depth:
            pv=max(1,node.visits)
            node=max(node.children,key=lambda c:(c.value/c.visits+float(exploration)*sqrt(log(pv)/c.visits),c.action,c.state))
            depth+=1
        if node.untried and depth < max_depth:
            a,n,c=node.untried.pop(0)
            child=_Node(n,parent=node,action=a,untried=edges(n))
            node.children.append(child)
            node,cost,depth=child,cost+float(c),depth+1
        state, steps = node.state, 0
        while state not in utilities and steps < max_depth-depth:
            choices=edges(state)
            if not choices: break
            _,n,c=sorted(choices,key=lambda e:(e[2],e[0],e[1]))[0]
            state,cost,steps=n,cost+float(c),steps+1
        reward=utilities.get(state,0.0)-cost
        while node is not None:
            node.visits+=1
            node.value+=reward
            node=node.parent
    candidates=[SearchCandidate(f"mcts-{c.action}-{c.state}",(c.action,),
        c.value/c.visits if c.visits else 0.0,{"state":c.state,"visits":c.visits}) for c in root.children]
    candidates.sort(key=lambda c:(-c.score,c.candidate_id))
    return SearchResult(tuple(candidates),iterations,bool(root.untried))
