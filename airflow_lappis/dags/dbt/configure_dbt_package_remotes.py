#!/usr/bin/env python3
"""Configure a `submodule` git remote for dbt packages installed by `dbt deps`."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml


PACKAGES_FILE = Path("packages.yml")
PACKAGES_DIR = Path("dbt_packages")
REMOTE_NAME = "submodule"


def run_git(package_dir: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=package_dir,
        check=check,
        text=True,
        capture_output=True,
    )


def read_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    if not isinstance(data, dict):
        raise ValueError(f"{path} precisa ter um objeto YAML na raiz")

    return data


def repo_stem(git_url: str) -> str:
    parsed = urlparse(git_url)
    raw_name = Path(parsed.path).name or git_url.rstrip("/").split("/")[-1]
    return raw_name.removesuffix(".git")


def candidate_names(package: dict) -> list[str]:
    names: list[str] = []
    explicit_name = package.get("name")

    if isinstance(explicit_name, str) and explicit_name:
        names.append(explicit_name)

    stem = repo_stem(package["git"])
    names.extend(
        [
            stem,
            stem.replace("-", "_"),
            stem.removesuffix("-dbt"),
            stem.replace("-", "_").removesuffix("_dbt"),
        ]
    )

    return list(dict.fromkeys(name for name in names if name))


def dbt_project_name(package_dir: Path) -> str | None:
    project_file = package_dir / "dbt_project.yml"
    if not project_file.exists():
        return None

    data = read_yaml(project_file)
    name = data.get("name")
    return name if isinstance(name, str) else None


def find_package_dir(package: dict, installed_dirs: list[Path]) -> Path | None:
    names = set(candidate_names(package))

    for package_dir in installed_dirs:
        if package_dir.name in names:
            return package_dir

    for package_dir in installed_dirs:
        project_name = dbt_project_name(package_dir)
        if project_name in names:
            return package_dir

    return None


def ensure_git_remote(package_dir: Path, git_url: str) -> None:
    if not (package_dir / ".git").exists():
        run_git(package_dir, "init")

    current_remote = run_git(package_dir, "remote", "get-url", REMOTE_NAME, check=False)
    if current_remote.returncode == 0:
        if current_remote.stdout.strip() != git_url:
            run_git(package_dir, "remote", "set-url", REMOTE_NAME, git_url)
        return

    run_git(package_dir, "remote", "add", REMOTE_NAME, git_url)


def git_packages(packages_file: Path) -> list[dict]:
    data = read_yaml(packages_file)
    packages = data.get("packages", [])

    if not isinstance(packages, list):
        raise ValueError("packages.yml precisa ter uma lista em `packages`")

    return [
        package
        for package in packages
        if isinstance(package, dict) and isinstance(package.get("git"), str)
    ]


def main() -> int:
    packages = git_packages(PACKAGES_FILE)
    if not packages:
        print("Nenhum pacote git encontrado em packages.yml")
        return 0

    if not PACKAGES_DIR.exists():
        print(f"Pasta {PACKAGES_DIR} nao encontrada. Rode `dbt deps` antes.", file=sys.stderr)
        return 1

    installed_dirs = [path for path in PACKAGES_DIR.iterdir() if path.is_dir()]
    missing_packages: list[str] = []

    for package in packages:
        git_url = package["git"]
        package_dir = find_package_dir(package, installed_dirs)

        if package_dir is None:
            missing_packages.append(git_url)
            continue

        ensure_git_remote(package_dir, git_url)
        print(f"{package_dir}: remote `{REMOTE_NAME}` -> {git_url}")

    if missing_packages:
        print(
            "Nao foi possivel encontrar as pastas criadas pelo dbt deps para:",
            file=sys.stderr,
        )
        for git_url in missing_packages:
            print(f"  - {git_url}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
