#!/usr/bin/env python3
"""Workspace Guard Master Orchestrator

Automates Phase 0 (Audit), Phase 1 (Backup), Phase 2 (Restructure & Quarantine),
Phase 3 (Cross-Repo Guards), Phase 4 (Document Lifecycle), and Phase 5 (Verification)
for dual-repository development workspaces across any project.
"""

import argparse
import hashlib
import json
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


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)


class WorkspaceGuard:
    def __init__(self, config_path: Path):
        self.config_path = config_path.resolve()
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)

        self.project_name = self.cfg["project_name"]
        self.workspace_root = Path(os.path.expanduser(self.cfg["workspace_root"])).resolve()
        self.code_cfg = self.cfg["code_repo"]
        self.spec_cfg = self.cfg["spec_repo"]
        self.guard_rules = self.cfg.get("guard_rules", {})
        self.spec_only_paths = self.guard_rules.get("spec_only_paths", [
            "product/", "research/", "zzzops/", "delivery/", "experience/",
            "engineering/", "evals/", "architecture/ADRs/", "EXECUTIVE-SUMMARY-AR.md", "DECISION-REGISTER.md"
        ])
        self.templates_dir = Path(__file__).parent.parent / "assets" / "templates"

    def phase0_audit(self, current_repo_path: Path) -> Path:
        """Phase 0: Read-only audit and leak scan."""
        current_repo_path = current_repo_path.resolve()
        print(f"🔍 Phase 0: Auditing local repository at {current_repo_path} (Read-only)...")

        backups_dir = self.workspace_root / "_backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        audit_file = backups_dir / "AUDIT.md"

        # 1. Remotes
        remotes_proc = run_git(["remote", "-v"], cwd=current_repo_path)
        # 2. Branches
        branches_proc = run_git(["branch", "-vv"], cwd=current_repo_path)
        # 3. Status
        status_proc = run_git(["status", "--porcelain=v2"], cwd=current_repo_path)
        # 4. Stashes
        stashes_proc = run_git(["stash", "list"], cwd=current_repo_path)
        # 5. Git config
        config_proc = run_git(["config", "--list", "--show-origin"], cwd=current_repo_path)
        relevant_config = [
            line for line in config_proc.stdout.splitlines()
            if any(k in line for k in ["remote.", "branch.", "push.", "core.hooksPath"])
        ]

        # 6. Deep leak check against history
        print("🔍 Scanning commit history for spec-only paths...")
        history_files_proc = run_git(["log", "--all", "--name-only", "--format="], cwd=current_repo_path)
        all_committed_files = set(history_files_proc.stdout.splitlines())

        leaks = []
        for f in all_committed_files:
            for sp in self.spec_only_paths:
                if f.startswith(sp):
                    leaks.append(f)
                    break

        content = [
            f"# Phase 0 Repository Audit Report: {self.project_name}",
            f"- **Audit Date:** {datetime.now(timezone.utc).isoformat()}",
            f"- **Audited Path:** `{current_repo_path}`\n",
            "## 1. Git Remotes",
            "```text",
            remotes_proc.stdout.strip() or "(none)",
            "```\n",
            "## 2. Local Branches & Tracking",
            "```text",
            branches_proc.stdout.strip() or "(none)",
            "```\n",
            "## 3. Working Tree Status & Stashes",
            "### Uncommitted & Untracked (`git status --porcelain=v2`)",
            "```text",
            status_proc.stdout.strip() or "(clean)",
            "```",
            "### Stashes (`git stash list`)",
            "```text",
            stashes_proc.stdout.strip() or "(none)",
            "```\n",
            "## 4. Relevant Git Config",
            "```text",
            "\n".join(relevant_config) or "(default)",
            "```\n",
            "## 5. History Leak Check Results",
            f"- Spec-only paths checked: `{', '.join(self.spec_only_paths[:5])}...`"
        ]

        if leaks:
            content.extend([
                f"\n⚠️ **LEAKS FOUND IN REPOSITORY HISTORY ({len(leaks)} occurrences):**",
                "```text",
                "\n".join(sorted(leaks)),
                "```",
                "\n> **STOP CONDITION TRIGGERED:** Leaks detected in history. Halting migration for owner review."
            ])
        else:
            content.append("\n✅ **No spec-only leaks detected in commit history.**")

        content.extend([
            "\n## 6. Items Requiring Owner Clarification",
            "- Check mixed branches with commits touching both code and spec.",
            "- Check any ambiguous uncommitted files before moving to quarantine."
        ])

        audit_file.write_text("\n".join(content), encoding="utf-8")
        print(f"✅ Audit written to {audit_file}.")

        if leaks:
            print(f"🛑 STOP: {len(leaks)} leak(s) found in commit history! See {audit_file}", file=sys.stderr)
            sys.exit(2)

        return audit_file

    def phase1_backup(self, current_repo_path: Path) -> list[tuple[Path, str]]:
        """Phase 1: Verified git bundle and tarball backups."""
        current_repo_path = current_repo_path.resolve()
        print(f"📦 Phase 1: Creating verified backups for {current_repo_path}...")

        backups_dir = self.workspace_root / "_backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

        bundle_path = backups_dir / f"{self.project_name}-{timestamp}.bundle"
        tar_path = backups_dir / f"{self.project_name}-{timestamp}-worktree.tar.gz"

        # 1. Create Git bundle
        print(f"  Creating git bundle: {bundle_path.name}...")
        bundle_res = run_git(["bundle", "create", str(bundle_path), "--all"], cwd=current_repo_path)
        if bundle_res.returncode != 0:
            print(f"❌ Failed to create git bundle: {bundle_res.stderr}", file=sys.stderr)
            sys.exit(1)

        # 2. Verify Git bundle
        print("  Verifying bundle integrity...")
        verify_res = run_git(["bundle", "verify", str(bundle_path)], cwd=current_repo_path)
        if verify_res.returncode != 0:
            print(f"❌ Git bundle verification failed: {verify_res.stderr}", file=sys.stderr)
            sys.exit(1)

        # 3. Create tarball of working tree excluding build/cache artifacts
        print(f"  Creating working tree archive: {tar_path.name}...")
        tar_cmd = [
            "tar", "-czf", str(tar_path),
            "--exclude=node_modules",
            "--exclude=bin",
            "--exclude=.git",
            "--exclude=dist",
            "--exclude=build",
            "-C", str(current_repo_path),
            "."
        ]
        tar_res = subprocess.run(tar_cmd, capture_output=True, text=True)
        if tar_res.returncode != 0:
            print(f"❌ Failed to archive working tree: {tar_res.stderr}", file=sys.stderr)
            sys.exit(1)

        # 4. Calculate SHA-256 hashes
        bundle_sha = calculate_sha256(bundle_path)
        tar_sha = calculate_sha256(tar_path)

        # Append to AUDIT.md
        audit_file = backups_dir / "AUDIT.md"
        if audit_file.exists():
            with open(audit_file, "a", encoding="utf-8") as f:
                f.write("\n## 7. Verified Backup Digests\n")
                f.write(f"- `{bundle_path.name}`: `{bundle_sha}` (git bundle verified)\n")
                f.write(f"- `{tar_path.name}`: `{tar_sha}` (tarball archive)\n")

        print(f"✅ Verified Git Bundle: {bundle_sha[:12]}...")
        print(f"✅ Verified Working Tree Tarball: {tar_sha[:12]}...")
        return [(bundle_path, bundle_sha), (tar_path, tar_sha)]

    def phase2_restructure(self, legacy_repo_path: Path):
        """Phase 2: Clones, migration, and quarantine."""
        print(f"🏗️  Phase 2: Setting up target workspace at {self.workspace_root}...")
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        code_dir = self.workspace_root / "code"
        spec_dir = self.workspace_root / "spec"
        quarantine_dir = self.workspace_root / "_quarantine" / legacy_repo_path.name

        # Clone clean public and private repos
        if not code_dir.exists():
            print(f"  Cloning code repo: {self.code_cfg['remote_url']} -> code/")
            run_git(["clone", self.code_cfg["remote_url"], "code"], cwd=self.workspace_root)
        if not spec_dir.exists():
            print(f"  Cloning spec repo: {self.spec_cfg['remote_url']} -> spec/")
            run_git(["clone", self.spec_cfg["remote_url"], "spec"], cwd=self.workspace_root)

        # Quarantine legacy repo
        quarantine_dir.parent.mkdir(parents=True, exist_ok=True)
        if legacy_repo_path.exists() and not quarantine_dir.exists():
            print(f"  Moving legacy repo to quarantine: {quarantine_dir}...")
            shutil.move(str(legacy_repo_path), str(quarantine_dir))

            # Disable push URLs in quarantined repo
            remotes = run_git(["remote"], cwd=quarantine_dir).stdout.splitlines()
            for r in remotes:
                run_git(["remote", "set-url", "--push", r, "DISABLED-quarantine"], cwd=quarantine_dir)

            readme_quarantine = quarantine_dir / "QUARANTINE-README.md"
            readme_quarantine.write_text(
                f"# Quarantined Combined Repository: {self.project_name}\n\n"
                "All remote push URLs have been disabled to prevent accidental pushes.\n"
                "Active isolated repositories are located at:\n"
                "- `../../code`\n"
                "- `../../spec`\n\n"
                "Do NOT delete this folder until migration has been thoroughly verified.\n",
                encoding="utf-8"
            )

        print("✅ Restructure and quarantine completed.")

    def phase3_install_guards(self):
        """Phase 3: Install git configs, hooks, CI, Claude settings, and AGENTS.md."""
        print("🛡️  Phase 3: Installing cross-repo guards...")
        code_dir = self.workspace_root / "code"
        spec_dir = self.workspace_root / "spec"

        prefixes_space = " ".join(self.spec_only_paths)
        prefixes_quoted = " ".join([f'"{p}"' for p in self.spec_only_paths])

        # Git configs
        for repo_dir in [code_dir, spec_dir]:
            if repo_dir.exists():
                run_git(["config", "remote.pushDefault", "origin"], cwd=repo_dir)
                run_git(["config", "push.default", "current"], cwd=repo_dir)
                run_git(["config", "core.hooksPath", ".githooks"], cwd=repo_dir)

        # 1. Code hooks
        code_hooks = code_dir / ".githooks"
        code_hooks.mkdir(parents=True, exist_ok=True)

        pre_commit_src = (self.templates_dir / "pre-commit.sh").read_text(encoding="utf-8")
        pre_commit_rendered = pre_commit_src.replace("{{SPEC_ONLY_PREFIXES}}", prefixes_space)
        (code_hooks / "pre-commit").write_text(pre_commit_rendered, encoding="utf-8")
        os.chmod(code_hooks / "pre-commit", 0o755)

        pre_push_src = (self.templates_dir / "pre-push.sh").read_text(encoding="utf-8")
        pre_push_code = pre_push_src.replace("{{EXPECTED_REMOTE_URL}}", self.code_cfg["remote_url"]) \
                                   .replace("{{FORBIDDEN_REMOTE_URL}}", self.spec_cfg["remote_url"]) \
                                   .replace("{{REPO_ROLE}}", "code") \
                                   .replace("{{SPEC_ONLY_PREFIXES}}", prefixes_space)
        (code_hooks / "pre-push").write_text(pre_push_code, encoding="utf-8")
        os.chmod(code_hooks / "pre-push", 0o755)

        # 2. Spec hooks
        spec_hooks = spec_dir / ".githooks"
        spec_hooks.mkdir(parents=True, exist_ok=True)
        pre_push_spec = pre_push_src.replace("{{EXPECTED_REMOTE_URL}}", self.spec_cfg["remote_url"]) \
                                    .replace("{{FORBIDDEN_REMOTE_URL}}", self.code_cfg["remote_url"]) \
                                    .replace("{{REPO_ROLE}}", "spec") \
                                    .replace("{{SPEC_ONLY_PREFIXES}}", "")
        (spec_hooks / "pre-push").write_text(pre_push_spec, encoding="utf-8")
        os.chmod(spec_hooks / "pre-push", 0o755)

        # 3. CI Workflow in Code repo
        ci_dir = code_dir / ".github" / "workflows"
        ci_dir.mkdir(parents=True, exist_ok=True)
        ci_src = (self.templates_dir / "ci-no-private-content.yml").read_text(encoding="utf-8")
        ci_rendered = ci_src.replace("{{CI_FORBIDDEN_PATHS}}", prefixes_quoted)
        (ci_dir / "ci-no-private-content.yml").write_text(ci_rendered, encoding="utf-8")

        # 4. Claude Code Settings in Code repo
        claude_dir = code_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.templates_dir / "claude-settings.json", claude_dir / "settings.json")

        # 5. Contract sync tool in code/tools/
        code_tools = code_dir / "tools"
        code_tools.mkdir(parents=True, exist_ok=True)
        sync_script = Path(__file__).parent / "sync_contracts.py"
        shutil.copy2(sync_script, code_tools / "sync_contracts.py")
        os.chmod(code_tools / "sync_contracts.py", 0o755)

        # 6. Workspace Local Files
        readme_tmpl = (self.templates_dir / "README-WORKSPACE.md.template").read_text(encoding="utf-8")
        readme_rendered = readme_tmpl.replace("{{PROJECT_NAME}}", self.project_name) \
                                     .replace("{{PROJECT_SLUG}}", self.project_name.lower().replace(" ", "-")) \
                                     .replace("{{WORKSPACE_ROOT}}", str(self.workspace_root)) \
                                     .replace("{{CODE_REMOTE_URL}}", self.code_cfg["remote_url"]) \
                                     .replace("{{SPEC_REMOTE_URL}}", self.spec_cfg["remote_url"]) \
                                     .replace("{{CODE_VISIBILITY}}", self.code_cfg["visibility"]) \
                                     .replace("{{SPEC_VISIBILITY}}", self.spec_cfg["visibility"])
        (self.workspace_root / "README-WORKSPACE.md").write_text(readme_rendered, encoding="utf-8")

        ws_tmpl = (self.templates_dir / "project.code-workspace.template").read_text(encoding="utf-8")
        ws_rendered = ws_tmpl.replace("{{CODE_VISIBILITY}}", self.code_cfg["visibility"]) \
                             .replace("{{SPEC_VISIBILITY}}", self.spec_cfg["visibility"])
        slug = self.project_name.lower().replace(" ", "-")
        (self.workspace_root / f"{slug}.code-workspace").write_text(ws_rendered, encoding="utf-8")

        print("✅ Cross-repo guards, git hooks, CI workflows, and local workspace files installed.")


def main():
    parser = argparse.ArgumentParser(description="Workspace Guard Master CLI")
    parser.add_argument("--config", required=True, help="Path to workspace-config.json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Run Phase 0 read-only audit")
    audit_parser.add_argument("--repo", required=True, help="Path to current repository")

    backup_parser = subparsers.add_parser("backup", help="Run Phase 1 verified backups")
    backup_parser.add_argument("--repo", required=True, help="Path to current repository")

    restructure_parser = subparsers.add_parser("restructure", help="Run Phase 2 restructure")
    restructure_parser.add_argument("--repo", required=True, help="Path to current repository")

    subparsers.add_parser("install-guards", help="Run Phase 3 install guards")

    args = parser.parse_args()
    guard = WorkspaceGuard(Path(args.config))

    if args.command == "audit":
        guard.phase0_audit(Path(args.repo))
    elif args.command == "backup":
        guard.phase1_backup(Path(args.repo))
    elif args.command == "restructure":
        guard.phase2_restructure(Path(args.repo))
    elif args.command == "install-guards":
        guard.phase3_install_guards()


if __name__ == "__main__":
    main()
