"""Dispatcher for the /pkt chat command protocol. Never executes shell strings."""
import argparse
import subprocess
import sys
from common import PACKAGE, local_path

HELP = """Perintah chat setelah skill dimuat:
/pkt help                         Daftar perintah
/pkt mode <profil>                Agent memilih auto/codex-gpt/antigravity-gemini
/pkt lan                          1 router, 1 switch, 2 PC
/pkt vlan                         2 switch, VLAN 10/20 dan trunk
/pkt ospf                         2 router, 2 switch, 4 PC
/pkt bgp                          3 router serial, AS 100/200/300, 7 PC
/pkt buat <deskripsi>              Agent membuat spec lalu build
/pkt edit <spec> <perubahan>       Agent menyalin/mengedit spec lalu build baru
/pkt build <spec>                  Build YAML/JSON yang sudah ada
/pkt validate <spec>               Periksa spec tanpa Packet Tracer
/pkt check <folder-hasil>          Audit CLI/file .pkt offline, tanpa kontrol GUI
/pkt decode <input.pkt> <out.xml>  Decode lokal
/pkt encode <input.xml> <out.pkt>  Validasi dan encode lokal

CLI: python <skill>/scripts/pkt.py lan --workspace PATH [--out hasil/lan]
Awalan /pkt opsional pada CLI. Gunakan tanda kutip untuk path dengan spasi.
Build: --out, --workspace, --pt-install. Validate: --xml, --workspace.
Encode/decode: --workspace. Tanpa --out, build memilih hasil/<nama>-N
jika folder sebelumnya sudah ada. File lama tidak ditimpa.
buat/edit/mode adalah instruksi agent, bukan parser bahasa natural di Python.
Protokol ini tidak mendaftarkan menu slash/autocomplete bawaan aplikasi.
"""

def next_output(workspace, stem):
    base = f"hasil/{stem}"
    candidate, n = base, 2
    while local_path(candidate, workspace).exists():
        candidate = f"{base}-{n}"
        n += 1
    return candidate

def parser():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("help", help="Daftar perintah chat")
    for name in ("lan", "vlan", "ospf", "bgp", "build"):
        cmd = commands.add_parser(name)
        if name == "build":
            cmd.add_argument("spec")
        cmd.add_argument("--workspace", default=".")
        cmd.add_argument("--out")
        cmd.add_argument("--pt-install")
    cmd = commands.add_parser("validate")
    cmd.add_argument("spec")
    cmd.add_argument("--workspace", default=".")
    cmd.add_argument("--xml", action="store_true")
    cmd = commands.add_parser("check")
    cmd.add_argument("folder")
    cmd.add_argument("--workspace", default=".")
    for name in ("decode", "encode"):
        cmd = commands.add_parser(name)
        cmd.add_argument("input")
        cmd.add_argument("output")
        cmd.add_argument("--workspace", default=".")
    return p

def command_args(a):
    scripts = PACKAGE / "scripts"
    if a.command in ("lan", "vlan", "ospf", "bgp", "build"):
        out = a.out if a.out is not None else next_output(a.workspace, a.command)
        local_path(out, a.workspace)
        args = [sys.executable, str(scripts / "build_topology.py")]
        args += [a.spec] if a.command == "build" else ["--preset", a.command]
        args += ["--out", out, "--workspace", a.workspace, "--json-report"]
        if a.pt_install:
            args += ["--pt-install", a.pt_install]
        return args
    if a.command == "validate":
        args = [sys.executable, str(scripts / "validate.py"), a.spec, "--workspace", a.workspace]
        return args + (["--xml"] if a.xml else [])
    if a.command == "check":
        return [sys.executable, str(scripts / "check_topology.py"), a.folder, "--workspace", a.workspace]
    return [sys.executable, str(scripts / "pkt_codec.py"), a.command,
            a.input, a.output, "--workspace", a.workspace]

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "/pkt":
        argv.pop(0)
    if not argv:
        argv = ["help"]
    p = parser()
    a = p.parse_args(argv)
    if a.command == "help":
        print(HELP)
        return 0
    try:
        return subprocess.run(command_args(a), shell=False).returncode
    except (ValueError, OSError) as exc:
        p.exit(2, f"Perintah gagal: {exc}\n")

if __name__ == "__main__":
    sys.exit(main())
