# Document Lifecycle & Schema Specification

This reference defines the document classification system, YAML frontmatter schema, archiving protocol, index generation, and automated validation gates.

## Frontmatter YAML Schema

Every Markdown document in `spec/` and `code/docs/` (except standard licenses or generated third-party files) must begin with valid YAML frontmatter:

```yaml
---
doc_id: PROJ-SPEC-0001          # Unique stable identifier, never reused (e.g. PROJ-CODE-0001 in code/)
title: Document Title
lifecycle: durable              # Enum: durable | transient
status: active                  # Enum: active | superseded | archived
visibility: private             # Enum: private in spec/, public in code/
owner: Project Owner
last_reviewed: 2026-09-27       # ISO date: YYYY-MM-DD
review_by: 2027-03-27           # ISO date: next review date (durable) or expiration date (transient)
expires_when: null              # Transient only: string describing event (e.g. "Feature X PR merged")
superseded_by: null             # String: relative path of replacing document when status = superseded
archived_on: null               # ISO date: YYYY-MM-DD when status = archived
archive_reason: null            # String: explanation of why document was archived
---
```

---

## Classification Rules

### 1. Durable Documents
- **Definition:** Documents representing long-lived truth, architecture, or policy that remain authoritative until explicitly amended or superseded.
- **Examples:**
  - `README.md`, `AGENTS.md`, `CONTEXT.md`
  - `product/PRD.md`, `product/REQUIREMENTS.md`, `product/DECISION-REGISTER.md`
  - `architecture/ARCHITECTURE.md`, `architecture/ADRs/*`
  - `contracts/README.md`, `contracts/SCHEMA-EVOLUTION.md`
  - `evals/README.md`, `research/SOURCES.md`
- **Default Review Cadence:** 6 months from `last_reviewed`.

### 2. Transient Documents
- **Definition:** Documents created to serve a specific phase, milestone, or task that lose authority once that event completes.
- **Examples:**
  - Slice prompts, task execution plans, handoff summaries
  - Dated recheck notes (e.g. `research/RECHECK-2026-09-26.md`)
  - Dated design drafts, spike findings, prototype notes
  - Milestone baseline test logs (e.g. `docs/baseline-run.md`)
- **Requirement:** Must include a non-null `expires_when` describing the termination event.

### 3. Generated Snapshots
- Output folders containing generated JSON snapshots (e.g. `graphify-out/`, `.planning/graphs/`).
- Because JSON files cannot hold YAML frontmatter, archive these entire folders under `archive/<folder>` and place a `README.md` banner inside explaining the snapshot date and provenance.

### 4. Research Evaluations
- Evaluations (`research/EVALUATION-*.md`) remain `durable` as long as an active ADR or decision cites them.
- Once no active decision cites the evaluation, move it to `archive/research/` with reason "Decision recorded in D-xx".

### 5. Ambiguous Documents
- Classify conservatively as `lifecycle: durable` and `status: active`.
- Log the document in `AUDIT.md` under **"Items Requiring Owner Clarification"**.

---

## Archiving Protocol

When an active document is retired:
1. **Move with Git:**
   `git mv <path> archive/<path>`
   Preserving relative path structure keeps directory hierarchies organized and retains git history.
2. **Update Frontmatter:**
   - Set `status: archived`
   - Set `archived_on: YYYY-MM-DD`
   - Set `archive_reason: "<concise reason>"`
3. **Insert Warning Banner:**
   Directly beneath the closing `---` of the frontmatter, insert:
   ```markdown
   > **ARCHIVED, STALE: kept for the record only. Do not implement from this file. Current source: <path or "none">.**
   ```
4. **Preserve Content:**
   Do NOT modify or reformat the remaining document body. Archived documents represent historical evidence.
5. **Update Inbound Links:**
   Update references in active documents, `README.md`, and manifest files so no active document links into `archive/` (except within an explicit "History" or "Changelog" section).
6. **Superseded Documents:**
   If a durable document is superseded by a newer version (e.g. ADR-0001 superseded by ADR-0005):
   - Leave the file in place (do not move to `archive/`).
   - Set `status: superseded` and `superseded_by: "architecture/ADRs/ADR-0005.md"`.
   - Insert banner:
     `> **SUPERSEDED: kept for the record only. Do not implement from this file. Current source: <superseded_by>.**`

---

## Index Generation (DOCS-INDEX.md)

`DOCS-INDEX.md` is generated automatically at the repository root by `scripts/generate_docs_index.py`. It must never be manually edited.

Format:
```markdown
# Documentation Index

Generated automatically on: YYYY-MM-DD

## Durable Active Documents
| Doc ID | Title | Path | Last Reviewed | Review By | Owner |
|---|---|---|---|---|---|
| IBJ-SPEC-0001 | Product Requirements | product/PRD.md | 2026-09-27 | 2027-03-27 | Owner |

## Transient Documents
| Doc ID | Title | Path | Expires When | Review By | Owner |
|---|---|---|---|---|---|
| IBJ-SPEC-0042 | Phase 1 Slice Plan | plans/slice-1.md | Slice 1 Merged | 2026-10-15 | Owner |

## Superseded Documents
| Doc ID | Title | Path | Superseded By | Owner |
|---|---|---|---|---|
| IBJ-SPEC-0003 | Initial Architecture | architecture/ADR-0001.md | architecture/ADR-0004.md | Owner |

## Archived Documents
| Doc ID | Title | Path | Archived On | Archive Reason |
|---|---|---|---|---|
| IBJ-SPEC-0010 | Spike Evaluation | archive/research/SPIKE.md | 2026-09-27 | Decided in ADR-0002 |
```

---

## Automated Validator Rules

The validator script (`validate_docs.py`) runs across the repo and enforces:

1. **Frontmatter Integrity:** Every Markdown file must parse valid YAML frontmatter with all required keys.
2. **ID Uniqueness:** No two files may share the same `doc_id`.
3. **Visibility Contract:** Spec repo cannot have `visibility: public`; Code repo cannot have `visibility: private`.
4. **Archive Banner:** Every file with `status: archived` must reside under `archive/` and contain the standardized banner.
5. **No Broken Inbound Links:** Active documents cannot link into `archive/` unless in a markdown section titled `## History`.
6. **Superseded Target Check:** Every doc with `status: superseded` must specify an existing `superseded_by` path.
7. **Fresh Index:** `DOCS-INDEX.md` must match real filesystem state without differences.
8. **Stale Review Warning:** Emits warnings for any document where `review_by` is in the past.
