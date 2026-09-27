#!/usr/bin/env node

/**
 * Dual-Repo Workspace Guard CLI & Universal Agent Installer
 * Executes cross-repo workspace management scripts or installs the skill into AI agent environments.
 */

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const scriptsDir = path.join(rootDir, 'scripts');

const args = process.argv.slice(2);
const command = args[0];

function printBanner() {
  console.log(`
\x1b[36m╔═══════════════════════════════════════════════════════════════════╗
║             DUAL-REPO WORKSPACE GUARD & DOC LIFECYCLE             ║
║     Cross-Repo Anti-Leak Git Guards • Contracts • Lifecycles     ║
╚═══════════════════════════════════════════════════════════════════╝\x1b[0m
`);
}

function printUsage() {
  printBanner();
  console.log(`
\x1b[1mUsage:\x1b[0m
  \x1b[32mnpx dual-repo-workspace-guard\x1b[0m <command> [options]

\x1b[1mSkill Installation Commands:\x1b[0m
  \x1b[33minstall\x1b[0m                      Install skill into all detected agent harnesses
                              (Claude Code, Antigravity, Gemini CLI, Cursor, Codex)

\x1b[1mWorkspace Management Commands:\x1b[0m
  \x1b[33maudit\x1b[0m                        Phase 0: Run read-only audit & history leak scan
  \x1b[33mbackup\x1b[0m                       Phase 1: Create verified git bundles & tar archives
  \x1b[33mrestructure\x1b[0m                  Phase 2: Set up clean clones & quarantine old repo
  \x1b[33minstall-guards\x1b[0m               Phase 3: Install .githooks, CI guard, & Claude settings
  \x1b[33msync-contracts\x1b[0m               Phase 3f: Sync contracts with SHA-256 provenance
  \x1b[33mvalidate-docs\x1b[0m                Phase 4: Validate frontmatter schema & doc lifecycles
  \x1b[33mgenerate-docs-index\x1b[0m          Phase 4d: Generate categorized DOCS-INDEX.md
  \x1b[33mverify-guards\x1b[0m                Phase 5: Run 7-point guard verification test suite

\x1b[1mExamples:\x1b[0m
  npx dual-repo-workspace-guard install
  npx dual-repo-workspace-guard audit --config workspace-config.json --repo ./old-repo
  npx dual-repo-workspace-guard verify-guards --workspace ~/Documents/project-workspace --code-remote <url> --spec-remote <url>
`);
}

function installSkill() {
  printBanner();
  console.log('\x1b[1m📦 Installing dual-repo-workspace-guard across AI Agent Environments...\x1b[0m\n');

  const homeDir = process.env.HOME || process.env.USERPROFILE || '';
  if (!homeDir) {
    console.error('❌ Error: Could not determine user home directory.');
    process.exit(1);
  }

  const targets = [
    { name: 'Claude Code', dir: path.join(homeDir, '.claude', 'skills', 'dual-repo-workspace-guard') },
    { name: 'Antigravity / Gemini CLI', dir: path.join(homeDir, '.gemini', 'config', 'skills', 'dual-repo-workspace-guard') },
    { name: 'Codex / OpenCode', dir: path.join(homeDir, '.codex', 'skills', 'dual-repo-workspace-guard') },
    { name: 'Agent Kernel', dir: path.join(homeDir, '.agents', 'skills', 'dual-repo-workspace-guard') },
    { name: 'Cursor Global', dir: path.join(homeDir, '.cursor', 'skills', 'dual-repo-workspace-guard') }
  ];

  const itemsToCopy = ['SKILL.md', 'skill-spec.json', 'references', 'scripts', 'assets', 'evals'];
  let installedCount = 0;

  for (const target of targets) {
    const parentDir = path.dirname(target.dir);
    // If parent tool directory exists or can be created
    try {
      if (fs.existsSync(parentDir) || target.name.includes('Agent Kernel') || target.name.includes('Claude')) {
        fs.mkdirSync(target.dir, { recursive: true });

        for (const item of itemsToCopy) {
          const src = path.join(rootDir, item);
          const dst = path.join(target.dir, item);
          if (fs.existsSync(src)) {
            fs.cpSync(src, dst, { recursive: true });
          }
        }

        console.log(`  \x1b[32m✅ Installed for ${target.name}\x1b[0m -> \x1b[90m${target.dir}\x1b[0m`);
        installedCount++;
      }
    } catch (err) {
      console.warn(`  \x1b[33m⚠️  Skipped ${target.name}: ${err.message}\x1b[0m`);
    }
  }

  console.log(`\n\x1b[32m🎉 Successfully installed skill across ${installedCount} agent environment(s)!\x1b[0m`);
  console.log('You can now invoke dual-repo-workspace-guard in any AI coding agent session.\n');
}

function runPython(scriptName, scriptArgs) {
  const scriptPath = path.join(scriptsDir, scriptName);
  if (!fs.existsSync(scriptPath)) {
    console.error(`❌ Script not found: ${scriptPath}`);
    process.exit(1);
  }

  const result = spawnSync('python3', [scriptPath, ...scriptArgs], {
    stdio: 'inherit',
    cwd: process.cwd(),
    env: process.env
  });

  process.exit(result.status ?? 0);
}

if (!command || command === '--help' || command === '-h' || command === 'help') {
  printUsage();
  process.exit(0);
}

if (command === 'install' || command === '--install') {
  installSkill();
  process.exit(0);
}

const restArgs = args.slice(1);

switch (command) {
  case 'audit':
  case 'backup':
  case 'restructure':
  case 'install-guards':
    runPython('workspace_guard.py', [command, ...restArgs]);
    break;
  case 'sync-contracts':
    runPython('sync_contracts.py', restArgs);
    break;
  case 'validate-docs':
    runPython('validate_docs.py', restArgs);
    break;
  case 'generate-docs-index':
    runPython('generate_docs_index.py', restArgs);
    break;
  case 'verify-guards':
    runPython('verify_guards.py', restArgs);
    break;
  default:
    console.error(`\x1b[31mUnknown command: ${command}\x1b[0m\n`);
    printUsage();
    process.exit(1);
}
