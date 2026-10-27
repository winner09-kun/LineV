import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from package_release import release_files
from verify_install import run_checks


class InstallTests(unittest.TestCase):
    def setUp(self):
        (ROOT.parent / "qa").mkdir(exist_ok=True)

    def test_release_without_site_packages_or_cache(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent / "qa") as tmp:
            archive = Path(tmp) / "release.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
                for source, target in release_files():
                    z.write(source, target.as_posix())
            report = run_checks(archive, Path(tmp) / "fresh", offline_only=True)
            self.assertEqual(report["status"], "passed", report.get("error"))
            self.assertEqual(report["runtime"], "not_tested")
            self.assertEqual(json.loads((Path(tmp) / "fresh/install-report.json").read_text(encoding="utf-8"))["status"], "passed")

    def test_unsafe_archive_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent / "qa") as tmp:
            archive = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("../escaped.txt", "bad")
            report = run_checks(archive, Path(tmp) / "fresh", offline_only=True)
            self.assertEqual(report["status"], "failed")
            self.assertIn("Unsafe archive", report["error"])
            self.assertFalse((Path(tmp) / "escaped.txt").exists())

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent / "qa") as tmp:
            with self.assertRaises(FileExistsError):
                run_checks(Path(tmp) / "absent.zip", tmp, offline_only=True)


if __name__ == "__main__":
    unittest.main()
