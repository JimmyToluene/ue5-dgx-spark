#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 JimmyToluene (https://github.com/JimmyToluene)
# Shared settings for the aarch64 third-party rebuild scripts in this folder. Sourced, not run.
#
#   UE_ROOT   the UnrealEngine 5.4 checkout with patches/unreal-engine-5.4-aarch64.patch applied and
#             GitDependencies fetched                         (default: $HOME/UnrealEngine)
#   UE_TP_WORK  scratch folder for build trees, logs, downloads (default: $HOME/ue-arm64-thirdparty)
#   UE_TP_JOBS  parallel compile jobs                            (default: number of cores / 2)
#
# Tools: system clang-18 / lld-18 / llvm-ar-18 with libc++ (see README.md, step 1). The engine links the
# system libc++, so every C++ library rebuilt here uses -stdlib=libc++ unless noted.
set -u
UE_ROOT=${UE_ROOT:-$HOME/UnrealEngine}
E=$UE_ROOT/Engine
TP=$E/Source/ThirdParty
T=aarch64-unknown-linux-gnueabi          # Epic's directory name for LinuxArm64 third-party libraries
W=${UE_TP_WORK:-$HOME/ue-arm64-thirdparty}
LOG=$W/logs
DL=$W/downloads
J=${UE_TP_JOBS:-$(( $(nproc) / 2 ))}
CLANG=${CLANG:-clang-18}
CLANGXX=${CLANGXX:-clang++-18}
AR=${AR:-llvm-ar-18}
NM=${NM:-llvm-nm-18}
LLD="--ld-path=$(command -v ld.lld-18 || command -v ld.lld)"
CC="$CLANG -fPIC -O2 -w"
CXX="$CLANGXX -fPIC -O2 -w -stdlib=libc++"

[ -d "$E/Source" ] || { echo "UE_ROOT=$UE_ROOT does not look like an UnrealEngine checkout"; exit 1; }
[ "$(uname -m)" = "aarch64" ] || { echo "these scripts build for the aarch64 host they run on"; exit 1; }
mkdir -p "$W" "$LOG" "$DL"

# mklib <name> <out.a> <compiler> <flags> -- <sources...>: compile in parallel, archive, log to $LOG/<name>.log
mklib() {
    local name=$1 out=$2 comp=$3 flags=$4; shift 5
    local od=$W/obj/$name i=0
    rm -rf "$od"; mkdir -p "$od" "$(dirname "$out")"
    : > "$LOG/$name.log"
    for s in "$@"; do
        i=$((i+1))
        ( $comp $flags -c "$s" -o "$od/$i.o" >> "$LOG/$name.log" 2>&1 || echo "FAILED $s" >> "$LOG/$name.log" ) &
        if (( i % J == 0 )); then wait; fi
    done
    wait
    if grep -q "^FAILED" "$LOG/$name.log"; then
        echo "!! $name: $(grep -c '^FAILED' "$LOG/$name.log") sources failed (see $LOG/$name.log)"; return 1
    fi
    rm -f "$out"; $AR rcs "$out" "$od"/*.o && echo "ok   $name -> ${out#$UE_ROOT/} ($i objects)"
}

# keep_x86 <file>: before overwriting a library whose .Build.cs path is the same for both architectures,
# keep the original once as <file>.x86
keep_x86() { [ -e "$1.x86" ] || { [ -e "$1" ] && cp -a "$1" "$1.x86"; }; }

# fetch <url> <file> <sha256>: download once into $DL and check the hash
fetch() {
    local url=$1 out=$DL/$2 sum=$3
    [ -f "$out" ] || curl -fL --retry 3 -o "$out" "$url" || return 1
    echo "$sum  $out" | sha256sum -c --quiet - || { echo "!! checksum mismatch for $out"; return 1; }
}

# git_at <url> <dir> <tag> <commit>: shallow clone of a tag, checked against the expected commit
git_at() {
    local url=$1 dir=$DL/$2 tag=$3 commit=$4
    [ -d "$dir/.git" ] || git clone -q --depth 1 --branch "$tag" "$url" "$dir" || return 1
    [ "$(git -C "$dir" rev-parse HEAD)" = "$commit" ] || { echo "!! $dir is not at $commit"; return 1; }
}

# run_steps <default list> [names...]: call step_<name> for each requested name
run_steps() {
    local all=$1; shift
    local rc=0 n
    for n in ${@:-$all}; do
        declare -F "step_$n" >/dev/null || { echo "unknown step: $n (known: $all)"; return 1; }
        "step_$n" || rc=1
    done
    return $rc
}
