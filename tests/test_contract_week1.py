"""Checks only static schemas and the RAM benchmark's non-Playwright helpers."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class ContractTests(unittest.TestCase):
    def test_schemas_include_required_fields(self):
        expectations = {
            "task_request": {"task_id","intent","idempotency_key","auth_context_ref","deadline_ms"},
            "tool_action": {"task_id","action_id","idempotency_key","required_capability","postcondition"},
            "tool_result": {"task_id","action_id","status","verified","evidence"}
        }
        for name,fields in expectations.items():
            obj=json.loads((ROOT/"contracts"/(name+".schema.json")).read_text(encoding="utf-8"))
            self.assertEqual(obj["type"],"object")
            self.assertEqual(obj["additionalProperties"],False)
            self.assertTrue(fields.issubset(set(obj["required"])))

    def test_benchmark_meminfo_parser(self):
        spec=importlib.util.spec_from_file_location("bench",ROOT/"scripts"/"bench_playwright_ram.py")
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"meminfo"
            path.write_text("MemTotal: 8000000 kB\nMemAvailable: 1572864 kB\n")
            self.assertEqual(mod.mem_available_mib(path),1536.0)

    def test_benchmark_does_not_claim_homologation(self):
        text=(ROOT/"scripts"/"bench_playwright_ram.py").read_text(encoding="utf-8")
        self.assertIn('"homologation_completed":False',text)
        self.assertIn('"wayland_tested":False',text)

if __name__=="__main__":
    unittest.main()
