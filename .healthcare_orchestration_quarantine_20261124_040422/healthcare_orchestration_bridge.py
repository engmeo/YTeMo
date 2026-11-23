
import inspect, types

try:
    from .healthcare_orchestration_extension import HealthcareOrchestrator
except ImportError:
    from healthcare_orchestration_extension import HealthcareOrchestrator

def _call(fn, payload):
    sig = inspect.signature(fn)
    params = sig.parameters
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return fn(**payload)
    kwargs = {k: v for k, v in payload.items()
              if k in params and params[k].kind in
              (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)}
    required = [p for p in params.values()
                if p.default is inspect.Parameter.empty and p.kind in
                (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                 inspect.Parameter.KEYWORD_ONLY)]
    if all(p.name in kwargs for p in required):
        return fn(**kwargs)
    if len(required) == 1:
        return fn(payload)
    return fn()

def _find(service, alternatives):
    for tokens in alternatives:
        for name in dir(service):
            if name.startswith("_") or not all(token in name.lower() for token in tokens):
                continue
            value = getattr(service, name, None)
            if callable(value):
                return value
    return None

def attach_orchestration(service):
    # Use the exact registry keys required by HealthcareOrchestrator.
    mapping = {
        "cost_intelligence": (("cost",),),
        "medication_support": (("medication",), ("medicine",)),
        "lab_result": (("lab",), ("laboratory",)),
        "bhyt_support": (("bhyt",), ("insurance",)),
    }
    specialists = {}
    for registered_name, alternatives in mapping.items():
        method = _find(service, alternatives)
        if method is not None:
            specialists[registered_name] = (lambda payload, fn=method: _call(fn, payload))

    orchestrator = HealthcareOrchestrator(specialists=specialists)

    def run_orchestrated(self, request):
        payload = dict(request) if isinstance(request, dict) else {
            "query": str(request), "text": str(request)
        }
        return orchestrator.run(payload)

    service.run_orchestrated = types.MethodType(run_orchestrated, service)
    service.orchestration_capabilities = tuple(sorted(specialists))
    return service
