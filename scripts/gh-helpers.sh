#!/usr/bin/env bash
# Lightweight helpers for GitHub CLI (gh) to speed up daily PR workflow.
# Usage: source scripts/gh-helpers.sh

set -euo pipefail

# Set default repo (edit the slug if you fork)
gh_default_repo() {
  local repo=${1:-"TigerTORA/hive-small-file-platform"}
  gh repo set-default "$repo"
  echo "Default repo set to: $repo"
}

# Open a PR from current branch to main, fill title/body from commits
gh_pr_new() {
  local base=${1:-main}
  local head
  head=$(git rev-parse --abbrev-ref HEAD)
  gh pr create --fill --base "$base" --head "$head"
}

# Open a PR and enable label-based auto-merge
gh_pr_new_auto() {
  gh_pr_new "$@"
  local num
  num=$(gh pr view --json number -q .number)
  gh pr edit "$num" --add-label automerge
  echo "PR #$num labeled 'automerge'"
}

# Add or remove automerge label to a PR
gh_pr_automerge_on() {
  local num=${1:?"PR number required"}
  gh pr edit "$num" --add-label automerge
}
gh_pr_automerge_off() {
  local num=${1:?"PR number required"}
  gh pr edit "$num" --remove-label automerge || true
}

# Watch the latest workflow run for this branch until it finishes
gh_run_watch() {
  gh run watch --exit-status || true
}

# Quick list of open PRs for current branch
gh_pr_my() {
  local head
  head=$(git rev-parse --abbrev-ref HEAD)
  gh pr list -H "$head" -s open
}

echo "Loaded gh helpers. Examples:"
echo "  source scripts/gh-helpers.sh && gh_default_repo"
echo "  gh_pr_new_auto   # create PR from current branch and label automerge"
echo "  gh_pr_my         # list open PRs for this branch"
echo "  gh_run_watch     # watch CI until finish"

