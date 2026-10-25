"""Compatibility shim for lab_api; portable pkt_core replaces Linux libgcrypt."""
from pathlib import Path
from pkt_core import decode_bytes as _decode, encode_bytes

def decode_bytes(data, fmt="pkt", **kwargs):
    return _decode(data, fmt).xml

def decode(path, fmt="pkt", **kwargs):
    return decode_bytes(Path(path).read_bytes(), fmt)

def encode(path, xml, fmt="pkt"):
    Path(path).write_bytes(encode_bytes(xml, fmt))
