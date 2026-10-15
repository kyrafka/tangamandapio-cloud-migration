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
AWS_RELEASE_LOCK = ROOT / "app" / "aws_release" / "current" / "requirements.lock"
AWS_RELEASE_INPUT = ROOT / "app" / "aws_release" / "current" / "requirements.txt"
AZURE_FUNCTION_LOCK = ROOT / "app" / "azure_function" / "requirements.lock"
AZURE_FUNCTION_INPUT = ROOT / "app" / "azure_function" / "requirements.txt"
LOCKED_LINE = re.compile(r"^\s*([A-Za-z0-9_.-]+)==([^\s\\]+)")
HASH_LINE = re.compile(r"--hash=sha256:[a-f0-9]{64}(?:\s|$)")


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


def find_unhashed_lock_entries(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    entries: list[tuple[str, list[str]]] = []
    current_name: str | None = None
    current_lines: list[str] = []

    for line in lines:
        match = LOCKED_LINE.match(line)
        if match:
            if current_name is not None:
                entries.append((current_name, current_lines))
            current_name = match.group(1)
            current_lines = [line]
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        entries.append((current_name, current_lines))

    return [name for name, entry_lines in entries if not any(HASH_LINE.search(line) for line in entry_lines)]


def main() -> int:
    failures: list[str] = []

    locked = read_lock(LOCK)
    manifests = (
        ("CI", read_manifests(INPUT), locked),
        ("AWS release", read_manifests(AWS_RELEASE_INPUT), read_lock(AWS_RELEASE_LOCK)),
        ("Azure Function", read_manifests(AZURE_FUNCTION_INPUT), read_lock(AZURE_FUNCTION_LOCK)),
    )

    for label, requirements, manifest_lock in manifests:
        for requirement in requirements:
            if requirement.marker and not requirement.marker.evaluate():
                continue
            name = canonicalize_name(requirement.name)
            version = manifest_lock.get(name)
            if version is None:
                failures.append(f"{label} {requirement.name}: falta en su lock")
            elif requirement.specifier and version not in requirement.specifier:
                failures.append(
                    f"{label} {requirement.name}=={version} no satisface "
                    f"{requirement.specifier} ({requirement})"
                )

    for label, lock_path in (
        ("AWS release", AWS_RELEASE_LOCK),
        ("Azure Function", AZURE_FUNCTION_LOCK),
    ):
        for name, version in read_lock(lock_path).items():
            if locked.get(name) != version:
                failures.append(f"{label} {name}=={version}: debe coincidir con el lock CI revisado")

        unhashed = find_unhashed_lock_entries(lock_path)
        if unhashed:
            failures.append(f"{label} sin hash SHA-256: " + ", ".join(unhashed))

    if failures:
        print("PYTHON_LOCK=DESACTUALIZADO", file=sys.stderr)
        print("\n".join(f"- {failure}" for failure in failures), file=sys.stderr)
        return 1

    print(
        "PYTHON_LOCK=VIGENTE "
        f"({len(manifests[0][1])} requisitos CI; "
        f"{len(manifests[1][1])} requisitos AWS release; "
        f"{len(manifests[2][1])} requisitos Azure Function; hash SHA-256 por paquete)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
