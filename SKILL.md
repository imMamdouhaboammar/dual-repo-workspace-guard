---
name: dual-repo-workspace-guard
description: >
  Reorganize mixed local repositories into isolated dual-repo workspaces, install cross-repo anti-leak git hooks and CI guards, establish contract synchronization, and manage document lifecycles with schema validation across any project. Use when separating code and specs into separate repositories, isolating public and private repositories in a shared workspace, installing cross-repo git guards, creating unidirectional contract sync pipelines, or implementing frontmatter document lifecycles — even if they don't explicitly say "dual-repo-workspace-guard". Do NOT use for standard single-repo feature development or routine git branch merges.
---

# Dual-Repo Workspace Guard & Document Lifecycle Engine

Isolate mixed local repositories into dual repositories (e.g. public implementation code and private specs/research), install multi-layered cross-repo guards against private data leaks, establish unidirectional contract synchronization, and enforce document lifecycle schemas across any project.

$$\text{Mixed Repo} \xrightarrow[\text{Audit \& Backup}]{\text{Phases 0–1}} \text{Isolated Clones} \xrightarrow[\text{Hooks, CI \& Sync}]{\text{Phases 2–3}} \text{Guarded Workspace} \xrightarrow[\text{Lifecycle \& Proof}]{\text{Phases 4–5}} \text{Dual PR Delivery}$$

---

## ⚡ Runtime Requirements (Pre-flight)

Before executing any commands, verify that git (>=2.25), python3 (>=3.8), tar, POSIX sh, and shasum/sha256sum are available.

> Full pre-flight details and parameter schemas → **[references/runtime-setup.md](references/runtime-setup.md)**

```bash
# Verify essential toolchain
git --version && python3 --version && tar --version && command -v shasum || command -v sha256sum
```

**Stop Rule:** If any prerequisite tool is missing or unverified, stop immediately. Report the missing capability to the user. Never improvise with unverified alternatives.

---

## 🗺️ Map of Content (MOC)

| Phase / Component | Freedom | Primary Reference | Automation Script |
|---|---|---|---|
| **Layout & Architecture** | Low | [references/architecture-layout.md](references/architecture-layout.md) | `scripts/workspace_guard.py` |
| **Phase 0: Read-Only Audit** | Low | [references/architecture-layout.md](references/architecture-layout.md) | `scripts/workspace_guard.py audit` |
| **Phase 1: Zero-Loss Backup** | Low | [references/architecture-layout.md](references/architecture-layout.md) | `scripts/workspace_guard.py backup` |
| **Phase 2: Restructure & Quarantine** | Low | [references/architecture-layout.md](references/architecture-layout.md) | `scripts/workspace_guard.py restructure` |
| **Phase 3: Cross-Repo Guards** | Low | [references/cross-repo-guards.md](references/cross-repo-guards.md) | `scripts/workspace_guard.py install-guards` |
| **Phase 3f: Contract Sync** | Low | [references/contract-sync.md](references/contract-sync.md) | `scripts/sync_contracts.py` |
| **Phase 4: Document Lifecycle** | Medium | [references/document-lifecycle.md](references/document-lifecycle.md) | `scripts/validate_docs.py` |
| **Phase 5: 7-Point Proof Suite** | Low | [references/verification-suite.md](references/verification-suite.md) | `scripts/verify_guards.py` |

---

## Phase 0: Read-Only Audit (Freedom: Low)

Inspect the existing repository without making any modifications.

### TWI Execution Breakdown
- **Step:** Run `git remote -v`, `git branch -vv`, `git status --porcelain=v2`, `git stash list`, and perform a deep commit history scan for spec-only paths (`product/`, `research/`, `zzzops/`, `delivery/`, `architecture/ADRs/`, etc.).
- **Key Point:** Output results to `<workspace_root>/_backups/AUDIT.md`. Do not touch or stage any working tree files.
- **Why:** Modifying files or moving branches before discovering uncommitted work, stashes, or pre-existing history leaks leads to irreversible data loss or uncontained exposure.

**Pre-Execution Checklist:**
- [ ] Working tree inspected for uncommitted files and stashes.
- [ ] All remotes and tracking branches mapped.
- [ ] History scanned for sensitive private paths in public commits.
- [ ] Audit written to `_backups/AUDIT.md`.

**🛑 Hard Stop Conditions:**
1. **Leak Found in History:** If any private spec path exists in the public remote's git history, **STOP IMMEDIATELY**. Report the files, commit SHAs, and dates to the owner. Do not push, rewrite history, or open PRs.
2. **Unexpected Layout:** If a third remote or submodule configuration is found, **STOP AND REPORT**.

---

## Phase 1: Zero-Loss Backup & Verification (Freedom: Low)

Create verifiable, bit-for-bit backups of all repositories before restructuring.

### TWI Execution Breakdown
- **Step:** For every repository, generate a complete Git bundle (`git bundle create _backups/<name>-<date>.bundle --all`), verify it with `git bundle verify`, and tarball the working tree (excluding build artifacts). Record SHA-256 digests in `AUDIT.md`.
- **Key Point:** Both the bundle verification and SHA-256 calculation must succeed before proceeding to Phase 2.
- **Why:** Restructuring involves directory moves and remote reconfigurations; without verified bundle archives, any mistake cannot be rolled back safely.

**Pre-Execution Checklist:**
- [ ] Git bundle generated with `--all` refs.
- [ ] `git bundle verify` returns exit code 0.
- [ ] Untracked/uncommitted files archived in `.tar.gz` (excluding `node_modules`, build output).
- [ ] SHA-256 digests computed and appended to `AUDIT.md`.

---

## Phase 2: Restructure, Quarantine & Clean Clones (Freedom: Low)

Establish the clean multi-root workspace layout and freeze legacy repositories.

### Target Layout
```text
<workspace_root>/                    # plain folder, NOT a git repository
  README-WORKSPACE.md                 # local only, never committed anywhere
  <project>.code-workspace            # VS Code multi-root file, local only
  code/                               # clone of PUBLIC repo; only remote: origin = public
  spec/                               # clone of PRIVATE repo; only remote: origin = private
  code-worktrees/                     # optional git worktrees for parallel code branches
  _quarantine/                        # legacy combined repo, push URLs disabled
  _backups/                           # git bundles and working-tree archives
```

### TWI Execution Breakdown
- **Step:** Clone `code/` and `spec/` from their respective remotes. Move uncommitted files to the appropriate clone by ownership. Pure unpushed branches are cherry-picked onto their respective clone. Move the old repository into `_quarantine/` and disable all remote push URLs (`git remote set-url --push <remote> DISABLED-quarantine`).
- **Key Point:** Each clone must have **exactly one** remote. Never add the other repository as a remote. Mixed branches are not split automatically; leave them in quarantine and list in `AUDIT.md`.
- **Why:** Cross-remotes cause accidental `git push --all` leaks. Disabling push in quarantine prevents developers from accidentally pushing from the old folder.

---

## Phase 3: Cross-Repo Guards & Sync Protocol (Freedom: Low)

Install automated barriers across Git configuration, hooks, CI, and agent permissions.

> Detailed guard implementations → **[references/cross-repo-guards.md](references/cross-repo-guards.md)**  
> Contract synchronization engine → **[references/contract-sync.md](references/contract-sync.md)**

### Required Guard Installations
1. **Per-Repo Git Config:** In each clone, run `git config remote.pushDefault origin`, `git config push.default current`, and `git config core.hooksPath .githooks`.
2. **Versioned Hooks (`.githooks/`, POSIX `sh`):**
   - `code/.githooks/pre-commit`: Refuses staged files containing spec-only paths or `visibility: private`.
   - `code/.githooks/pre-push`: Refuses pushes to non-public remotes, or commits touching spec paths/private frontmatter.
   - `spec/.githooks/pre-push`: Refuses pushes to non-private remotes.
3. **CI Gate (`code/.github/workflows/ci-no-private-content.yml`):** Runs on push and PR; fails on spec-only paths or `visibility: private`.
4. **Claude Code Sandboxing (`code/.claude/settings.json`):** Allows read access to `../spec/**`, denies write access outside `code/`.
5. **AGENTS.md Boundary Sections:** Place repository role headers at the top of each repo's `AGENTS.md`.
6. **Contract Sync Tool (`code/tools/sync_contracts.py`):**
   - Unidirectional copy from `spec/` to `code/` for `contracts/schemas/*.json` and `contracts/examples/*.json` only.
   - Enforces clean spec working tree and pinned commit SHA.
   - Updates `contracts/PROVENANCE.md` with SHA-256 digests.
7. **Workspace Local Files:** Install `README-WORKSPACE.md` and `<project>.code-workspace` at workspace root (never committed).

---

## Phase 4: Document Lifecycle & Schema Validation (Freedom: Medium)

Establish unambiguous document states and automated validation.

> Document schema and classification canon → **[references/document-lifecycle.md](references/document-lifecycle.md)**

### Frontmatter Standard
Every Markdown document in `spec/` and `code/docs/` requires YAML frontmatter:
```yaml
---
doc_id: PROJ-SPEC-0001
title: Document Title
lifecycle: durable              # durable | transient
status: active                  # active | superseded | archived
visibility: private             # private in spec/, public in code/
owner: Project Owner
last_reviewed: 2026-09-27
review_by: 2027-03-27
expires_when: null              # transient only
superseded_by: null             # path when superseded
archived_on: null               # date when archived
archive_reason: null
---
```

### Archiving Procedure
1. Move file using `git mv <path> archive/<path>`.
2. Update frontmatter: `status: archived`, `archived_on: YYYY-MM-DD`, `archive_reason: "..."`.
3. Insert warning banner directly below frontmatter:
   `> **ARCHIVED, STALE: kept for the record only. Do not implement from this file. Current source: <path or "none">.**`
4. Do NOT modify the rest of the body text (preserves historical record).
5. Update all inbound links in active docs, `README.md`, and manifests.
6. Regenerate index: `python3 scripts/generate_docs_index.py`.
7. Validate: `python3 scripts/validate_docs.py`.

---

## Phase 5: 7-Point Guard Verification Suite (Freedom: Low)

Prove empirically that all guards fail closed and pass valid workflows.

> Detailed test procedures → **[references/verification-suite.md](references/verification-suite.md)**

```bash
# Run automated verification suite
python3 scripts/verify_guards.py --workspace <workspace-root> --code-remote <code-url> --spec-remote <spec-url>
```

**The 7 Mandatory Proof Points:**
1. In `code/`, `git push --dry-run` to private URL is refused.
2. In `spec/`, `git push --dry-run` to public URL is refused.
3. In `code/`, staging a private file or `visibility: private` is refused at commit.
4. CI `no-private-content` workflow fails when a forbidden path is introduced.
5. Claude Code permission rules deny writes to `../spec`.
6. `sync_contracts.py` refuses dirty spec trees, wrong commits, non-contract paths, and passes cleanly.
7. `validate_docs.py` passes on clean repository and fails if an archive banner is removed.

---

## Delivery Protocol

Deliver changes via two independent pull requests (one per repository):
- Branch name in both repos: `chore/workspace-guards-and-doc-lifecycle`
- **Spec PR:** Frontmatter additions, archive moves, warning banners, `DOCS-INDEX.md`, validator script, hooks, and `AGENTS.md`.
- **Code PR:** Hooks, CI workflow, `.claude/settings.json`, `sync_contracts.py`, frontmatter on code docs, index, and `AGENTS.md`.
- **PR Descriptions:** Include Phase 0 audit summary (zero private data in public PR), full doc classification table, archived documents list with reasons, raw Phase 5 verification proof logs, and items awaiting owner review.
- **Commit discipline:** Conventional commits, one concern per commit (`chore(guards): ...`, `docs(lifecycle): ...`).

---

## Invariants & Absolute Prohibitions

| Invariant | Why It Must Never Be Broken |
|---|---|
| **No Cross Remotes** | Never add the other repository as a remote. It invites accidental cross-pushes and history contamination. |
| **No Force Pushing** | Never force-push or rewrite remote branches. Remote history is immutable during migration. |
| **No Deleting Backups / Quarantine** | `_backups/` and `_quarantine/` are safety nets. Only the human owner may delete them after full sign-off. |
| **No Committing Local Workspace Files** | `README-WORKSPACE.md` and `*.code-workspace` are developer-local. Committing them leaks local directory layouts. |
| **No `--no-verify`** | Bypassing git hooks bypasses security gates. The workspace strictly forbids `--no-verify`. |
| **Preserve Archived Body Content** | Archived files are legal/engineering evidence. Never edit the text below the warning banner. |
| **No Guessing Classifications** | Unclear documents default to `durable + active` and are flagged for owner review. |

### Rationalization & Discipline Table

| Temptation / Rationalization | Reality & Response |
|---|---|
| *"Skipping the backup will save 5 minutes."* | **Forbidden.** One bad cherry-pick or wrong move without a verified bundle causes permanent data loss. Run `phase1_backup`. |
| *"I will just add the spec repo as a remote to cherry-pick easily."* | **Forbidden.** A remote link between public and private creates irreversible leak risk. Fetch or cherry-pick via bundle or patch. |
| *"The pre-commit hook is blocking my quick commit; I'll use `--no-verify`."* | **Forbidden.** If the hook blocks, private content was staged. Fix the staging boundary. Never bypass. |
| *"I should rewrite this archived doc to make it accurate."* | **Forbidden.** Archived docs represent what was believed at that time. Add the banner and create a new doc instead. |
