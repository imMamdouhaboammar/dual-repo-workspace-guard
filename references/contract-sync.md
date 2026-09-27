# Contract Synchronization Protocol

This reference defines the unidirectional sync mechanism between the private specification repository and the public code repository.

## The Synchronization Invariant

1. **Unidirectional (Spec -> Code Only):** Contracts originate in `spec/` and are replicated to `code/`. Nothing is ever synced from `code/` to `spec/`. The spec repository references code solely via public commit SHAs or PR links.
2. **Strict Whitelist:** The sync tool copies **ONLY**:
   - `contracts/schemas/*.json`
   - `contracts/examples/*.json`
   Any other file (Markdown notes, internal specs, draft schemas) is rejected immediately.
3. **Immutable Provenance:** Every sync operation updates `contracts/PROVENANCE.md` in the code repository, documenting the exact upstream commit SHA, sync timestamp, and individual SHA-256 digests of every synchronized file.

---

## Tool Interface & CLI Contract

File: `code/tools/sync_contracts.py`

### Usage
```bash
python3 tools/sync_contracts.py --spec ../spec --commit <sha>
python3 tools/sync_contracts.py --check-provenance
```

### Execution Flow & Validation Steps

1. **Path Resolution:** Resolves and validates `--spec` directory exists and is a git repository.
2. **Clean Tree Verification:**
   ```bash
   cd "$SPEC_DIR" && git status --porcelain
   ```
   If untracked or uncommitted changes exist in `spec/`, abort immediately with an error. Syncing uncommitted work introduces untracked drift.
3. **Commit Hash Verification:**
   Verifies that the provided `--commit <sha>` matches the checked-out HEAD of `spec/` (or is a valid commit object).
4. **Copy & Filter:**
   - Iterates through `contracts/schemas/` and `contracts/examples/`.
   - Copies files into `code/contracts/schemas/` and `code/contracts/examples/`.
   - Rejects any file outside `.json` schema/example patterns.
5. **Digest Calculation:**
   Calculates SHA-256 checksums for each synchronized file.
6. **Provenance Manifest Generation:**
   Rewrites `contracts/PROVENANCE.md`:
   ```markdown
   # Contract Provenance Record

   - **Source Repository:** Private Spec Repository
   - **Upstream Commit SHA:** <commit_sha>
   - **Sync Timestamp:** <iso_8601_timestamp>

   ## Synchronized Files & SHA-256 Checksums
   | File Path | SHA-256 Checksum |
   |---|---|
   | contracts/schemas/order.json | a1b2c3... |
   | contracts/examples/sample_order.json | d4e5f6... |
   ```
7. **Verification Pass:**
   Executes `--check-provenance` to confirm that disk content on `code/` matches the newly written `PROVENANCE.md` digests.
