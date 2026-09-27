# Runtime Requirements & Pre-flight Checks

This reference defines the environment prerequisites, parameter contract, and pre-flight validation rules for reorganizing dual-repo workspaces and installing cross-repo guards.

## Pre-flight Checklist

Before performing any action, verify all required CLI tools are present and satisfy version constraints:

| Tool | Minimum Version | Verification Command | Failure Remediation |
|---|---|---|---|
| `git` | 2.25+ | `git --version` | Install or update Git via system package manager (`brew install git` or `apt install git`) |
| `python3` | 3.8+ | `python3 --version` | Install Python 3 via standard toolchain (`brew install python3` or `uv python install`) |
| `tar` | POSIX compatible | `tar --version` | System standard archive utility required for working-tree backups |
| `shasum` or `sha256sum` | Any | `command -v shasum || command -v sha256sum` | Required for SHA-256 digest calculation and contract provenance verification |
| `sh` | POSIX sh | `sh -c 'echo ok'` | Required to execute `.githooks/` without Bash/Zsh dependencies |

**Stop Rule:** If any tool is missing, stop immediately. Report the missing tool and command to install it. Never improvise with unverified substitutes.

---

## Workspace Parameters Contract

The skill accepts configuration either via command-line flags to `workspace_guard.py`, via an optional `workspace-config.json`, or via guided discovery:

```json
{
  "project_name": "project-slug",
  "workspace_root": "~/Documents/project-slug-workspace",
  "code_repo": {
    "name": "code",
    "remote_url": "https://github.com/organization/code-repo",
    "visibility": "public",
    "docs_path": "docs",
    "doc_prefix": "CODE"
  },
  "spec_repo": {
    "name": "spec",
    "remote_url": "https://github.com/organization/spec-repo",
    "visibility": "private",
    "docs_path": ".",
    "doc_prefix": "SPEC"
  },
  "guard_rules": {
    "spec_only_paths": [
      "product/",
      "research/",
      "zzzops/",
      "delivery/",
      "experience/",
      "engineering/",
      "evals/",
      "architecture/ADRs/",
      "EXECUTIVE-SUMMARY-AR.md",
      "DECISION-REGISTER.md"
    ],
    "allowed_contract_patterns": [
      "contracts/schemas/*.json",
      "contracts/examples/*.json"
    ]
  },
  "document_lifecycle": {
    "owner": "Mamdouh Aboammar",
    "default_review_horizon_months": 6
  }
}
```

---

## Safety Mode & Non-Destructive Invariant

Every execution must run in safe, incremental order:
1. **Never mutate working files before Phase 1 verified bundle backups.**
2. **Never add a remote pointing to the other repository.**
3. **Never push or modify remote repository state during migration.**
4. **Never delete the old combined repository** — always move to `_quarantine/` with remote push URL disabled.
