#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 JimmyToluene (https://github.com/JimmyToluene)
# Run the aarch64 editor WITH its real Vulkan renderer on a virtual X display, so the window and viewport
# can be checked (and screenshotted) from an SSH session or a coding harness, without the DGX console.
# The NVIDIA driver renders on the GB10 under Xvfb when the Vulkan loader is pointed at the NVIDIA ICD.
#
#   tools/run_editor_xvfb.sh /path/to/Project.uproject [map] [extra editor args]
#   python3 tools/xshot.py :98 shot.png            # screenshot of the whole virtual screen
#
# Needs: apt install xvfb x11-apps (for xwd); python3-pil for xshot.py.
# Env: UE_ROOT (default ~/UnrealEngine), DISPLAY_NUM (default 98), LOG (default /tmp/ue_editor_xvfb.log)
set -u
UE_ROOT=${UE_ROOT:-$HOME/UnrealEngine}
PROJECT=${1:?usage: run_editor_xvfb.sh <Project.uproject> [map] [args]}; shift
N=${DISPLAY_NUM:-98}
LOG=${LOG:-/tmp/ue_editor_xvfb.log}
ICD=/usr/share/vulkan/icd.d/nvidia_icd.json
[ -f "$ICD" ] || { echo "no $ICD — is the NVIDIA driver's Vulkan ICD installed?"; exit 1; }

if ! xdpyinfo -display ":$N" >/dev/null 2>&1; then
    nohup Xvfb ":$N" -screen 0 1920x1080x24 -nolisten tcp > /tmp/xvfb_$N.log 2>&1 &
    for i in $(seq 1 20); do xdpyinfo -display ":$N" >/dev/null 2>&1 && break; sleep 0.5; done
fi

export DISPLAY=":$N" VK_ICD_FILENAMES="$ICD" SDL_VIDEODRIVER=x11
export DOTNET_ROOT=${DOTNET_ROOT:-$HOME/.dotnet}
cd "$UE_ROOT/Engine/Binaries/Linux"
echo "editor on DISPLAY=:$N, log $LOG (first start compiles shaders for several minutes)"
exec ./UnrealEditor "$PROJECT" "$@" -vulkan -nosplash -unattended -nopause -stdout -ResX=1920 -ResY=1080 -abslog="$LOG"
