"""Testa contratos e helpers do benchmark; nao valida o desktop real."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def import_bench():
    spec = importlib.util.spec_from_file_location("bench", ROOT/"scripts"/"bench_playwright_ram.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContractTests(unittest.TestCase):
    def test_schemas_include_required_fields(self):
        expectations = {
            "task_request": {"task_id","intent","idempotency_key","auth_context_ref","deadline_ms"},
            "tool_action": {"task_id","action_id","idempotency_key","required_capability","postcondition"},
            "tool_result": {"task_id","action_id","status","verified","evidence",
                            "observed_state","postcondition_check"}
        }
        for name, fields in expectations.items():
            obj = json.loads((ROOT/"contracts"/(name+".schema.json")).read_text(encoding="utf-8"))
            self.assertEqual(obj["type"], "object")
            self.assertFalse(obj["additionalProperties"])
            self.assertTrue(fields.issubset(set(obj["required"])))

    def test_observed_state_schema_rejects_unverified_success(self):
        from jsonschema import Draft202012Validator, FormatChecker
        schema = json.loads((ROOT/"contracts/tool_result.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        base = {
            "schema_version": "0.2",
            "task_id": "8be21031-80dd-42db-b194-2b96033e4fd6",
            "action_id": "f9d4f706-e866-4eec-ac96-e3c252441eb0",
            "status": "completed", "verified": True, "elapsed_ms": 77,
            "evidence": [{"kind":"window","ref":"win:firefox"}], "error_code": None,
            "observed_state": {
                "observed_at": "2026-11-11T18:00:00Z",
                "source": "at_spi",
                "target_ref": "window:firefox",
                "attributes": {"visible": True, "title": "Página de teste"}
            },
            "postcondition_check": {
                "check": "window_visible", "matched": True, "observation_fresh_ms": 21
            }
        }
        self.assertEqual(list(validator.iter_errors(base)), [])
        for change in (
            {"verified":False},
            {"observed_state": None},
            {"postcondition_check": None},
            {"postcondition_check":{"check":"window_visible","matched":False,
                                    "observation_fresh_ms":21}},
        ):
            sample = base | change
            self.assertTrue(list(validator.iter_errors(sample)), change)

    def test_benchmark_meminfo_parser(self):
        mod = import_bench()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"meminfo"
            path.write_text("MemTotal: 8000000 kB\nMemAvailable: 1572864 kB\n")
            self.assertEqual(mod.mem_available_mib(path), 1536.0)

    def test_stress_evaluator_distinguishes_smoke_from_gate(self):
        mod = import_bench()
        metrics = [
            {"kind":"metric","browser_pss_mib":300+(i % 2),"browser_rss_sum_mib":450,
             "mem_available_mib":3000,"open_tabs":i%2,"phase":"post_close"}
            for i in range(800)
        ]
        events = [
            {"kind":"event","event":"cycle_completed","elapsed_s":float(i*100)}
            for i in range(20)
        ] + [{"kind":"event","event":"test_finished","elapsed_s":1801}]
        blocked = {"image":25}
        passed=mod.evaluate(metrics, events, 1800, blocked, True, [])
        self.assertEqual(passed["result"], "pass")
        self.assertEqual(mod.evaluate(metrics, events, 120, blocked, True, [])["result"],
                         "inconclusive")
        metrics[-200:] = [dict(m, browser_pss_mib=500) for m in metrics[-200:]]
        failed=mod.evaluate(metrics, events, 1800, blocked, True, [])
        self.assertEqual(failed["result"], "fail")
        self.assertGreater(failed["post_close_pss_growth_mib"], 128)

    def test_evidence_never_claims_homologation(self):
        text=(ROOT/"scripts"/"bench_playwright_ram.py").read_text(encoding="utf-8")
        self.assertIn('"homologation_completed": False', text)
        self.assertIn('"wayland_tested": False', text)
        self.assertIn("MIN_GATE_SECONDS = 1800", text)

    def test_accessibility_fixture_is_async(self):
        html=(ROOT/"tests/fixtures/atspi_dynamic.html").read_text(encoding="utf-8")
        self.assertIn("setTimeout(makeButton, 1200)",html)
        self.assertIn('node.remove()',html)
        self.assertIn('role="status"',html)


if __name__ == "__main__":
    unittest.main()
