#!/usr/bin/env python3
"""Apply the Lead Gen patch with version checks and a reversible local backup.

Standard-library only. No network, database, credentials, Git or deployment writes.
Run from an extracted patch directory, not from inside the project being patched.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
from typing import Any

PATCH_ID = "apollo-company-name-2026-10-03"


class PatchError(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise PatchError(f"Unsafe manifest path: {relative!r}")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or not parts.parts or any(p in {".", ".."} for p in parts.parts):
        raise PatchError(f"Unsafe manifest path: {relative!r}")
    if relative != parts.as_posix():
        raise PatchError(f"Non-canonical manifest path: {relative!r}")
    target = root.joinpath(*parts.parts)
    current = root
    for part in parts.parts:
        current = current / part
        if current.is_symlink():
            raise PatchError(f"Refusing to follow a symlink: {current}")
    if not target.resolve().is_relative_to(root.resolve()):
        raise PatchError(f"Path leaves the selected directory: {relative}")
    if target.exists() and not target.is_file():
        raise PatchError(f"Expected a file, not a directory: {target}")
    return target


def current_hash(path: Path) -> str | None:
    return digest(path.read_bytes()) if path.exists() else None


def matches(path: Path, expected: str | None, expected_lf: str | None = None) -> bool:
    """Accept only byte identity or a documented UTF-8 CRLF/LF conversion."""
    if not path.exists():
        return expected is None
    data = path.read_bytes()
    if digest(data) == expected:
        return True
    if expected is None or expected_lf is None or b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return digest(data.replace(b"\r\n", b"\n")) == expected_lf


def atomic_write(path: Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".leadgen-patch-", dir=path.parent, delete=False) as handle:
            name = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
        name = None
    finally:
        if name is not None:
            Path(name).unlink(missing_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise PatchError(f"Cannot read {path}: {error}") from error
    if not isinstance(content, dict):
        raise PatchError(f"Invalid manifest: {path}")
    return content


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != 1 or manifest.get("patch_id") != PATCH_ID:
        raise PatchError("Manifest is not for this patch version.")
    if not isinstance(manifest.get("files"), list) or not manifest["files"]:
        raise PatchError("Manifest has no replacement files.")
    seen: set[str] = set()
    for entry in manifest["files"]:
        relative = entry.get("path")
        if not isinstance(relative, str) or relative in seen:
            raise PatchError("Duplicate or invalid replacement path.")
        seen.add(relative)
        for key in ("before_sha256", "after_sha256"):
            value = entry.get(key)
            if key == "before_sha256" and value is None:
                continue
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise PatchError(f"Invalid {key} for {relative}")


def preflight(project: Path, package: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    validate_manifest(manifest)
    if project == package or project.is_relative_to(package):
        raise PatchError("Extract the patch separately from your existing project. Do not patch the package itself.")
    if not (project / "backend/app/main.py").is_file() or not (project / "frontend/package.json").is_file():
        raise PatchError("--project must point to the existing repository root containing backend and frontend.")
    conflicts: list[str] = []
    pending: list[dict[str, Any]] = []
    for entry in manifest["files"]:
        payload = safe_path(package, entry["path"])
        if current_hash(payload) != entry["after_sha256"]:
            conflicts.append(f"Patch payload missing or modified: {entry['path']}")
            continue
        target = safe_path(project, entry["path"])
        existing = current_hash(target)
        if matches(target, entry["after_sha256"], entry.get("after_lf_sha256")):
            continue
        if not matches(target, entry["before_sha256"], entry.get("before_lf_sha256")):
            conflicts.append(f"Project differs from the supplied source ZIP: {entry['path']}")
            continue
        # Preserve the exact local pre-image (including Windows line endings),
        # rather than the source archive's bytes, for conflict-safe rollback.
        pending.append({**entry, "before_sha256": existing})
    # Unchanged interfaces/dependency files also have to match. A matching edited
    # file alone does not prove that a newer application's contracts are compatible.
    for entry in manifest.get("baseline_guards", []):
        if not matches(safe_path(project, entry["path"]), entry["sha256"], entry.get("lf_sha256")):
            conflicts.append(f"Unchanged source/dependency contract differs: {entry['path']}")
    if conflicts:
        raise PatchError("Preflight stopped; no project files were changed.\n  " + "\n  ".join(conflicts) +
                         "\nCompare these differences first. Do not force this patch over a newer version.")
    return pending


def restore_entries(project: Path, backup: Path, entries: list[dict[str, Any]]) -> None:
    for entry in reversed(entries):
        target = safe_path(project, entry["path"])
        if entry["before_sha256"] is None:
            target.unlink(missing_ok=True)
        else:
            data = safe_path(backup / "files", entry["path"]).read_bytes()
            if digest(data) != entry["before_sha256"]:
                raise PatchError(f"Backup hash mismatch: {entry['path']}")
            atomic_write(target, data, entry.get("mode", 0o644))


def apply(project: Path, package: Path, manifest: dict[str, Any], pending: list[dict[str, Any]]) -> None:
    if not pending:
        print("Already applied: all patch files and guarded source files match. Nothing changed.")
        return
    parent = project.parent / f"{project.name}-patch-backups"
    if parent.is_symlink():
        raise PatchError("Refusing a symlinked backup directory.")
    parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup = parent / stamp
    backup.mkdir()
    entries: list[dict[str, Any]] = []
    # Save every pre-image before changing any project file.
    for entry in pending:
        target = safe_path(project, entry["path"])
        existing = current_hash(target)
        if existing != entry["before_sha256"]:
            raise PatchError(f"File changed during preparation: {entry['path']}. Nothing has been applied.")
        saved = dict(entry)
        saved["mode"] = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
        if target.exists():
            atomic_write(safe_path(backup / "files", entry["path"]), target.read_bytes(), saved["mode"])
        entries.append(saved)
    record = {"schema": 1, "patch_id": PATCH_ID, "project": str(project), "created_utc": stamp, "files": entries}
    atomic_write(backup / "backup_manifest.json", (json.dumps(record, indent=2) + "\n").encode())
    written: list[dict[str, Any]] = []
    try:
        for entry in entries:
            target = safe_path(project, entry["path"])
            if current_hash(target) != entry["before_sha256"]:
                raise PatchError(f"File changed during apply: {entry['path']}")
            data = safe_path(package, entry["path"]).read_bytes()
            if digest(data) != entry["after_sha256"]:
                raise PatchError(f"Patch payload changed during apply: {entry['path']}")
            # Include the current file so an interruption just after replacement
            # is also recoverable by the exception handler.
            written.append(entry)
            atomic_write(target, data, entry["mode"])
    except BaseException as error:
        try:
            restore_entries(project, backup, written)
        except BaseException as rollback_error:
            raise PatchError(f"Apply failed ({error}); automatic restore also failed ({rollback_error}). "
                             f"Preserved backup: {backup}") from error
        raise PatchError(f"Apply failed and files written by this run were restored: {error}. Backup: {backup}") from error
    print(f"Applied {len(entries)} files. No network, Git, database, or deployment changes were made.")
    print(f"BACKUP: {backup}")
    print("Run the complete backend tests and frontend check/test/build before deployment.")
    print(f'ROLLBACK: python "{package / "APPLY_PATCH.py"}" --project "{project}" --rollback "{backup}"')


def rollback(project: Path, backup: Path) -> None:
    record = load_json(backup / "backup_manifest.json")
    validate_manifest(record)
    if Path(record.get("project", "")).resolve() != project:
        raise PatchError("This backup belongs to a different project directory.")
    conflicts = []
    for entry in record["files"]:
        target = safe_path(project, entry["path"])
        if not (matches(target, entry["before_sha256"], entry.get("before_lf_sha256")) or
                matches(target, entry["after_sha256"], entry.get("after_lf_sha256"))):
            conflicts.append(f"Edited since patch: {entry['path']}")
        if entry["before_sha256"] is not None:
            if current_hash(safe_path(backup / "files", entry["path"])) != entry["before_sha256"]:
                conflicts.append(f"Backup file damaged or missing: {entry['path']}")
    if conflicts:
        raise PatchError("Rollback stopped before writing; preserve/reconcile your later edits first.\n  " + "\n  ".join(conflicts))
    restore_entries(project, backup, record["files"])
    print("Rollback complete. Original files restored; newly added patch files removed.")
    print("This restores local source only. Deploy the restored code to roll back hosted services.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path, help="Existing project root containing backend/ and frontend/")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Read-only compatibility/integrity check (default)")
    action.add_argument("--apply", action="store_true", help="Back up and apply matching replacement files")
    action.add_argument("--rollback", type=Path, metavar="BACKUP_DIRECTORY", help="Restore the specified automatic backup")
    args = parser.parse_args()
    try:
        project = args.project.expanduser().resolve()
        package = Path(__file__).resolve().parent
        if args.rollback:
            rollback(project, args.rollback.expanduser().resolve())
        else:
            manifest = load_json(package / "patch_manifest.json")
            pending = preflight(project, package, manifest)
            if args.apply:
                apply(project, package, manifest, pending)
            else:
                print(f"PASS: patch integrity and source compatibility checks. {len(pending)} files to apply; "
                      f"{len(manifest['files']) - len(pending)} already match. No changes made.")
        return 0
    except (PatchError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
