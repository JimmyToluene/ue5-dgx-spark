#!/bin/bash
# All aarch64 third-party work for the UE 5.4 editor, in order. Run after applying the main patch and
# fetching GitDependencies (README.md steps 1-3), before building UnrealEditor (README.md step 5).
#
#   UE_ROOT=~/UnrealEngine scripts/thirdparty/build_all.sh
#
# Re-runnable. Logs: $UE_TP_WORK/logs (default ~/ue-arm64-thirdparty/logs). Downloads (METIS, Draco, ispc,
# Embree; about 120 MB) go to $UE_TP_WORK/downloads and are checked against fixed hashes / commits.
D=$(dirname "$0")
rc=0
bash "$D/build_intree.sh"      || rc=1
bash "$D/build_downloaded.sh"  || rc=1
bash "$D/make_placeholders.sh" || rc=1
[ $rc -eq 0 ] && echo "all third-party steps done" || echo "some steps failed — see the !! lines above"
exit $rc
