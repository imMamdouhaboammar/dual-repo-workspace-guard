# 7-Point Guard Verification Suite & Proof Protocol

This reference defines the verification procedures, empirical proof gates, and evidence capture formats required before submitting the delivery pull requests.

## The 7 Proof Points

Every guard must be tested under both positive (valid pass) and negative (fail-closed) conditions. The raw terminal outputs are captured and embedded into the final PR descriptions.

### Test 1: Cross-Remote Push Rejection in Code Repo
- **Objective:** Prove `code/.githooks/pre-push` rejects pushes targeting the private remote URL.
- **Procedure:**
  ```bash
  cd "$WORKSPACE_ROOT/code"
  git push --dry-run "$SPEC_REMOTE_URL" main
  ```
- **Expected Result:** Exit code 1. Hook prints rejection notice citing remote URL mismatch.

### Test 2: Cross-Remote Push Rejection in Spec Repo
- **Objective:** Prove `spec/.githooks/pre-push` rejects pushes targeting the public remote URL.
- **Procedure:**
  ```bash
  cd "$WORKSPACE_ROOT/spec"
  git push --dry-run "$CODE_REMOTE_URL" main
  ```
- **Expected Result:** Exit code 1. Hook prints rejection notice citing remote URL mismatch.

### Test 3: Staged Private Content Rejection at Commit
- **Objective:** Prove `code/.githooks/pre-commit` prevents private files or private frontmatter from being committed.
- **Procedure:**
  ```bash
  cd "$WORKSPACE_ROOT/code"
  echo "---"$'\n'"visibility: private"$'\n'"---" > test-leak.md
  git add test-leak.md
  git commit -m "test: simulate accidental private commit"
  ```
- **Expected Result:** Exit code 1. Hook detects `visibility: private` and aborts commit before commit object creation.
- **Cleanup:** `git reset HEAD test-leak.md && rm test-leak.md`

### Test 4: CI Workflow Rejection Simulation
- **Objective:** Prove `ci-no-private-content.yml` fails on forbidden paths.
- **Procedure:**
  Run the CI evaluation logic directly in a subshell against a simulated forbidden folder:
  ```bash
  mkdir -p "$WORKSPACE_ROOT/code/product"
  touch "$WORKSPACE_ROOT/code/product/secret.md"
  # Run CI step script
  # Verify non-zero exit code
  rm -rf "$WORKSPACE_ROOT/code/product"
  ```
- **Expected Result:** Non-zero exit code with error message identifying forbidden path.

### Test 5: Agent Boundary Enforcement Dry Test
- **Objective:** Prove `.claude/settings.json` restricts edits outside the code repository.
- **Procedure:**
  Attempt dry file write to `../spec/probe.tmp` from an agent subsession rooted in `code/`.
- **Expected Result:** Permission denied by tool boundary.

### Test 6: Contract Sync Protocol Integrity
- **Objective:** Prove `sync_contracts.py` fails on dirty tree, invalid commit, or non-whitelisted paths, and succeeds cleanly.
- **Procedures:**
  1. Dirty tree test: create untracked file in `spec/`, run sync, verify exit 1.
  2. Non-contract test: attempt syncing `spec/notes.txt`, verify exit 1.
  3. Clean sync test: run with verified commit SHA, confirm `contracts/PROVENANCE.md` updated and matches checksums.

### Test 7: Document Validator Positive & Negative Gates
- **Objective:** Prove `validate_docs.py` passes on clean workspace, but fails immediately if an archived banner is removed.
- **Procedure:**
  1. Run `python3 scripts/validate_docs.py` -> passes (exit 0).
  2. Temporarily delete banner from one file in `archive/`.
  3. Run validator -> fails with exit 1 identifying missing banner.
  4. Restore banner -> passes (exit 0).
