#!/bin/bash
# Build for aarch64 the third-party libraries that have no source in the UE 5.4 tree. Each source is
# downloaded once into $UE_TP_WORK/downloads and checked against a fixed hash or commit.
#
# usage: build_downloaded.sh [step ...]     (no step = all)
# steps:
#   metis     METIS 5.1.0 (NaniteBuilder). Built against Epic's metis.h, which swaps two option enums.
#   draco     Draco 1.5.6 (glTF import through Interchange).
#   ispctex   the real Intel ISPC texture compressor (BC1-7, BC6H, ETC1, ASTC) instead of a placeholder,
#             compiled with the official ispc 1.21.0 aarch64 release (the version Epic bundles for x86).
#   embree    Embree 3.13.5 (first 3.x with NEON). Needs the Embree3.Build.cs arm64 branch described in
#             docs/GB10_RENDERING.md; without Embree the editor builds no mesh cards / distance fields for Lumen.
source "$(dirname "$0")/common.sh"

step_metis() {
    local ue=$TP/metis/5.1.0 src=$W/metis-5.1.0 bd=$W/metis
    fetch https://karypis.github.io/glaros/files/sw/metis/metis-5.1.0.tar.gz metis-5.1.0.tar.gz \
        76faebe03f6c963127dbb73c13eab58c9a3faeae48779f049066a21c087c5db2 || return 1
    rm -rf "$src" "$bd"; tar -xzf "$DL/metis-5.1.0.tar.gz" -C "$W"; mkdir -p "$bd"
    tr -d '\r' < "$ue/include/metis.h" > "$src/include/metis.h"
    ( cd "$bd" && cmake -G Ninja -DCMAKE_C_COMPILER="$CLANG" -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
        -DGKLIB_PATH="$src/GKlib" -DSHARED=0 \
        -DCMAKE_C_FLAGS="-fPIC -w -Wno-implicit-function-declaration -Wno-incompatible-pointer-types -Wno-int-conversion" "$src" \
        && ninja metis ) > "$LOG/metis.log" 2>&1 || { echo "!! metis failed (see $LOG/metis.log)"; return 1; }
    mkdir -p "$ue/libmetis/Linux/$T/Release" "$ue/libmetis/Linux/$T/Debug"
    cp "$bd/libmetis/libmetis.a" "$ue/libmetis/Linux/$T/Release/" && cp "$bd/libmetis/libmetis.a" "$ue/libmetis/Linux/$T/Debug/" && echo "ok   metis"
}

step_draco() {
    local ue=$E/Plugins/Interchange/Runtime/Source/ThirdParty/Draco bd=$W/draco
    git_at https://github.com/google/draco.git draco 1.5.6 9f856abaafb4b39f1f013763ff061522e0261c6f || return 1
    rm -rf "$bd"; mkdir -p "$bd"
    ( cd "$bd" && cmake -G Ninja -DCMAKE_C_COMPILER="$CLANG" -DCMAKE_CXX_COMPILER="$CLANGXX" -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DCMAKE_CXX_FLAGS="-w -stdlib=libc++" -DBUILD_SHARED_LIBS=OFF \
        -DDRACO_TRANSCODER_SUPPORTED=OFF -DDRACO_TESTS=OFF "$DL/draco" && ninja -j "$J" draco_static ) > "$LOG/draco.log" 2>&1 \
        || { echo "!! draco failed (see $LOG/draco.log)"; return 1; }
    mkdir -p "$ue/lib/Linux/$T" && cp "$bd/libdraco.a" "$ue/lib/Linux/$T/" && echo "ok   draco"
}

step_ispctex() {
    local src=$TP/Intel/ISPCTexComp/ISPCTextureCompressor-14d998c/ispc_texcomp bd=$W/ispctex
    local out=$E/Binaries/ThirdParty/Intel/ISPCTexComp/LinuxArm64-Release ispc=$W/ispc-v1.21.0-linux.aarch64/bin/ispc
    fetch https://github.com/ispc/ispc/releases/download/v1.21.0/ispc-v1.21.0-linux.aarch64.tar.gz ispc-v1.21.0-linux.aarch64.tar.gz \
        63002ab88c5e290d69bd9700fba0dcffbb7b95f0c8dfda0a15f1ba157ca6326b || return 1
    [ -x "$ispc" ] || tar -xzf "$DL/ispc-v1.21.0-linux.aarch64.tar.gz" -C "$W"
    rm -rf "$bd"; mkdir -p "$bd/ispc_texcomp" "$out"; cp "$src"/*.ispc "$src"/*.cpp "$src"/*.h "$bd/ispc_texcomp/"
    ( cd "$bd" && for k in kernel kernel_astc; do
          "$ispc" -O2 --arch=aarch64 --target=neon-i32x4 --opt=fast-math --pic \
              -o ispc_texcomp/${k}_ispc.o -h ispc_texcomp/${k}_ispc.h ispc_texcomp/$k.ispc || exit 1
      done
      for c in ispc_texcomp ispc_texcomp_astc; do
          $CLANGXX -std=c++14 -stdlib=libc++ -O2 -fPIC -w -I. -c ispc_texcomp/$c.cpp -o ispc_texcomp/$c.o || exit 1
      done ) > "$LOG/ispctex.log" 2>&1 || { echo "!! ispctex failed (see $LOG/ispctex.log)"; return 1; }
    rm -f "$out/libispc_texcomp.a" && $AR rcs "$out/libispc_texcomp.a" "$bd"/ispc_texcomp/*.o && echo "ok   ispctex (real compressor, NEON)"
}

step_embree() {
    # Embree's CMake sets its own C++ flags, so it uses the default GNU C++ library; its API is plain C.
    local bd=$W/embree inc=$TP/Intel/Embree/Embree3135/Linux/$T lib=$E/Binaries/ThirdParty/Intel/Embree/Embree3135/Linux/$T/lib
    git_at https://github.com/embree/embree.git embree v3.13.5 698442324ccddd11725fb8875275dc1384f7fb40 || return 1
    rm -rf "$bd"; mkdir -p "$bd"
    ( cd "$bd" && cmake -G Ninja -DCMAKE_C_COMPILER="$CLANG" -DCMAKE_CXX_COMPILER="$CLANGXX" -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_SHARED_LINKER_FLAGS="$LLD" -DCMAKE_EXE_LINKER_FLAGS="$LLD" \
        -DEMBREE_ARM=ON -DEMBREE_MAX_ISA=NEON -DEMBREE_ISPC_SUPPORT=OFF -DEMBREE_TUTORIALS=OFF \
        -DEMBREE_TASKING_SYSTEM=INTERNAL -DEMBREE_STATIC_LIB=OFF -DEMBREE_RAY_MASK=ON -DEMBREE_FILTER_FUNCTION=ON \
        "$DL/embree" && ninja -j "$J" embree ) > "$LOG/embree.log" 2>&1 || { echo "!! embree failed (see $LOG/embree.log)"; return 1; }
    mkdir -p "$inc/include/embree3" "$lib"
    cp "$DL"/embree/include/embree3/*.h "$inc/include/embree3/" && cp -P "$bd"/libembree3.so* "$lib/" && echo "ok   embree -> ${lib#$UE_ROOT/}"
}

run_steps "metis draco ispctex embree" "$@"
