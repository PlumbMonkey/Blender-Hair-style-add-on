"""
Package the addon into a .zip for Blender installation.

Usage:
    python build_zip.py

Produces: procedural_scalp_hair_v2.0.0.zip
"""

import zipfile
import os
import sys

ADDON_DIR = "procedural_scalp_hair"
VERSION = "2.1.0"
OUTPUT = f"procedural_scalp_hair_v{VERSION}.zip"

EXCLUDE_PATTERNS = {
    "__pycache__",
    ".pyc",
    ".pyo",
    ".DS_Store",
    "Thumbs.db",
}


def should_include(filepath):
    for pat in EXCLUDE_PATTERNS:
        if pat in filepath:
            return False
    return True


def build():
    if not os.path.isdir(ADDON_DIR):
        print(f"ERROR: '{ADDON_DIR}' directory not found. Run from the project root.")
        sys.exit(1)

    with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ADDON_DIR):
            dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
            for fname in files:
                fpath = os.path.join(root, fname)
                if should_include(fpath):
                    arcname = fpath  # keeps procedural_scalp_hair/ prefix
                    zf.write(fpath, arcname)
                    print(f"  + {arcname}")

    print(f"\nBuilt: {OUTPUT}")


if __name__ == "__main__":
    build()
