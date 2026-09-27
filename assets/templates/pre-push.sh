#!/bin/sh
# Cross-Repo Guard: pre-push hook (POSIX sh, zero dependencies)
# Refuses push if target remote URL is wrong or if pushing forbidden private content.

set -e

REMOTE_NAME="$1"
REMOTE_URL="$2"

EXPECTED_REMOTE_URL="{{EXPECTED_REMOTE_URL}}"
FORBIDDEN_REMOTE_URL="{{FORBIDDEN_REMOTE_URL}}"
REPO_ROLE="{{REPO_ROLE}}" # "code" or "spec"
FORBIDDEN_PREFIXES="{{SPEC_ONLY_PREFIXES}}"

# 1. Validate remote URL destination
# Normalize trailing .git or slashes for comparison
NORM_REMOTE_URL=$(echo "$REMOTE_URL" | sed 's/\.git$//; s/\/$//')
NORM_FORBIDDEN_URL=$(echo "$FORBIDDEN_REMOTE_URL" | sed 's/\.git$//; s/\/$//')

if [ -n "$FORBIDDEN_REMOTE_URL" ] && [ "$NORM_REMOTE_URL" = "$NORM_FORBIDDEN_URL" ]; then
  printf "\n=======================================================\n" >&2
  printf "❌ PUSH BLOCKED: Forbidden Remote Target Detected\n" >&2
  printf "=======================================================\n" >&2
  printf "Attempted push to forbidden cross-repository remote:\n" >&2
  printf "Target URL: %s\n" "$REMOTE_URL" >&2
  printf "This repository (%s) must NEVER push to this remote.\n" "$REPO_ROLE" >&2
  printf "=======================================================\n\n" >&2
  exit 1
fi

if [ -n "$EXPECTED_REMOTE_URL" ]; then
  NORM_EXPECTED_URL=$(echo "$EXPECTED_REMOTE_URL" | sed 's/\.git$//; s/\/$//')
  if [ "$NORM_REMOTE_URL" != "$NORM_EXPECTED_URL" ]; then
    printf "\n=======================================================\n" >&2
    printf "❌ PUSH BLOCKED: Remote URL Mismatch\n" >&2
    printf "=======================================================\n" >&2
    printf "Attempted push to unapproved remote URL: %s\n" "$REMOTE_URL" >&2
    printf "Expected canonical URL: %s\n" "$EXPECTED_REMOTE_URL" >&2
    printf "=======================================================\n\n" >&2
    exit 1
  fi
fi

# 2. Content checks on pushed commits (Code repo only)
if [ "$REPO_ROLE" = "code" ]; then
  ZERO_SHA="0000000000000000000000000000000000000000"
  VIOLATIONS=""

  while read -r local_ref local_sha remote_ref remote_sha; do
    # Skip branch deletion
    if [ "$local_sha" = "$ZERO_SHA" ]; then
      continue
    fi

    # Determine revision range to inspect
    if [ "$remote_sha" = "$ZERO_SHA" ]; then
      # New branch: check commits not in any existing remote tracking branch
      REV_RANGE="$local_sha --not --remotes"
    else
      REV_RANGE="$remote_sha..$local_sha"
    fi

    # List files touched across all pushed commits
    TOUCHED_FILES=$(git log --name-only --format="" $REV_RANGE 2>/dev/null | sort -u || true)

    for file in $TOUCHED_FILES; do
      [ -z "$file" ] && continue

      # Check path prefixes
      for prefix in $FORBIDDEN_PREFIXES; do
        case "$file" in
          $prefix*)
            VIOLATIONS="${VIOLATIONS}\n  - Spec path in commit: $file"
            ;;
        esac
      done

      # Check private visibility in touched Markdown files
      case "$file" in
        *.md|*.markdown)
          if git show "$local_sha:$file" 2>/dev/null | grep -q "^visibility:[[:space:]]*private"; then
            VIOLATIONS="${VIOLATIONS}\n  - Private frontmatter in commit: $file"
          fi
          ;;
      esac
    done
  done

  if [ -n "$VIOLATIONS" ]; then
    printf "\n=======================================================\n" >&2
    printf "❌ PUSH BLOCKED: Commits Contain Forbidden Spec Content\n" >&2
    printf "=======================================================\n" >&2
    printf "Pushed commits contain files from private specification repo:\n" >&2
    printf "$VIOLATIONS\n\n" >&2
    printf "Please remove these commits before pushing to public remote.\n" >&2
    printf "=======================================================\n\n" >&2
    exit 1
  fi
fi

exit 0
