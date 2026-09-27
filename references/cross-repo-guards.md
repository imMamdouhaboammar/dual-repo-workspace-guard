# Cross-Repository Guards & Prevention of Data Leaks

This reference details the multi-layered defense system installed across git configuration, versioned hooks, continuous integration, agent permissions, and repo documentation.

## Layer 1: Per-Repo Git Configuration

Run inside each cloned repository:

```bash
# Ensure pushes default to origin and match current branch name
git config remote.pushDefault origin
git config push.default current

# Direct git to version-controlled hooks inside the repository
git config core.hooksPath .githooks
```

---

## Layer 2: Versioned Git Hooks (.githooks/)

All hooks must be pure POSIX `sh` without bashisms, external npm packages, or Python runtime dependencies so they execute reliably in any developer or CI environment.

### Code Repo `pre-commit` (`code/.githooks/pre-commit`)
- **Job:** Intercept staged changes before they enter local history.
- **Rules:**
  1. Inspect staged files via `git diff --cached --name-only`.
  2. Block if any file path starts with a spec-only directory (`product/`, `research/`, `zzzops/`, `delivery/`, `experience/`, `engineering/`, `evals/`, `architecture/ADRs/`, etc.).
  3. Scan staged Markdown files for YAML frontmatter containing `visibility: private` (using `grep -q "^visibility:[[:space:]]*private"`).
  4. If a violation is detected: print an unambiguous error message detailing the offending paths and exit with status code 1.

### Code Repo `pre-push` (`code/.githooks/pre-push`)
- **Job:** Guard remote pushes from pushing private commits or targeting the wrong remote.
- **Rules:**
  1. Validate the destination remote URL against the canonical public repository URL.
  2. Read push refs from standard input (`<local_ref> <local_sha> <remote_ref> <remote_sha>`).
  3. For each non-deletion commit range, check touched files (`git diff --name-only $remote_sha $local_sha`).
  4. Reject if commits contain any spec-only path or file with `visibility: private`.

### Spec Repo `pre-push` (`spec/.githooks/pre-push`)
- **Job:** Guard private specification repo from pushing to public remotes.
- **Rules:**
  1. Validate destination URL against the canonical private repository URL.
  2. Block any push targeting external or mismatched remotes.

---

## Layer 3: CI Enforcement in Public Code Repo

Git hooks protect local actions, but client hooks can theoretically be skipped via `--no-verify`. Continuous Integration provides the non-bypassable server-side boundary.

File: `code/.github/workflows/ci-no-private-content.yml`
```yaml
name: No Private Content Gate

on:
  push:
    branches: ["**"]
  pull_request:
    branches: ["**"]

jobs:
  no-private-content:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Verify zero spec-only paths
        run: |
          FORBIDDEN_PATHS=("product" "research" "zzzops" "delivery" "experience" "engineering" "evals" "architecture/ADRs" "EXECUTIVE-SUMMARY-AR.md" "DECISION-REGISTER.md")
          FOUND=0
          for p in "${FORBIDDEN_PATHS[@]}"; do
            if [ -e "$p" ]; then
              echo "::error file=$p::Forbidden spec path exists in public repo: $p"
              FOUND=1
            fi
          done
          if [ $FOUND -ne 0 ]; then
            echo "CI FAILED: Spec-only paths detected in public repository."
            exit 1
          fi

      - name: Verify zero private frontmatter
        run: |
          PRIVATE_FILES=$(grep -r -l --include="*.md" "^visibility:[[:space:]]*private" . || true)
          if [ -n "$PRIVATE_FILES" ]; then
            echo "::error::Found files with 'visibility: private':"
            echo "$PRIVATE_FILES"
            exit 1
          fi
          echo "Verified: Zero private content detected."
```

---

## Layer 4: Claude Code & Agent Sandboxing

Add `.claude/settings.json` in `code/` to allow read-only access to `../spec` while blocking write/edit operations outside the project root:

```json
{
  "permissions": {
    "filesystem": {
      "allowRead": ["../spec/**"],
      "denyWrite": ["../spec/**"]
    }
  }
}
```

---

## Layer 5: AGENTS.md Repository Boundary Declarations

Every repository must declare its identity and boundary rules at the very top of `AGENTS.md`:

### In `code/AGENTS.md`:
```markdown
# Repository Role: Code (Implementation)
- Visibility: PUBLIC
- Allowed Content: Application implementation code, public tests, build tooling, public documentation (`docs/`).
- FORBIDDEN Content: Private product specs, ADRs, internal research, or anything with `visibility: private`.
- Sibling Repository: Spec repo is located at `../spec` (Read-only reference).
- Contract Sync: Schemas and examples are copied ONLY via `tools/sync_contracts.py` from `../spec`. NEVER manually edit copied contracts in this repo.
```

### In `spec/AGENTS.md`:
```markdown
# Repository Role: Spec (Specifications & Architecture)
- Visibility: PRIVATE
- Allowed Content: PRDs, requirements, ADRs, research evaluations, architecture models, contracts, and internal ops.
- Sibling Repository: Implementation code repo is located at `../code`.
- Contract Sync: This repository is the source of truth for contracts (`contracts/schemas/` and `contracts/examples/`). Contracts are synced unidirectionally to `../code`. Code is never copied here.
```
