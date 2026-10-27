"""Test a release ZIP in a fresh, isolated local installation (no GUI/network)."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import zipfile


def run_checks(archive, output, pt_install=None, offline_only=False):
    archive, output = Path(archive).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {"status": "running", "python": platform.python_version(), "os": platform.platform(),
              "zip_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "checks": [],
              "scope": "clean local extraction; no GUI, no independent machine or agent-host test",
              "runtime": "not_tested"}
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("PYTHON")}
    package_parent = output / "skill install ünicode" / ".agents" / "skills"
    workspace = output / "project with spaces 日本"
    cwd = output / "unrelated cwd"
    for directory in (package_parent, workspace, cwd):
        directory.mkdir(parents=True)

    def check(name, ok, detail=None):
        report["checks"].append({"name": name, "status": "passed" if ok else "failed", "detail": detail})
        if not ok:
            raise ValueError(name + ": " + str(detail))

    def command(name, args, code=0, json_output=False):
        result = subprocess.run([sys.executable, "-S", "-B", "-X", "utf8", str(script), *args],
                                cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", timeout=240)
        check(name, result.returncode == code, (result.stderr or result.stdout)[-1500:] if result.returncode != code else None)
        return json.loads(result.stdout) if json_output else result.stdout

    try:
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            check("zip-integrity", z.testzip() is None)
            for name in names:
                p = PurePosixPath(name)
                check_safe = (bool(p.parts) and not p.is_absolute() and ".." not in p.parts and "\\" not in name
                              and p.parts[0] == "cisco-pkt-builder" and ":" not in name)
                if not check_safe:
                    raise ValueError("Unsafe archive entry: " + name)
            check("source-only-release", not any(PurePosixPath(n).suffix in {".pkt", ".pka", ".xml", ".pyd", ".pyc"}
                  or ".cisco-pkt-cache" in n or "__pycache__" in n for n in names))
            z.extractall(package_parent)
        package = package_parent / "cisco-pkt-builder"
        script = package / "scripts" / "pkt.py"
        check("required-package-files", all((package / p).is_file() for p in
              ("SKILL.md", "agents/openai.yaml", "references/codex-gpt.md", "references/antigravity-gemini.md",
               "scripts/check_topology.py", "scripts/analyze_pkt.py", "vendor/yaml/__init__.py", "vendor/pkt_core/__init__.py")))
        original = {str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in package.rglob("*") if p.is_file()}
        for path in package.rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path), feature_version=(3, 10))
        check("python310-syntax-only", True, "Syntax compatibility is not execution on Python 3.10")
        check("no-inherited-cache", not (workspace / ".cisco-pkt-cache").exists())
        command("help-no-site-packages", ["help"])
        for preset in ("lan", "vlan", "ospf", "bgp"):
            shutil.copyfile(package / "examples" / (preset + ".yaml"), workspace / (preset + ".yaml"))
            command("validate-" + preset, ["validate", preset + ".yaml", "--workspace", str(workspace)])
        command("unknown-command-rejected", ["unknown"], code=2)
        command("output-escape-rejected", ["lan", "--workspace", str(workspace), "--out", "../outside"], code=2)
        command("missing-pt-explained", ["lan", "--workspace", str(workspace), "--pt-install", str(output / "no-pt")], code=2)
        check("offline-commands-no-cache", not (workspace / ".cisco-pkt-cache").exists())
        if offline_only:
            report["checks"].append({"name": "cold-bootstrap-build-check", "status": "not_tested"})
        else:
            for preset in ("bgp", "lan", "vlan", "ospf"):
                args = [preset, "--workspace", str(workspace)]
                if pt_install:
                    args += ["--pt-install", str(Path(pt_install).resolve())]
                built = command("build-" + preset, args, json_output=True)
                check("build-file-" + preset, Path(built["pkt"]).is_file())
                audited = command("check-" + preset, ["check", "hasil/" + preset, "--workspace", str(workspace)], json_output=True)
                expected = "passed_static" if preset in ("lan", "bgp") else "partial"
                check("audit-status-" + preset, audited["status"] == expected, audited["status"])
                check("no-fabricated-runtime-" + preset, set(audited["runtime"].values()) == {"not_tested"})
            command("existing-output-protected", ["lan", "--workspace", str(workspace), "--out", "hasil/lan"], code=2)
            command("codec-decode", ["decode", "hasil/bgp/lab-bgp.pkt", "decoded.xml", "--workspace", str(workspace)])
            command("codec-encode", ["encode", "decoded.xml", "encoded.pkt", "--workspace", str(workspace)])
            check("codec-byte-roundtrip", (workspace / "encoded.pkt").read_bytes() == (workspace / "hasil/bgp/lab-bgp.pkt").read_bytes())
        after = {str(p.relative_to(package)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in package.rglob("*") if p.is_file()}
        check("installed-package-unchanged", original == after)
        check("unrelated-cwd-clean", not list(cwd.iterdir()))
        report["status"] = "passed"
    except (ValueError, OSError, SyntaxError, subprocess.TimeoutExpired, zipfile.BadZipFile) as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
    (output / "install-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive")
    p.add_argument("--out", required=True, help="Fresh directory for extracted test installation and report")
    p.add_argument("--pt-install")
    p.add_argument("--offline-only", action="store_true", help="Skip bootstrap/build when PT is unavailable")
    a = p.parse_args()
    try:
        report = run_checks(a.archive, a.out, a.pt_install, a.offline_only)
        print(json.dumps({"status": report["status"], "checks": len(report["checks"]),
                          "report": str(Path(a.out).resolve() / "install-report.json"), "error": report.get("error")}))
        return 0 if report["status"] == "passed" else 2
    except (ValueError, OSError) as exc:
        p.exit(2, f"Install test failed: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
