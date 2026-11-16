# Third-party libraries on aarch64

How each library the UE 5.4 editor links is provided on aarch64 Linux, and which script step does it.
"Built" means compiled for aarch64 by `scripts/thirdparty/`; all C++ libraries use the system libc++
(`-stdlib=libc++`), because the engine is linked against it. The output paths are the ones the port patch's
`.Build.cs` changes expect (`aarch64-unknown-linux-gnueabi`), except where noted.

| Library | How | Step | Notes |
|---|---|---|---|
| DXC + ShaderConductor | built (CMake, in-tree source) | `build_intree.sh shaderconductor` | ~10 min; shader compiler for Vulkan |
| nvTextureTools 2.0.8 | built (CMake, in-tree) | `nvtt` | shared libraries |
| Ogg 1.2.2 | built (in-tree) | `ogg` | writes the `config_types.h` configure would generate |
| Opus 1.1 | built (in-tree, float build) | `opus` | the bundled configure does not run off x86 |
| Kiss FFT, SPIRV-Reflect, hlslcc, VHACD, SpeedTree 7 | built (in-tree) | `kissfft spirvreflect hlslcc vhacd speedtree` | |
| SymsLib | built (CMake, in-tree) | `syms` | |
| astcenc 4.2.0 | built with NEON over the x86 file (same path in its `.Build.cs`) | `astcenc` | x86 original kept as `*.x86` |
| etc2comp | built over the x86 file | `etc2comp` | |
| libpng 1.5.27, Vorbis 1.3.2 | rebuilt | `png vorbis` | Epic's arm64 archives are not position independent |
| Intel TBB 2019u8 | rebuilt | `tbb` | Epic's arm64 `libtbb.a` references libstdc++ |
| libstrophe | Epic's arm64 archive + a `__res_query` forwarder | `strophe` | glibc ≥ 2.34 dropped that symbol |
| OpenEXR 3.2.1, Imath 3.1.9, Boost, Oodle Data/Network | Epic's arm64 libraries, unchanged | — | selected by the port patch |
| FreeImage, libsndfile | system libraries linked in place of the x86 `.so` | `freeimage sndfile` | |
| libxml2 | system static library | `xml2` | only used by the FBX module |
| METIS 5.1.0 | built from the upstream tarball against Epic's `metis.h` | `build_downloaded.sh metis` | Epic's header swaps two option enums |
| Draco 1.5.6 | built from the upstream tag | `draco` | glTF import |
| Intel ISPC texture compressor | built with the official ispc 1.21.0 aarch64 release, NEON target | `ispctex` | BC1–7, BC6H, ETC1, ASTC; real, not a placeholder |
| Embree 3.13.5 | built from the upstream tag (NEON) | `embree` | needs the `Embree3.Build.cs` change in `ENGINE_CHANGES.md`; Epic ships 3.12.2 for x86 only |
| FBX SDK, Bink audio encoder, coremod, libvpx, Steam, EOS, OpenXR loader, PROJ, OpenCV | **placeholders** (`tools/make_stub.py`) | `make_placeholders.sh` | link-only; the features do not work |
| CEF, USD, Perforce, and the plugins listed in the port patch's `UnrealEditor.Target.cs` | disabled by the port patch | — | |
| Oodle Texture | not loaded (x86 file names) | — | other texture encoders are used |
| Python 3 SDK | missing for arm64 | — | editor Python scripting unavailable |
| Engine-wide ISPC (Chaos, Niagara kernels) | off (port patch), C++ fallbacks | — | could be turned on with the ispc aarch64 compiler; not tried |
