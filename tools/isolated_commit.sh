#!/usr/bin/env bash
# Commit without ever touching the shared staging area.
#
# WHY THIS EXISTS
# ---------------
# Several agents work in this one checkout, and they all share `.git/index`.
# Anything one agent stages can be swept into another agent's `git commit -a`.
# That happened TWICE in one session: a fifth-basis tool, its artifact, its gate
# and an analyser change all landed inside a commit whose message was about an
# unrelated row, and earlier another agent's files rode along in mine. The work
# survives, but its history becomes unfindable, which defeats the point of
# banking it.
#
# The fix is not "be quicker". `git apply --cached` + `git add` + `git commit` is
# a multi-second window no matter how tightly it is written. This uses a PRIVATE
# index (GIT_INDEX_FILE) so the shared one is never written at all, then commits
# with plumbing and moves the branch ref only if HEAD has not moved underneath.
#
# USAGE
#   tools/isolated_commit.sh -m <msgfile> [-p <patchfile>] [file ...]
#     -m  file containing the commit message (required)
#     -p  a unified diff to apply to the private index -- use for SHARED files
#         where only some hunks are yours
#     files are added whole; use for files only you touch
#
# If HEAD moved while we were building the commit, nothing is written and the
# script exits 3 so the caller can rebuild against the new HEAD.
set -euo pipefail

MSGFILE=""
PATCHFILE=""
while getopts "m:p:" opt; do
  case "$opt" in
    m) MSGFILE="$OPTARG" ;;
    p) PATCHFILE="$OPTARG" ;;
    *) echo "usage: $0 -m msgfile [-p patchfile] [file ...]" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))

[[ -f "$MSGFILE" ]] || { echo "message file not found: $MSGFILE" >&2; exit 2; }

BRANCH="$(git symbolic-ref --short HEAD)"
BEFORE="$(git rev-parse HEAD)"

PRIVATE_INDEX="$(mktemp -t abl-index.XXXXXX)"
trap 'rm -f "$PRIVATE_INDEX"' EXIT
export GIT_INDEX_FILE="$PRIVATE_INDEX"

# Seed the private index from HEAD, so it contains no other agent's staged work.
git read-tree "$BEFORE"

if [[ -n "$PATCHFILE" ]]; then
  git apply --cached "$PATCHFILE"
fi
if (( $# )); then
  git add -- "$@"
fi

if git diff-index --cached --quiet "$BEFORE" --; then
  echo "nothing to commit" >&2
  exit 1
fi

TREE="$(git write-tree)"

# Only move the branch if HEAD is still where we started. Another agent
# committing mid-flight means our tree was built on a stale base.
NOW="$(git rev-parse HEAD)"
if [[ "$NOW" != "$BEFORE" ]]; then
  echo "HEAD moved ($BEFORE -> $NOW) while building the commit; nothing written." >&2
  echo "Rebuild against the new HEAD and retry." >&2
  exit 3
fi

COMMIT="$(git commit-tree "$TREE" -p "$BEFORE" -F "$MSGFILE")"
git update-ref -m "isolated_commit" "refs/heads/$BRANCH" "$COMMIT" "$BEFORE"

# Sync the SHARED index for exactly the paths we committed.
#
# Without this the shared index still describes the old HEAD, so a path we just
# ADDED shows up there as a staged DELETION -- and the next agent's `git commit`
# would apply it, removing the file. That is strictly worse than the problem this
# script exists to solve, and it is why the first version was wrong.
#
# We set each committed path's index entry to the blob we just committed. That
# never stages working-tree content, so a shared file where only some hunks were
# ours does not drag another agent's edits in; it only stops the index claiming
# a deletion that did not happen.
CHANGED="$(git diff-tree --no-commit-id --name-only -r "$COMMIT")"
if [[ -n "$CHANGED" ]]; then
  unset GIT_INDEX_FILE
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    if blob="$(git rev-parse --verify --quiet "$COMMIT:$path")"; then
      mode="$(git ls-tree "$COMMIT" -- "$path" | awk '{print $1}')"
      git update-index --add --cacheinfo "$mode,$blob,$path"
    else
      git update-index --force-remove -- "$path"
    fi
  done <<< "$CHANGED"
fi
echo "committed $COMMIT on $BRANCH (shared index never staged, only re-synced)"
