"""Offline .pkt/XML codec with authenticated decode and no overwrite."""
import argparse
import xml.etree.ElementTree as ET
from common import local_path, write_new
from pkt_core import decode_bytes, encode_bytes
from pkt_core.errors import PacketTracerError
from validate import validate_xml

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["encode", "decode"])
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--workspace", default=".")
    a = p.parse_args()
    try:
        src = local_path(a.input, a.workspace, exists=True)
        dst = local_path(a.output, a.workspace)
        if src.suffix.lower() == ".pka" or dst.suffix.lower() == ".pka":
            raise ValueError(".pka di luar scope MVP")
        if a.mode == "encode":
            xml = src.read_bytes()
            validate_xml(xml)
            data = encode_bytes(xml, "pkt")
            if decode_bytes(data, "pkt").xml != xml:
                raise ValueError("Round-trip gagal")
        else:
            data = decode_bytes(src.read_bytes(), "pkt").xml
            root = ET.fromstring(data)
            if root.tag != "PACKETTRACER5":
                raise ValueError("Hanya .pkt didukung")
        write_new(dst, data)
        print(dst)
    except (ValueError, OSError, ET.ParseError, PacketTracerError) as exc:
        p.exit(2, f"Codec gagal: {exc}\n")

if __name__ == "__main__":
    main()
