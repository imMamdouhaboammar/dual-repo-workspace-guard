#!/bin/sh
# Cross-Repo Guard: pre-commit hook (POSIX sh, zero dependencies)
# Refuses commit if staged changes contain spec-only paths or private frontmatter.

set -e

FORBIDDEN_PREFIXES="{{SPEC_ONLY_PREFIXES}}"
VIOLATIONS=""

# Get list of staged files (Added, Copied, Modified)
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
  exit 0
fi

# 1. Check for forbidden spec paths
for file in $STAGED_FILES; do
  for prefix in $FORBIDDEN_PREFIXES; do
    case "$file" in
      $prefix*)
        VIOLATIONS="${VIOLATIONS}\n  - Forbidden spec path: $file"
        ;;
    esac
  done
done

# 2. Check for private visibility in YAML frontmatter
for file in $STAGED_FILES; do
  case "$file" in
    *.md|*.markdown)
      if [ -f "$file" ]; then
        if grep -q "^visibility:[[:space:]]*private" "$file" 2>/dev/null; then
          VIOLATIONS="${VIOLATIONS}\n  - Private visibility frontmatter: $file"
        fi
      fi
      ;;
  esac
done

if [ -n "$VIOLATIONS" ]; then
  printf "\n=======================================================\n" >&2
  printf "❌ COMMIT BLOCKED: Cross-Repository Leak Detected\n" >&2
  printf "=======================================================\n" >&2
  printf "The following staged files belong to the private specification\n" >&2
  printf "repository and are strictly forbidden in this public repository:\n" >&2
  printf "$VIOLATIONS\n\n" >&2
  printf "Remediation:\n" >&2
  printf "1. Unstage the files: git reset HEAD <file>\n" >&2
  printf "2. Move them to the private repository (../spec/)\n" >&2
  printf "3. If schemas or examples are needed, sync via tools/sync_contracts.py\n" >&2
  printf "=======================================================\n\n" >&2
  exit 1
fi

exit 0
