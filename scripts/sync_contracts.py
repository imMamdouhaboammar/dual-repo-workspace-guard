#!/usr/bin/env python3
"""Contract Synchronization Utility

Unidirectionally synchronizes contract schemas and examples from a private
specification repository to a public code repository with strict whitelist
enforcement, clean tree validation, and SHA-256 provenance logging.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def calculate_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def check_git_clean(repo_path: Path) -> bool:
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    return len(res.stdout.strip()) == 0


def verify_commit_exists(repo_path: Path, commit_sha: str) -> bool:
    res = subprocess.run(
        ["git", "cat-file", "-e", f"{commit_sha}^{{commit}}"],
        cwd=repo_path,
        capture_output=True,
    )
    return res.returncode == 0


def check_provenance(contracts_dir: Path) -> bool:
    provenance_file = contracts_dir / "PROVENANCE.md"
    if not provenance_file.exists():
        print(f"❌ Error: Provenance manifest not found at {provenance_file}", file=sys.stderr)
        return False

    recorded_hashes = {}
    with open(provenance_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("|") and not line.startswith("| File") and not line.startswith("|---"):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    file_rel, sha = parts[0], parts[1]
                    recorded_hashes[file_rel] = sha

    if not recorded_hashes:
        print(f"❌ Error: No file checksum records found in {provenance_file}", file=sys.stderr)
        return False

    all_valid = True
    for rel_path, expected_sha in recorded_hashes.items():
        disk_file = contracts_dir.parent / rel_path
        if not disk_file.exists():
            print(f"❌ Missing file recorded in provenance: {rel_path}", file=sys.stderr)
            all_valid = False
            continue
        actual_sha = calculate_sha256(disk_file)
        if actual_sha != expected_sha:
            print(f"❌ Checksum mismatch for {rel_path}: expected {expected_sha}, got {actual_sha}", file=sys.stderr)
            all_valid = False

    if all_valid:
        print("✅ Provenance verified: all contract files match registered checksums.")
    return all_valid


def sync_contracts(spec_dir: Path, code_dir: Path, commit_sha: str) -> bool:
    spec_dir = spec_dir.resolve()
    code_dir = code_dir.resolve()

    if not spec_dir.exists():
        print(f"❌ Error: Spec directory does not exist: {spec_dir}", file=sys.stderr)
        return False

    if not check_git_clean(spec_dir):
        print("❌ Error: Spec repository working tree is dirty. Stash or commit changes first.", file=sys.stderr)
        return False

    if not verify_commit_exists(spec_dir, commit_sha):
        print(f"❌ Error: Commit {commit_sha} does not exist in spec repository.", file=sys.stderr)
        return False

    spec_contracts = spec_dir / "contracts"
    if not spec_contracts.exists():
        print(f"❌ Error: No contracts folder found at {spec_contracts}", file=sys.stderr)
        return False

    dest_contracts = code_dir / "contracts"
    dest_schemas = dest_contracts / "schemas"
    dest_examples = dest_contracts / "examples"

    dest_schemas.mkdir(parents=True, exist_ok=True)
    dest_examples.mkdir(parents=True, exist_ok=True)

    synced_records = []

    # Check for invalid files in spec contracts
    for root, _, files in os.walk(spec_contracts):
        rel_root = Path(root).relative_to(spec_contracts)
        for f in files:
            file_rel = rel_root / f
            file_str = file_rel.as_posix()
            is_schema = file_str.startswith("schemas/") and f.endswith(".json")
            is_example = file_str.startswith("examples/") and f.endswith(".json")
            is_meta = f in ["README.md", "SCHEMA-EVOLUTION.md"]

            if not (is_schema or is_example or is_meta):
                print(f"❌ Error: Non-whitelisted contract file in spec: contracts/{file_str}", file=sys.stderr)
                return False

            if is_schema or is_example:
                src_file = Path(root) / f
                dst_file = dest_contracts / file_rel
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
                sha = calculate_sha256(dst_file)
                rel_from_code_root = Path("contracts") / file_rel
                synced_records.append((rel_from_code_root.as_posix(), sha))

    # Write PROVENANCE.md
    provenance_path = dest_contracts / "PROVENANCE.md"
    now_iso = datetime.now(timezone.utc).isoformat()
    with open(provenance_path, "w", encoding="utf-8") as f:
        f.write("# Contract Provenance Record\n\n")
        f.write(f"- **Source Repository:** Spec Repository\n")
        f.write(f"- **Upstream Commit SHA:** `{commit_sha}`\n")
        f.write(f"- **Sync Timestamp:** `{now_iso}`\n\n")
        f.write("## Synchronized Files & SHA-256 Checksums\n")
        f.write("| File Path | SHA-256 Checksum |\n")
        f.write("|---|---|\n")
        for file_path, sha in sorted(synced_records):
            f.write(f"| {file_path} | `{sha}` |\n")

    print(f"✅ Synchronized {len(synced_records)} contract file(s) from commit {commit_sha[:8]}.")
    print(f"✅ Provenance written to {provenance_path}.")

    return check_provenance(dest_contracts)


def main():
    parser = argparse.ArgumentParser(description="Synchronize contracts with provenance verification.")
    parser.add_argument("--spec", help="Path to specification repository")
    parser.add_argument("--code", default=".", help="Path to code repository (default: current directory)")
    parser.add_argument("--commit", help="Commit SHA from spec repository to pin")
    parser.add_argument("--check-provenance", action="store_true", help="Verify current contract files against PROVENANCE.md")

    args = parser.parse_args()

    code_path = Path(args.code)
    contracts_dir = code_path / "contracts"

    if args.check_provenance:
        success = check_provenance(contracts_dir)
        sys.exit(0 if success else 1)

    if not args.spec or not args.commit:
        parser.error("--spec and --commit are required for synchronization.")

    success = sync_contracts(Path(args.spec), code_path, args.commit)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
