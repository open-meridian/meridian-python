#!/usr/bin/env bash
# A sibling repository at its origin's main, never its working tree.
#
#   tools/sibling-at-main.sh add    <sibling> <cache> <out>
#   tools/sibling-at-main.sh files  <sibling> <cache> <out> <path>...
#   tools/sibling-at-main.sh remove <cache> <out>
#
# <sibling> is a checkout beside this one (../meridian-design), read only for
# its origin's address; nothing is written to it. Its main is fetched into
# <cache>, a bare repository under this checkout's build folder, kept between
# runs so a fetch brings only what is new. `add` puts a detached worktree of
# that main at <out>, history and all, for the checks that ask git about it;
# `files` writes only <path>... at that main to <out>; each prints the commit
# read. `remove` takes <out> away again, which the caller does when done.
#
# A working tree beside this one is whatever its owner left there, mid-change
# or weeks behind, and a gate that read it passed or failed on that (accepted
# 2026-11-07: siblings are read at origin/main, as CI reads them).
#
# A pre-push hook runs with GIT_DIR naming the pushing repository, absolutely
# from a worktree, and a git call against another directory would act on the
# pushing one instead (one flipped core.bare on a sibling clone): so none of
# git's location variables reaches the calls below.
set -euo pipefail
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_OBJECT_DIRECTORY \
      GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_PREFIX

usage() {
  echo "usage: $0 add <sibling> <cache> <out> | files <sibling> <cache> <out> <path>... | remove <cache> <out>" >&2
  exit 2
}

fetch() {  # <sibling> <cache>
  local url
  url=$(git -C "$1" remote get-url origin 2>/dev/null) \
    || { echo "sibling-at-main: no git checkout with an origin at $1" >&2; exit 1; }
  [ -d "$2" ] || { mkdir -p "$(dirname "$2")" && git init -q --bare "$2"; }
  git -C "$2" fetch -q "$url" +refs/heads/main:refs/heads/main \
    || { echo "sibling-at-main: could not fetch main from $url" >&2; exit 1; }
}

remove() {  # <cache> <out>
  if [ -d "$1" ]; then
    git -C "$1" worktree remove --force "$2" >/dev/null 2>&1 || true
    git -C "$1" worktree prune
  fi
  rm -rf "$2"
}

case "${1:-}" in
  add)
    [ $# -eq 4 ] || usage
    fetch "$2" "$3"
    remove "$3" "$4"
    git -C "$3" worktree add -q --detach "$(cd "$(dirname "$4")" 2>/dev/null && pwd || { mkdir -p "$(dirname "$4")" && cd "$(dirname "$4")" && pwd; })/$(basename "$4")" refs/heads/main
    ;;
  files)
    [ $# -ge 5 ] || usage
    fetch "$2" "$3"
    rm -rf "$4"
    mkdir -p "$4"
    git -C "$3" archive refs/heads/main -- "${@:5}" | tar -x -C "$4"
    ;;
  remove)
    [ $# -eq 3 ] || usage
    remove "$2" "$3"
    exit 0
    ;;
  *) usage ;;
esac
git -C "$3" rev-parse --short=12 refs/heads/main
