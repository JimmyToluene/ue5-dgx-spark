#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 JimmyToluene (https://github.com/JimmyToluene)
# Placeholders for the x86-only libraries that have no aarch64 build. Every exported function returns 0, so the
# modules link and the editor starts, but the feature does NOT work:
#   FBX import/export, Bink audio encoding, coremod, libvpx (WebM), Steam, EOS, OpenXR, PROJ (geo-referencing),
#   OpenCV.
# Made with tools/make_stub.py, which never exports C/C++ runtime names (see its header).
# Libraries whose .Build.cs has a separate arm64 path get a new file there. The others are replaced in place and
# the x86 original is kept beside them as <file>.x86 (re-running uses the kept original).
#
# usage: make_placeholders.sh
source "$(dirname "$0")/common.sh"
STUB="python3 $(cd "$(dirname "$0")/../.." && pwd)/tools/make_stub.py"
B=$E/Binaries/ThirdParty S=$E/Source
export NM AR CLANG

new_file() {   # new_file <x86 original> <arm64 path>
    [ -f "$1" ] || { echo "!! missing $1"; return 1; }
    $STUB "$1" "$2"
}
in_place() {   # in_place <file used by both architectures>
    local f=$1
    [ -f "$f.x86" ] || { [ -f "$f" ] && cp -a "$f" "$f.x86"; } || { echo "!! missing $f"; return 1; }
    $STUB "$f.x86" "$f"
}

rc=0
new_file "$B/FBX/2020.2/Linux/x86_64-unknown-linux-gnu/libfbxsdk.so" "$B/FBX/2020.2/Linux/$T/libfbxsdk.so" || rc=1
new_file "$S/Runtime/BinkAudioDecoder/SDK/BinkAudio/Lib/libbinka_ue_encode_lnx64_static.a" \
         "$S/Runtime/BinkAudioDecoder/SDK/BinkAudio/Lib/libbinka_ue_encode_lnxarm64_static.a" || rc=1
new_file "$TP/coremod/coremod-4.2.6/lib/Linux/x86_64-unknown-linux-gnu/libcoremodLinux.a" "$TP/coremod/coremod-4.2.6/lib/Linux/$T/libcoremodLinux.a" || rc=1
new_file "$TP/libvpx/libvpx-1.13.1/lib/Unix/x86_64-unknown-linux-gnu/libvpx_fPIC.a" "$TP/libvpx/libvpx-1.13.1/lib/Unix/$T/libvpx_fPIC.a" || rc=1
new_file "$B/Steamworks/Steamv157/x86_64-unknown-linux-gnu/libsteam_api.so" "$B/Steamworks/Steamv157/$T/libsteam_api.so" || rc=1
in_place "$TP/EOSSDK/SDK/Bin/libEOSSDK-Linux-Shipping.so" || rc=1
in_place "$B/OpenXR/linux/x86_64-unknown-linux-gnu/libopenxr_loader.so" || rc=1
in_place "$E/Plugins/Runtime/GeoReferencing/Source/ThirdParty/vcpkg-installed/overlay-x64-linux/lib/libproj.a" || rc=1
in_place "$E/Plugins/Runtime/OpenCV/Binaries/ThirdParty/Linux/libopencv_world.so.405" || rc=1
exit $rc
