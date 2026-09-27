# Architecture & Target Workspace Layout

This reference specifies the physical directory layout, git remote isolation invariants, quarantine protocols, and branch migration rules.

## Target Directory Layout

```text
<workspace_root>/                    # plain folder, NOT a git repository
  README-WORKSPACE.md                 # local only, never committed anywhere
  <project>.code-workspace            # VS Code multi-root file, local only
  code/                               # clone of the PUBLIC repo; only remote: origin = public
  spec/                               # clone of the PRIVATE repo; only remote: origin = private
  code-worktrees/                     # optional git worktrees for parallel code branches
  _quarantine/                        # legacy combined repo after migration, push disabled
  _backups/                           # git bundles and working-tree archives from Phase 1
    AUDIT.md                          # comprehensive Phase 0 audit report
    <name>-<date>.bundle              # git bundle containing --all refs
    <name>-<date>-worktree.tar.gz     # tarball of uncommitted/untracked state
```

### The One-Remote-Per-Repo Invariant

- `code/` repository has **exactly one** remote: `origin = <public-code-remote-url>`.
- `spec/` repository has **exactly one** remote: `origin = <private-spec-remote-url>`.
- **Absolute Rule:** No repository ever gets the other repository configured as a git remote, even temporarily or with read-only fetch. Having cross-remotes creates fatal risks of `git push --all`, branch confusion, or auto-fetch synchronization leaks.

---

## Quarantine Protocol

When a legacy repository is migrated:
1. Move the entire legacy folder into `_quarantine/<original-folder-name>/`.
2. Disable remote push on all configured remotes:
   ```bash
   for r in $(git remote); do
     git remote set-url --push "$r" "DISABLED-quarantine"
   done
   ```
3. Add a prominent `QUARANTINE-README.md` at `_quarantine/<original-folder-name>/QUARANTINE-README.md`:
   ```markdown
   # QUARANTINE NOTICE: DO NOT COMMIT OR PUSH

   This legacy combined repository was quarantined during the dual-repo separation on $(date).
   All remotes have their push URLs disabled to prevent accidental pushes.
   The active repositories are located at:
   - ../../code
   - ../../spec

   Do NOT delete this quarantine folder until the owner has reviewed and validated the migration.
   ```
4. Never delete `_quarantine/`. The deletion decision belongs solely to the repository owner.

---

## Uncommitted Work & Branch Migration Protocol

### Uncommitted Files
- Files belonging to implementation/code go to `code/`.
- Files belonging to specifications, ADRs, research, or product decisions go to `spec/`.
- **Unclear ownership:** If a file's destination cannot be proven 100% unambiguously, do not guess. Leave the file in `_quarantine/` and record it in `AUDIT.md` under **"Items Requiring Owner Clarification"**.

### Branch Migration & Cherry-Picking
1. Inspect local branches with unpushed commits:
   `git log <remote>/main..<branch>`
2. **Pure Branch:** If all commits on the branch touch exclusively code files or exclusively spec files, cherry-pick them onto a matching branch in the corresponding clean clone:
   ```bash
   git checkout -b <branch-name> origin/main
   git cherry-pick <commit-hashes>
   ```
3. **Mixed Branch:** If a branch contains commits touching both code and spec files:
   - **Do NOT attempt to rewrite or split commits automatically.**
   - Leave the branch untouched in `_quarantine/`.
   - Log the branch name, commit count, and touched files in `AUDIT.md` for owner decision.
