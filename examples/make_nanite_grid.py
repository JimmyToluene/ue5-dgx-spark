#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 JimmyToluene (https://github.com/JimmyToluene)
"""Nanite test through Remote Control: copy a dense engine mesh twice (one copy with Nanite switched on, one without),
and lay a grid of N x N copies of one of them in a new level with a sun and a sky light.
usage: make_nanite_grid.py nanite|plain [N=40]"""
import sys
import time
import rc

SRC = "/Engine/EngineMeshes/SM_MatPreviewMesh_01"
kind = sys.argv[1] if len(sys.argv) > 1 else "nanite"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 40
dst = "/Game/Test/SM_Dense_Nanite" if kind == "nanite" else "/Game/Test/SM_Dense_Plain"
obj = dst + "." + dst.split("/")[-1]

if not rc.call(rc.EAL, "DoesAssetExist", AssetPath=dst):
    rc.call(rc.EAL, "DuplicateAsset", SourceAssetPath=SRC, DestinationAssetPath=dst)
    if kind == "nanite":
        s = rc.call(rc.SMES, "GetNaniteSettings", StaticMesh=obj)
        s["bEnabled"] = True
        t0 = time.time()
        rc.call(rc.SMES, "SetNaniteSettings", StaticMesh=obj, NaniteSettings=s, bApplyChanges=True)
        print("Nanite build took %.1f s" % (time.time() - t0))
    rc.call(rc.EAL, "SaveAsset", AssetToSave=dst, bOnlyIfIsDirty=False)
print(kind, "mesh:", obj, "| verts LOD0:", rc.call(rc.SMES, "GetNumberVerts", StaticMesh=obj, LODIndex=0),
      "| Nanite enabled:", rc.call(rc.SMES, "GetNaniteSettings", StaticMesh=obj)["bEnabled"])

level = "/Game/Test/Grid_" + kind
rc.new_level(level)
sun = rc.spawn_class("/Script/Engine.DirectionalLight", (0, 0, 2000), rotation=(-45, 30, 0), label="Sun")
rc.call(sun + ".LightComponent0", "SetIntensity", NewIntensity=6.0)
rc.spawn_class("/Script/Engine.SkyAtmosphere", (0, 0, 0), label="Atmosphere")
sky = rc.spawn_class("/Script/Engine.SkyLight", (0, 0, 500), label="SkyLight")
rc.set(sky + ".SkyLightComponent0", "bRealTimeCapture", True)
rc.spawn_mesh("/Engine/BasicShapes/Plane.Plane", (0, 0, 0), (N * 4.0, N * 4.0, 1), label="Ground")
step = 320.0
t0 = time.time()
for i in range(N):
    for j in range(N):
        rc.call(rc.EAS, "SpawnActorFromObject", _transaction=False, ObjectToUse=obj,
                Location=rc.vec((i - N / 2) * step, (j - N / 2) * step, 0), Rotation=rc.rot(0, (i * 37 + j * 91) % 360))
print("%d copies placed in %.0f s" % (N * N, time.time() - t0))
rc.spawn_class("/Script/Engine.PlayerStart", (-N * step * 0.55, -N * step * 0.20, 700), rotation=(-12, 20, 0), label="BenchStart")
rc.camera((-N * step * 0.62, -N * step * 0.25, 900), (-18, 22, 0))
rc.call(rc.LES, "SaveCurrentLevel")
