# Examples

`project/GB10Test.uproject` is the test project used for the results: Vulkan SM6, Lumen, Nanite, and the Remote
Control HTTP API on 127.0.0.1:30010. The scripts drive a running editor through that API (no mouse needed).

Reproduce the two test scenes and their measurements:

```bash
~/ue5-dgx-spark/tools/run_editor_xvfb.sh ~/ue5-dgx-spark/examples/project/GB10Test.uproject &
# wait until the editor is up: curl -s http://127.0.0.1:30010/remote/info answers
cd ~/ue5-dgx-spark/examples
python3 make_lumen_room.py              # /Game/Test/LumenRoom: closed room, one light, fixed exposure
python3 make_nanite_grid.py nanite 40   # /Game/Test/Grid_nanite: 1600 instances of a Nanite copy of an engine mesh
pkill -x UnrealEditor
P=~/ue5-dgx-spark/examples/project/GB10Test.uproject
~/ue5-dgx-spark/tools/bench_game.sh $P /Game/Test/LumenRoom
~/ue5-dgx-spark/tools/bench_game.sh $P /Game/Test/Grid_nanite
```

Both scripts replace a level of the same name if it exists, and place a `PlayerStart` that fixes the camera used by
`bench_game.sh`. `rc.py` is a small client for the Remote Control API (`call`, `cmd`, `get`, `set`, `spawn_mesh`,
`camera`, `new_level`).
