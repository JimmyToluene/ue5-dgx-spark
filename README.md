# ue5-dgx-spark

Build and run the **Unreal Engine 5.4 editor natively on an NVIDIA DGX Spark** (GB10, aarch64 Linux), with the
editor viewport, Lumen and Nanite rendering on the GB10.

Epic publishes no Linux ARM64 editor. A 52-file port patch by [MrQbit/unreal-dgx](https://github.com/MrQbit/unreal-dgx)
makes the engine compile on aarch64; this repository supplies what is still needed to build it reproducibly and
to render with it:

| | |
|---|---|
| `scripts/thirdparty/` | Builds 19 third-party libraries for aarch64, patches 1, links 3 system libraries and generates 9 placeholders. 4 minutes on the Spark. Downloads pinned by SHA-256 or commit. |
| `scripts/apply_engine_changes.py` | 4 engine changes, including a fix for Nanite meshes that never stream in past their coarsest level |
| `tools/make_stub.py` | Placeholders for x86-only libraries that do not export C/C++ runtime symbols (exporting them crashes unrelated libraries) |
| `tools/run_editor_xvfb.sh`, `tools/xshot.py` | Run the editor with its real renderer from an SSH session and take screenshots |
| `tools/bench_game.sh` | Frame-time measurement with the engine's FPS chart |
| `examples/` | Test project and scripts that drive the editor through Remote Control |

## Results

Measured on 2026-11-16, DGX Spark, NVIDIA driver 580.159.03, Ubuntu 24.04.4. Development build, `-game` window
at 1920×1080, VSync off; 40 s warm-up, then 60 s recorded with `tools/bench_game.sh`.

| Scene | Average fps | GPU frame time | 60 fps syncs missed | Hitches |
|---|---|---|---|---|
| Open World template map (Lumen, volumetric clouds) | 86.4 | 8.35 ms | 0 % | 0 |
| Lumen test room (one point light, bounce lighting) | 118.7 | 5.25 ms | 0 % | 0 |
| 1600 instances of a 32k-vertex Nanite mesh, sun + sky light | 80.3 | 9.20 ms | 0 % | 0 |

![The three measured views](docs/img/bench_views.jpg)

| Feature | State |
|---|---|
| Editor window and viewport, Vulkan SM5 and SM6 | works |
| Lumen, software ray tracing | works ([before/after](docs/img/gb10_lumen_on_off.jpg)) |
| Nanite | works with the streaming fix ([before/after](docs/img/gb10_nanite_before_after_fix.jpg)) |
| `-game` from the editor binary | works with the two `-game` changes |
| FBX, Bink audio encoding, Steam, EOS, OpenXR, OpenCV, PROJ, libvpx, coremod | placeholders — **do not work** |
| Cooking and packaging, Play-in-Editor, hardware ray tracing | not tested |

Details and known problems: [docs/RESULTS.md](docs/RESULTS.md).

## Build

Requirements: aarch64 Ubuntu 24.04, an Epic Games account linked to GitHub (for the engine source), 140 GB of free
disk space.

**1. Packages, compiler links, .NET**

```bash
sudo apt-get install -y clang-18 clang-tools-18 libc++-18-dev libc++abi-18-dev lld-18 build-essential cmake \
    ninja-build python3 libfontconfig-dev libfreeimage-dev libsndfile1 libxml2-dev vulkan-tools xvfb x11-apps python3-pil
mkdir -p ~/llvm18-bin && for t in clang clang++ ld.lld lld llvm-ar llvm-ranlib llvm-nm llvm-objcopy llvm-strip; do
    ln -sf /usr/bin/$t-18 ~/llvm18-bin/$t; done          # UnrealBuildTool looks for unversioned names
curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
bash /tmp/dotnet-install.sh --channel 8.0 --arch arm64 --install-dir ~/.dotnet
bash /tmp/dotnet-install.sh --channel 6.0 --runtime dotnet --arch arm64 --install-dir ~/.dotnet
bash /tmp/dotnet-install.sh --channel 6.0 --runtime aspnetcore --arch arm64 --install-dir ~/.dotnet
export DOTNET_ROOT=$HOME/.dotnet PATH=$HOME/llvm18-bin:$HOME/.dotnet:$PATH
```

**2. Engine source, port patch, engine changes**

```bash
git clone --branch 5.4 https://github.com/EpicGames/UnrealEngine.git ~/UnrealEngine
git -C ~/UnrealEngine checkout 847de5e2553adeb4d3498953604d0b0abe669780
git clone https://github.com/MrQbit/unreal-dgx.git ~/unreal-dgx
git -C ~/unreal-dgx checkout c5e8a776c3fe6a5bc0585c223be4c2ad4d732154
echo "eae0c885ad6c41d8bf941b4f21e66dce786d323c0e833ce5beb41f3d3b513506  $HOME/unreal-dgx/patches/unreal-engine-5.4-aarch64.patch" | sha256sum -c
git -C ~/UnrealEngine apply ~/unreal-dgx/patches/unreal-engine-5.4-aarch64.patch
git clone https://github.com/JimmyToluene/ue5-dgx-spark.git ~/ue5-dgx-spark
python3 ~/ue5-dgx-spark/scripts/apply_engine_changes.py ~/UnrealEngine
```

**3. Engine dependencies** (19 GB download, 80 GB on disk)

```bash
cd ~/UnrealEngine
dotnet publish Engine/Source/Programs/GitDependencies/GitDependencies.csproj -c Release -r linux-arm64 \
    --self-contained true -p:PublishTrimmed=false -o Engine/Binaries/DotNET/GitDependencies/linux-arm64
bash Engine/Build/BatchFiles/Linux/GitDependencies.sh --force
```

This ends with an error for one file, a licence PDF that Epic's server refuses (HTTP 403). The build does not use it.

**4. Third-party libraries**

```bash
UE_ROOT=~/UnrealEngine ~/ue5-dgx-spark/scripts/thirdparty/build_all.sh
```

**5. Editor** (33 minutes on the Spark)

```bash
cd ~/UnrealEngine
UE_ARM64_MINIMAL_EDITOR=1 ./Engine/Build/BatchFiles/Linux/Build.sh UnrealEditor Linux Development -ForceUseSystemCompiler
```

**6. Run**

```bash
~/ue5-dgx-spark/tools/run_editor_xvfb.sh ~/ue5-dgx-spark/examples/project/GB10Test.uproject
python3 ~/ue5-dgx-spark/tools/xshot.py :98 editor.png
```

The first start compiles shaders for about 4 minutes. On a machine with a monitor, run
`Engine/Binaries/Linux/UnrealEditor` directly instead.

## Limitations

- Verified on one DGX Spark. The scripts were run end to end on a prepared engine tree; a run from a fresh clone
  has not been done yet.
- The measured scenes are test scenes, not production content.
- Known problems, including a render-graph crash that appeared only while Nanite streaming was stalled:
  [docs/RESULTS.md](docs/RESULTS.md#known-problems).

## Credit

If you use, adapt or redistribute this work, credit **JimmyToluene** (<https://github.com/JimmyToluene>) and link
this repository. The required attribution is in [`NOTICE`](NOTICE); GitHub's "Cite this repository" button uses
[`CITATION.cff`](CITATION.cff).

The engine port patch is the work of [MrQbit](https://github.com/MrQbit/unreal-dgx). Unreal Engine is © Epic Games.

## Licence

- Code: [Apache License 2.0](LICENSE). Redistributions and derivative works must keep the [`NOTICE`](NOTICE) file.
- Documentation and images (`docs/`, `README.md`): [CC BY 4.0](LICENSE-docs). Reuse requires credit.
- No Unreal Engine source is included. `scripts/apply_engine_changes.py` contains only the new lines and one
  short anchor line per change. Unreal Engine is covered by Epic's EULA.
- The port patch is not redistributed; step 2 downloads it from its own repository.
- The libraries built by the scripts keep their own licences.
