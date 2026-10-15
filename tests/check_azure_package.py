"""Verify the configured Azure Function ZIP is an immutable build of current source."""

from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FUNCTION_SOURCE = ROOT / "app" / "azure_function"
TFVARS = ROOT / "iac" / "environments" / "azure-rebuild" / "rebuild.tfvars.example"
CONFIGURED_PACKAGE = re.compile(r'^\s*function_package_path\s*=\s*"([^"]+)"\s*$', re.MULTILINE)
SHA256_NAME = re.compile(r"^azure_function_package-([a-f0-9]{64})\.zip$")
SOURCE_FILES = ("function_app.py", "host.json", "requirements.txt", "requirements.lock")
RUNTIME_ENTRY = ".python_packages/lib/site-packages/azure/functions/__init__.py"


def validate_package(package_path: Path) -> list[str]:
    failures: list[str] = []
    filename_match = SHA256_NAME.fullmatch(package_path.name)
    if not filename_match:
        failures.append("el nombre debe incluir el SHA-256 completo del paquete")
    if not package_path.is_file():
        failures.append(f"no existe el paquete: {package_path}")
        return failures
    if filename_match:
        actual_hash = hashlib.sha256(package_path.read_bytes()).hexdigest()
        if actual_hash != filename_match.group(1):
            failures.append("el SHA-256 del contenido no coincide con el nombre inmutable")

    try:
        with zipfile.ZipFile(package_path) as archive:
            names = set(archive.namelist())
            for relative_path in SOURCE_FILES:
                if relative_path not in names:
                    failures.append(f"falta {relative_path} en el ZIP")
                    continue
                packaged = archive.read(relative_path)
                current = (FUNCTION_SOURCE / relative_path).read_bytes()
                if packaged != current:
                    failures.append(f"{relative_path} no coincide con el código fuente vigente")
            if RUNTIME_ENTRY not in names:
                failures.append("falta la dependencia Azure Functions dentro del ZIP")
            if "azure-functions==" not in archive.read("requirements.lock").decode("utf-8"):
                failures.append("requirements.lock no fija azure-functions")
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        failures.append(f"ZIP inválido o incompleto: {error}")
    return failures


def main() -> int:
    if len(sys.argv) > 2:
        print("AZURE_PACKAGE=FAIL (se admite solo el ZIP generado como argumento)", file=sys.stderr)
        return 2

    failures: list[str] = []
    match = CONFIGURED_PACKAGE.search(TFVARS.read_text(encoding="utf-8"))
    if not match:
        print("AZURE_PACKAGE=FAIL (rebuild.tfvars.example debe fijar un paquete SHA-256)", file=sys.stderr)
        return 1

    package_paths = [(TFVARS.parent / match.group(1)).resolve()]
    if len(sys.argv) == 2:
        package_paths.append(Path(sys.argv[1]).resolve())
    package_paths = list(dict.fromkeys(package_paths))

    for package_path in package_paths:
        package_failures = validate_package(package_path)
        if package_failures:
            failures.extend(f"{package_path.name}: {failure}" for failure in package_failures)

    if failures:
        print("AZURE_PACKAGE=FAIL", file=sys.stderr)
        print("\n".join(f"- {failure}" for failure in failures), file=sys.stderr)
        return 1

    for package_path in package_paths:
        print(f"AZURE_PACKAGE=SOURCE_MATCH_AND_SHA256_APPROVED ({package_path.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
