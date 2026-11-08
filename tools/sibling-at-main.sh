#!/usr/bin/env bash
# A sibling repository's files at its origin's main, never its working tree.
#
#   tools/sibling-at-main.sh <sibling> <cache> <out> <path>...
#
# <sibling> is a checkout beside this one (../meridian-design), read only for
# its origin's address. Its main is fetched into <cache>, a bare repository
# under this checkout's build/ kept between runs so a fetch brings only what
# is new, and <path>... at that commit are written to <out>, emptied first;
# the caller removes <out> when done. Prints the commit read.
#
# A working tree beside this one is whatever its owner left there, mid-change
# or weeks behind, and a gate that read it passed or failed on that (accepted
# 2026-11-07: siblings are read at origin/main, as CI reads them). Nothing is
# written to the sibling.
#
# A pre-push hook runs with GIT_DIR naming the pushing repository, absolutely
# from a worktree, and a git call against another directory would act on the
# pushing one instead (one flipped core.bare on a sibling clone): so none of
# git's location variables reaches the calls below.
set -euo pipefail
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_OBJECT_DIRECTORY \
      GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_PREFIX

[ $# -ge 4 ] || { echo "usage: $0 <sibling> <cache> <out> <path>..." >&2; exit 2; }
sibling=$1 cache=$2 out=$3
shift 3

url=$(git -C "$sibling" remote get-url origin 2>/dev/null) \
  || { echo "sibling-at-main: no git checkout with an origin at $sibling" >&2; exit 1; }
[ -d "$cache" ] || git init -q --bare "$cache"
git -C "$cache" fetch -q "$url" +refs/heads/main:refs/heads/main \
  || { echo "sibling-at-main: could not fetch main from $url" >&2; exit 1; }
rm -rf "$out"
mkdir -p "$out"
git -C "$cache" archive refs/heads/main -- "$@" | tar -x -C "$out"
git -C "$cache" rev-parse --short=12 refs/heads/main
