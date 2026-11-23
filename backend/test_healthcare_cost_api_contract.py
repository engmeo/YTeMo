import ast
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"


class HealthcareCostApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main_source = (BACKEND / "main.py").read_text(encoding="utf-8-sig")
        cls.frontend_source = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8-sig")
        cls.tree = ast.parse(cls.main_source)

    def test_request_schema_accepts_cost_items_and_bhyt(self):
        model = next(node for node in self.tree.body if isinstance(node, ast.ClassDef) and node.name == "HealthcareAnalysisRequest")
        fields = {node.target.id for node in model.body if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)}
        self.assertTrue({"document_text", "agent_keys", "cost_items", "bhyt"}.issubset(fields))

    def test_authenticated_route_calls_cost_report_builder(self):
        route = next(node for node in self.tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_healthcare_agents")
        args = [arg.arg for arg in route.args.args]
        self.assertIn("user", args)
        self.assertIn("Depends(get_current_user)", ast.unparse(route.args))
        body = ast.unparse(route)
        self.assertIn("build_cost_intelligence_report", body)
        self.assertIn("request.cost_items", body)
        self.assertIn("request.bhyt", body)
        self.assertIn("cost_intelligence_report", body)
        self.assertIn("source_quote", body)
        self.assertIn("source_quote not in request.document_text", body)

    def test_openapi_schema_exposes_optional_stt19_fields(self):
        schema = json.loads((ROOT / "docs" / "api" / "openapi.json").read_text(encoding="utf-8"))
        properties = schema["components"]["schemas"]["HealthcareAnalysisRequest"]["properties"]
        self.assertIn("cost_items", properties)
        self.assertIn("bhyt", properties)

    def test_frontend_submits_and_renders_cost_bhyt_report(self):
        for marker in ("costItemsJson", "bhytEligibleAmount", "bhytCoverageRate", "cost_intelligence_report", "payload.cost_items", "payload.bhyt"):
            self.assertIn(marker, self.frontend_source)
        after_session = self.frontend_source.split("const { data: { session } } = await supabase.auth.getSession();", 1)[1][:250]
        self.assertIn("syncHealthcareAccess", after_session)

    def test_frontend_has_one_initialize_call_after_healthcare_setup(self):
        calls = re.findall(r"(?m)^\s*initialize\(\);\s*$", self.frontend_source)
        self.assertEqual(len(calls), 1)
        self.assertLess(self.frontend_source.index("function syncHealthcareAccess"), self.frontend_source.rindex("initialize();"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
