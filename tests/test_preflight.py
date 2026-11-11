"""Testes do diagnóstico — não do núcleo Adam."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

PATH=Path(__file__).resolve().parents[1]/"scripts"/"preflight.py"
spec=importlib.util.spec_from_file_location("adam_preflight",PATH)
preflight=importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)

class PreflightTests(unittest.TestCase):
    def test_memory_parse(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"meminfo"
            file.write_text("MemTotal: 8388608 kB\nMemAvailable: 4194304 kB\nSwapTotal: 0 kB\n")
            info=preflight.meminfo_gib(file)
            self.assertEqual(info["MemTotal_gib"],8)
            self.assertEqual(info["MemAvailable_gib"],4)

    def test_secret_is_never_printed(self):
        secret="NEVER_PRINT_ME"
        info=preflight.check_environment({"XDG_SESSION_TYPE":"wayland","XDG_CURRENT_DESKTOP":"GNOME","ELEVENLABS_API_KEY":secret})
        self.assertTrue(info["elevenlabs_key_configured"])
        self.assertNotIn(secret,str(info))

    def test_tts_local_denied_for_alpha(self):
        info=preflight.check_environment({"ADAM_TTS_LOCAL_ENABLED":"true"})
        self.assertTrue(any("TTS local" in x for x in info["warnings"]))

    def test_no_false_homologation(self):
        info=preflight.check_environment({"XDG_SESSION_TYPE":"wayland","XDG_CURRENT_DESKTOP":"GNOME"})
        self.assertFalse(info["alpha_homologation_complete"])
        self.assertFalse(info["alpha_requirements_implemented"])

if __name__=="__main__":
    unittest.main()
