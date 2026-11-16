#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 JimmyToluene (https://github.com/JimmyToluene)
#
# Frame-time measurement of one level as a 1920x1080 -game window (VSync off, no frame cap) on the GB10.
# Starts the game from the editor binary on Xvfb, waits WARM seconds, records SECS seconds with the engine's
# own FPS chart (startfpschart / stopfpschart, sent through Remote Control), prints the summary, and quits.
# The project must enable the RemoteControl plugin (see examples/project).
#
#   tools/bench_game.sh /path/to/Project.uproject /Game/Maps/MyLevel [WARM=40] [SECS=60]
#
# Env: UE_ROOT (default ~/UnrealEngine), DISPLAY_NUM (default 98), LOG (default /tmp/ue_bench.log)
set -u
PROJECT=${1:?usage: bench_game.sh <Project.uproject> <map> [warm] [secs]}; MAP=${2:?map}
WARM=${3:-40}; SECS=${4:-60}
UE_ROOT=${UE_ROOT:-$HOME/UnrealEngine}; N=${DISPLAY_NUM:-98}; LOG=${LOG:-/tmp/ue_bench.log}
RC=http://127.0.0.1:30010/remote/object/call

xdpyinfo -display ":$N" >/dev/null 2>&1 || { nohup Xvfb ":$N" -screen 0 1920x1080x24 -nolisten tcp >/dev/null 2>&1 & sleep 2; }
export DISPLAY=":$N" VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json SDL_VIDEODRIVER=x11 DOTNET_ROOT=${DOTNET_ROOT:-$HOME/.dotnet}
cd "$UE_ROOT/Engine/Binaries/Linux"
./UnrealEditor "$PROJECT" "$MAP" -game -windowed -ResX=1920 -ResY=1080 -vulkan -nosplash -unattended -nopause \
    -RCWebControlEnable -ExecCmds="r.VSync 0,t.MaxFPS 0" -abslog="$LOG" > /dev/null 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null' EXIT

console() {
    curl -s -m 60 -X PUT "$RC" -H 'Content-Type: application/json' \
        -d "{\"objectPath\":\"/Script/Engine.Default__KismetSystemLibrary\",\"functionName\":\"ExecuteConsoleCommand\",\"parameters\":{\"Command\":\"$1\"}}" > /dev/null
}
for i in $(seq 1 900); do
    curl -s -m 2 -o /dev/null http://127.0.0.1:30010/remote/info && break
    kill -0 $PID 2>/dev/null || { echo "the game exited during start-up — see $LOG"; exit 1; }
    sleep 1
done
echo "running; warming up ${WARM}s, then recording ${SECS}s"
sleep "$WARM"; console startfpschart
sleep "$SECS"; console stopfpschart
sleep 3
grep -E "frames collected|Average (GPU|RenderThread|GameThread) frametime|Target (60|120) FPS|Total hitch" "$LOG" \
    | sed -E 's/^\[[^]]*\]\[[ 0-9]*\]LogChartCreation: //'
