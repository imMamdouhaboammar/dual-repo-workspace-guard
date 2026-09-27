#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_NAME="dual-repo-workspace-guard"

echo "📦 Installing ${TARGET_NAME} across AI agent environments..."

# Claude Code
if [ -d "$HOME/.claude" ] || command -v claude >/dev/null 2>&1; then
  mkdir -p "$HOME/.claude/skills"
  rm -rf "$HOME/.claude/skills/${TARGET_NAME}"
  cp -r "$SCRIPT_DIR" "$HOME/.claude/skills/${TARGET_NAME}"
  echo "  ✅ Installed for Claude Code -> $HOME/.claude/skills/${TARGET_NAME}"
fi

# Antigravity / Gemini CLI
if [ -d "$HOME/.gemini" ]; then
  mkdir -p "$HOME/.gemini/config/skills"
  rm -rf "$HOME/.gemini/config/skills/${TARGET_NAME}"
  cp -r "$SCRIPT_DIR" "$HOME/.gemini/config/skills/${TARGET_NAME}"
  echo "  ✅ Installed for Antigravity / Gemini CLI -> $HOME/.gemini/config/skills/${TARGET_NAME}"
fi

# Codex / OpenCode
if [ -d "$HOME/.codex" ]; then
  mkdir -p "$HOME/.codex/skills"
  rm -rf "$HOME/.codex/skills/${TARGET_NAME}"
  cp -r "$SCRIPT_DIR" "$HOME/.codex/skills/${TARGET_NAME}"
  echo "  ✅ Installed for Codex / OpenCode -> $HOME/.codex/skills/${TARGET_NAME}"
fi

# Cursor Global
if [ -d "$HOME/.cursor" ]; then
  mkdir -p "$HOME/.cursor/skills"
  rm -rf "$HOME/.cursor/skills/${TARGET_NAME}"
  cp -r "$SCRIPT_DIR" "$HOME/.cursor/skills/${TARGET_NAME}"
  echo "  ✅ Installed for Cursor -> $HOME/.cursor/skills/${TARGET_NAME}"
fi

# Universal Agent Kernel
mkdir -p "$HOME/.agents/skills"
rm -rf "$HOME/.agents/skills/${TARGET_NAME}"
cp -r "$SCRIPT_DIR" "$HOME/.agents/skills/${TARGET_NAME}"
echo "  ✅ Installed for Universal Agent Kernel -> $HOME/.agents/skills/${TARGET_NAME}"

echo ""
echo "🎉 Installation complete! The skill is now active across your agent environments."
