"""Create a content-addressed hotfix for the release dashboard health metric.

The deployed React bundle has no checked-in source map/source equivalent. Keep
this transformation narrow and fail closed if the expected v16 code changes.
The original immutable asset is retained for cache safety and rollback.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "current" / "static" / "assets"
SOURCE = ASSETS / "index-b24feb37dd96.js"
OLD = "value:t.database||`—`"
NEW = "value:t.status===`ok`?`ok`:t.status===`degraded`?`degradada`:`—`"


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    count = source.count(OLD)
    if count != 1:
        raise SystemExit(f"Expected one dashboard health mapping, found {count}.")

    patched = source.replace(OLD, NEW, 1).encode("utf-8")
    digest = hashlib.sha256(patched).hexdigest()
    destination = ASSETS / f"index-{digest[:12]}.js"
    if destination.exists() and destination.read_bytes() != patched:
        raise SystemExit(f"Refusing to overwrite different immutable asset: {destination}")
    destination.write_bytes(patched)
    print(f"asset={destination.name}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
