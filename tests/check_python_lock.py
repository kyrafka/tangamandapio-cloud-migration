"""Ensure the hashed CI lock satisfies every direct Python manifest constraint."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "app" / "requirements-ci.lock"
INPUT = ROOT / "app" / "requirements-ci.txt"
LOCKED_LINE = re.compile(r"^\s*([A-Za-z0-9_.-]+)==([^\s\\]+)")


def read_manifests(path: Path, visited: set[Path] | None = None) -> list[Requirement]:
    visited = visited or set()
    path = path.resolve()
    if path in visited:
        return []
    visited.add(path)

    requirements: list[Requirement] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-r ", "--requirement ")):
            include = line.split(maxsplit=1)[1]
            requirements.extend(read_manifests(path.parent / include, visited))
            continue
        if line.startswith("-"):
            continue
        requirements.append(Requirement(line))
    return requirements


def read_lock(path: Path) -> dict[str, Version]:
    locked: dict[str, Version] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = LOCKED_LINE.match(line)
        if match:
            name, version = match.groups()
            locked[canonicalize_name(name)] = Version(version)
    return locked


def main() -> int:
    requirements = read_manifests(INPUT)
    locked = read_lock(LOCK)
    failures: list[str] = []

    for requirement in requirements:
        if requirement.marker and not requirement.marker.evaluate():
            continue
        name = canonicalize_name(requirement.name)
        version = locked.get(name)
        if version is None:
            failures.append(f"{requirement.name}: falta en {LOCK.relative_to(ROOT)}")
        elif requirement.specifier and version not in requirement.specifier:
            failures.append(
                f"{requirement.name}=={version} no satisface "
                f"{requirement.specifier} ({requirement})"
            )

    if failures:
        print("PYTHON_LOCK=DESACTUALIZADO", file=sys.stderr)
        print("\n".join(f"- {failure}" for failure in failures), file=sys.stderr)
        return 1

    print(f"PYTHON_LOCK=VIGENTE ({len(requirements)} requisitos directos; hashes requeridos por CI)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
