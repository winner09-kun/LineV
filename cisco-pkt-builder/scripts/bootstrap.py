"""Prepare private local templates from an installed Packet Tracer, without network."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET
from common import local_path
from pkt_core import decode_bytes
from pkt_core.errors import PacketTracerError

MODELS = ("2911", "2960-24TT", "PC-PT", "Server-PT")
FILES = tuple(m + ".xml" for m in MODELS) + ("network_seed.xml",)
CACHE_SCHEMA = 2

def compatible_seed(document):
    """Lab writes save-ref-id links; do not mix them with legacy index-based seeds.

    The VERSION tag is insufficient: bundled files with the same version use
    different reference styles. Require evidence in devices AND actual links.
    """
    devices = document.findall("NETWORK/DEVICES/DEVICE")
    refs = [d.findtext("ENGINE/SAVE_REF_ID", "") for d in devices]
    links = document.findall("NETWORK/LINKS/LINK/CABLE")
    return (bool(devices) and bool(links) and len(set(refs)) == len(refs)
            and all(r.startswith("save-ref-id:") for r in refs)
            and all(c.findtext(side) in refs for c in links for side in ("FROM", "TO")))

def installation(explicit=None):
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not (p / "saves").is_dir():
            raise ValueError("--pt-install harus folder instalasi Packet Tracer yang memiliki saves/")
        return p
    candidates = []
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(variable)
        if base:
            candidates.extend(Path(base).glob("Cisco Packet Tracer*"))
    candidates += [Path("/opt/pt"), Path("/Applications/Cisco Packet Tracer.app/Contents")]
    for p in sorted(candidates, key=lambda x: str(x), reverse=True):
        if (p / "saves").is_dir():
            return p.resolve()
    raise ValueError("Instalasi Packet Tracer tidak ditemukan. Instal melalui Cisco atau berikan --pt-install PATH; pengguna tidak perlu menyediakan template.")

def cached(directory, serial=False):
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("schema") != CACHE_SCHEMA:
            return False
        required = FILES + (("HWIC-2T.xml",) if serial else ())
        return all(hashlib.sha256((directory / name).read_bytes()).hexdigest() == manifest["sha256"][name] for name in required)
    except (OSError, ValueError, KeyError, TypeError):
        return False

def prepare(workspace=".", pt_install=None, *, max_files=500, timeout=120, serial=False):
    directory = local_path(".cisco-pkt-cache", workspace)
    if cached(directory, serial):
        return directory
    root = installation(pt_install)
    # Read only the application's bundled samples, never Downloads/user labs.
    paths = sorted((p for p in (root / "saves").rglob("*.pkt") if p.is_file()), key=lambda p: (p.stat().st_size, str(p)))
    models, sources, seed, module = {}, {}, None, None
    version = None
    deadline = time.monotonic() + timeout
    scanned = 0
    for path in paths[:max_files]:
        if time.monotonic() > deadline:
            break
        if path.stat().st_size > 4_000_000:
            continue
        scanned += 1
        try:
            xml = decode_bytes(path.read_bytes(), "pkt").xml
            document = ET.fromstring(xml)
            if document.tag != "PACKETTRACER5":
                continue
            devices = document.findall("NETWORK/DEVICES/DEVICE")
            if serial and module is None:
                for slot in document.iter("SLOT"):
                    if (slot.findtext("TYPE") == "eInterfaceCard"
                            and slot.findtext("MODULE/MODEL") == "HWIC-2T"
                            and len(slot.findall("MODULE/PORT")) == 2
                            and all(p.findtext("TYPE") == "eSmartSerial" for p in slot.findall("MODULE/PORT"))):
                        module = ET.tostring(slot, encoding="utf-8")
                        sources["HWIC-2T"] = str(path.relative_to(root))
                        break
            for device in devices:
                kind = device.find("ENGINE/TYPE")
                model = kind.get("model") if kind is not None else None
                if model in MODELS and model not in models:
                    models[model] = ET.tostring(device, encoding="utf-8")
                    sources[model] = str(path.relative_to(root))
            if seed is None and document.find("PHYSICALWORKSPACE") is not None and compatible_seed(document):
                # Verify the physical workspace using the same reader as the builder.
                # Lab needs a file; use a private staging file inside the workspace.
                from lab_api import Lab
                directory.mkdir(parents=True, exist_ok=True)
                stage = local_path(directory / "seed-candidate.xml", workspace)
                stage.write_bytes(xml)
                try:
                    Lab(str(stage), {})
                except (ValueError, AttributeError, TypeError):
                    continue
                seed = xml
                version = document.findtext("VERSION")
                sources["seed"] = str(path.relative_to(root))
            if len(models) == len(MODELS) and seed is not None and (not serial or module is not None):
                break
        except (PacketTracerError, ET.ParseError, OSError, ValueError):
            continue
    missing = [m for m in MODELS if m not in models]
    if serial and module is None:
        missing.append("HWIC-2T")
    if seed is None:
        missing.append("physical workspace seed dengan link save-ref-id")
    if missing:
        raise ValueError(f"Bootstrap belum lengkap setelah {scanned} sampel: {', '.join(missing)}. Gunakan instalasi PT dengan sampel model tersebut; tidak ada template tebakan yang dibuat.")
    payload = {m + ".xml": data for m, data in models.items()}
    payload["network_seed.xml"] = seed
    if module is not None:
        payload["HWIC-2T.xml"] = module
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in payload.items():
        local_path(directory / name, workspace).write_bytes(data)
    manifest = {"schema": CACHE_SCHEMA, "source": "installed-packet-tracer-samples", "version": version,
                "files_scanned": scanned, "sources": sources,
                "sha256": {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()}}
    local_path(directory / "manifest.json", workspace).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return directory

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", default=".")
    p.add_argument("--pt-install")
    a = p.parse_args()
    try:
        result = prepare(a.workspace, a.pt_install)
        print(json.dumps({"status": "ready", "cache": str(result), "scope": "local-only"}))
    except (OSError, ValueError) as exc:
        p.exit(2, f"Bootstrap gagal: {exc}\n")

if __name__ == "__main__":
    main()
