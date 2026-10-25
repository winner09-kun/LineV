"""Shared, offline path and input handling."""
from pathlib import Path
import json
import sys

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "vendor"))

def local_path(value, workspace, *, exists=False):
    root = Path(workspace).resolve()
    p = Path(value)
    p = (root / p).resolve() if not p.is_absolute() else p.resolve()
    if not p.is_relative_to(root):
        raise ValueError(f"Path di luar workspace: {value}")
    if exists and not p.is_file():
        raise ValueError(f"File tidak ditemukan: {p}")
    return p

def load_spec(path):
    text = path.read_text(encoding="utf-8-sig")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml
        except ImportError as exc:
            raise ValueError("YAML memerlukan PyYAML; instal requirements.txt, atau gunakan JSON.") from exc
        class UniqueLoader(yaml.SafeLoader):
            pass
        def mapping(loader, node):
            result = {}
            for key_node, value_node in node.value:
                key = loader.construct_object(key_node)
                if key in result:
                    raise ValueError(f"Kunci YAML ganda: {key}")
                result[key] = loader.construct_object(value_node)
            return result
        UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
        try:
            return yaml.load(text, Loader=UniqueLoader)
        except yaml.YAMLError as exc:
            raise ValueError(f"Sintaks YAML tidak valid: {exc}") from exc

def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(data)
