import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pkt

class CommandTests(unittest.TestCase):
    def setUp(self):
        (ROOT.parent / "qa").mkdir(exist_ok=True)

    def test_help_does_not_execute(self):
        with patch.object(pkt.subprocess, "run") as run, contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(pkt.main(["/pkt"]), 0)
            self.assertIn("/pkt buat", out.getvalue())
            run.assert_not_called()

    def test_presets_preserve_options(self):
        for name in ("lan", "vlan", "ospf"):
            a = pkt.parser().parse_args([name, "--workspace", ".", "--out", "hasil/custom", "--pt-install", "C:/Program Files/PT"])
            cmd = pkt.command_args(a)
            self.assertEqual(cmd[cmd.index("--preset") + 1], name)
            self.assertEqual(cmd[cmd.index("--pt-install") + 1], "C:/Program Files/PT")
            self.assertIn("--json-report", cmd)

    def test_existing_output_gets_new_name(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent / "qa") as tmp:
            (Path(tmp) / "hasil/lan").mkdir(parents=True)
            (Path(tmp) / "hasil/lan-2").write_text("occupied")
            self.assertEqual(pkt.next_output(tmp, "lan"), "hasil/lan-3")

    def test_arguments_are_not_shell_code(self):
        value = "spec folder/lab;echo injected.yaml"
        with patch.object(pkt.subprocess, "run", return_value=subprocess.CompletedProcess([], 2)) as run:
            self.assertEqual(pkt.main(["/pkt", "validate", value]), 2)
            self.assertIn(value, run.call_args.args[0])
            self.assertIs(run.call_args.kwargs["shell"], False)

    def test_unknown_command_has_no_side_effect(self):
        with patch.object(pkt.subprocess, "run") as run, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                pkt.main(["/pkt", "delete"])
            self.assertEqual(error.exception.code, 2)
            run.assert_not_called()

    def test_child_preserves_isolation_and_uses_utf8(self):
        from types import SimpleNamespace
        with patch.object(pkt.sys, "flags", SimpleNamespace(no_site=1)), \
             patch.object(pkt.sys, "dont_write_bytecode", True), \
             patch.object(pkt.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(pkt.main(["validate", "lab.yaml"]), 0)
            self.assertEqual(run.call_args.args[0][1:5], ["-X", "utf8", "-S", "-B"])

    def test_validate_dispatch_integration(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/pkt.py"), "/pkt", "validate",
            "examples/lan.yaml", "--workspace", str(ROOT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "Valid")

    def test_decode_mapping_and_path_guard(self):
        a = pkt.parser().parse_args(["decode", "in.pkt", "out.xml"])
        cmd = pkt.command_args(a)
        self.assertEqual(cmd[2:5], ["decode", "in.pkt", "out.xml"])
        a = pkt.parser().parse_args(["lan", "--out", "../outside"])
        with self.assertRaisesRegex(ValueError, "di luar"):
            pkt.command_args(a)

if __name__ == "__main__":
    unittest.main()
