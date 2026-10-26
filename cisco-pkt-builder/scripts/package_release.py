"""Package source only; never include local Cisco XML, cache or generated labs."""
import argparse
from pathlib import Path
import zipfile
from common import PACKAGE, local_path

def release_files():
    allowed_dirs = {"scripts", "vendor", "tests", "references", "agents"}
    allowed_root = {"LICENSE", "requirements.txt"}
    for path in sorted(PACKAGE.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(PACKAGE)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyd", ".xml", ".pkt", ".pka", ".zip"}:
            continue
        if (len(relative.parts) == 1 and (path.suffix == ".md" or path.name in allowed_root)
            or relative.parts[0] in allowed_dirs
            or len(relative.parts) == 2 and relative.parts[0] == "examples" and path.suffix == ".yaml"):
            yield path, Path(PACKAGE.name) / relative

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    p.add_argument("--workspace", default=".")
    args = p.parse_args()
    out = local_path(args.out, args.workspace)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for source, target in release_files():
            archive.write(source, str(target))
    print(out)

if __name__ == "__main__":
    main()
