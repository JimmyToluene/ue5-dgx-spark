# Engine changes

`scripts/apply_engine_changes.py` makes these four changes in an engine tree that already has the port patch.
It finds each place by one anchor line, marks its edits with `ue5-dgx-spark`, and skips changes that are already
there. `--check` reports the state without editing. A fifth change (XMPP) is made to a library, not the source,
by `scripts/thirdparty/build_intree.sh strophe`.

## 1. Embree on aarch64

`Engine/Source/ThirdParty/Intel/Embree/Embree3.Build.cs` only links Embree for x86-64 Linux. Without Embree the
editor builds no mesh cards or distance fields (`Platform did not set USE_EMBREE, GenerateCardRepresentationData
failed`, 100 times on the default map) and Lumen loses most of the scene. The change adds an aarch64 branch that
links the Embree 3.13.5 that `scripts/thirdparty/build_downloaded.sh embree` builds (Epic bundles 3.12.2 for
x86-64 only; the API is the same).

## 2. Nanite streaming depth

`Engine/Source/Runtime/Engine/Private/Rendering/NaniteStreamingManager.cpp`, `ProcessNewResources`.

On PC, Nanite culls the hierarchy one level per pass. The number of passes is the deepest level among the pages
that are installed. A page is requested when the culling reaches the leaf that refers to it. If that leaf sits
deeper than every installed page, the culling never reaches it, the page is never requested and the number of
passes never grows: the mesh stays at its coarsest level, with no error or warning.

Observed case: the leaves that request page 2 are in node 19 (root → node 11 → node 19, depth 2), while the root
page and page 1 only contain leaves at depth 1. After page 1 loaded, the GPU requested only page 1 (to keep it
resident) and nothing else, indefinitely.

The change counts the deepest level of the whole mesh for its root page, so every leaf is reachable from the
start. Cost: a few extra, mostly empty culling passes per view.

This is not specific to aarch64. It exists in UE 5.4, 5.5 and 5.6; Epic fixed it in 5.7 on the build side
(`CalculateFinalPageHierarchyDepth` in `NaniteEncodeHierarchy.cpp`). Whether a mesh is affected depends on its
hierarchy layout, and on this machine the layout differed between builds of the same mesh with the same settings
(61 to 66 leaves over 13 builds). This change works at run time, so it also fixes meshes that were already built.

## 3. and 4. `-game` from the editor binary

Without these, `UnrealEditor <project> -game` stops with `No target platforms found` and an assertion in
`CompileGlobalShaderMap`.

- `Engine/Config/LinuxArm64/DataDrivenPlatformInfo.ini` gets the host keys `LinuxArm64:bIsEnabled=true` and
  `LinuxArm64:bUsesHostCompiler=true`, which the port patch adds only to the Linux file.
- `Engine/Source/Developer/TargetPlatform/Private/TargetPlatformManagerModule.cpp`: in `-game` the engine loads
  only the target platform named by `IniPlatformName()`, which is `LinuxArm64` on this host. The running platform
  of an editor binary (`LinuxEditor`) is created by the `Linux` module. The change also loads `Linux` on an
  aarch64 Linux host.

## 5. XMPP: `undefined symbol: __res_query`

glibc 2.34 and later no longer provide the unversioned `__res_query` that Epic's prebuilt aarch64 `libstrophe`
calls, so the XMPP module fails to link. The `-lresolv` that the port patch adds does not resolve it.
`build_intree.sh strophe` adds a one-function forwarder to `res_query` into `libstrophe_fPIC.a` and keeps the
original as `*.orig`.
