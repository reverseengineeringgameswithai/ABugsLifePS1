#!/usr/bin/env bash
set -euo pipefail

LOG="$HOME/Downloads/ABL/b2_commit_output.log"

{
  cd "$HOME/duckstation"

  git add -A

  git commit -m "external-debugger-control: headless RPC debugger service (RAM/GPU/exec-trace/access-log/CD overlays) for ABL RE"

  FORK_HASH="$(git rev-parse HEAD)"

  cd "$HOME/Downloads/ABL"

  printf 'duckstation fork pin: %s\nbranch: external-debugger-control\nspec: ~/duckstation/EXTERNAL_DEBUGGER_CONTROL.md\n' \
    "$FORK_HASH" > tools/FORK_COMMIT.txt

  git add -A

  git status

  git commit -m "Track Obsidian RE knowledge base + RE tools + findings store; parametrize host paths; reproducibility .gitignore"

  git rev-parse HEAD
} > "$LOG" 2>&1
