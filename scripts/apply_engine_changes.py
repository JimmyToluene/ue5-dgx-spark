#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 JimmyToluene (https://github.com/JimmyToluene)
"""Apply the four engine changes this repository needs on top of the port patch (see docs/ENGINE_CHANGES.md).

    python3 scripts/apply_engine_changes.py ~/UnrealEngine            apply (safe to run again)
    python3 scripts/apply_engine_changes.py ~/UnrealEngine --check    only report the state of each change

Each change is found by one anchor line in Epic's file and marked with "ue5-dgx-spark", so a second run skips
changes that are already there. If an anchor is not found exactly once, nothing in that file is touched.
"""
import os
import sys

MARK = "ue5-dgx-spark"

EMBREE = (
    "\t\telse if (Target.IsInPlatformGroup(UnrealPlatformGroup.Unix) && Target.Architecture == UnrealArch.Arm64)\n"
    "\t\t{\n"
    "\t\t\t// ue5-dgx-spark: Embree 3.13.5 built for aarch64 by scripts/thirdparty/build_downloaded.sh embree\n"
    "\t\t\tstring Lib = Path.Combine(Target.UEThirdPartyBinariesDirectory, \"Intel/Embree/Embree3135/Linux/aarch64-unknown-linux-gnueabi/lib\");\n"
    "\t\t\tPublicSystemIncludePaths.Add(Path.Combine(Target.UEThirdPartySourceDirectory, \"Intel/Embree/Embree3135/Linux/aarch64-unknown-linux-gnueabi/include\"));\n"
    "\t\t\tPublicAdditionalLibraries.Add(Path.Combine(Lib, \"libembree3.so\"));\n"
    "\t\t\tRuntimeDependencies.Add(Path.Combine(Lib, \"libembree3.so\"));\n"
    "\t\t\tRuntimeDependencies.Add(Path.Combine(Lib, \"libembree3.so.3\"));\n"
    "\t\t\tPublicDefinitions.Add(\"USE_EMBREE=1\");\n"
    "\t\t}\n")

NANITE_OLD = ("\t\t\tRootPageInfo.MaxHierarchyDepth = PageStreamingState.MaxHierarchyDepth;\n"
              "\t\t\tHierarchyDepthManager.Add(PageStreamingState.MaxHierarchyDepth);\n")
NANITE_NEW = (
    "\t\t\t// ue5-dgx-spark: count the deepest hierarchy level of the whole resource, not only the root page's.\n"
    "\t\t\t// Otherwise a page whose requesting leaves sit deeper than every installed page is never requested and\n"
    "\t\t\t// the mesh stays at its coarsest level (fixed by Epic on the builder side in 5.7).\n"
    "\t\t\tuint8 ResourceMaxDepth = PageStreamingState.MaxHierarchyDepth;\n"
    "\t\t\tfor (const FPageStreamingState& AnyPage : Resources->PageStreamingStates)\n"
    "\t\t\t{\n"
    "\t\t\t\tResourceMaxDepth = FMath::Max(ResourceMaxDepth, AnyPage.MaxHierarchyDepth);\n"
    "\t\t\t}\n"
    "\t\t\tRootPageInfo.MaxHierarchyDepth = ResourceMaxDepth;\n"
    "\t\t\tHierarchyDepthManager.Add(ResourceMaxDepth);\n")

TPM_OLD = "\t\t\t\tif (PlatformName != FPlatformProperties::IniPlatformName())\n"
TPM_NEW = (
    "\t\t\t\t// ue5-dgx-spark: on an aarch64 editor IniPlatformName() is \"LinuxArm64\", but the running platform of an\n"
    "\t\t\t\t// editor binary (\"LinuxEditor\") comes from the \"Linux\" module; without it -game asserts.\n"
    "\t\t\t\tbool bIsHostEditorPlatform = false;\n"
    "#if PLATFORM_LINUX && PLATFORM_CPU_ARM_FAMILY\n"
    "\t\t\t\tbIsHostEditorPlatform = (PlatformName == FName(TEXT(\"Linux\")));\n"
    "#endif\n"
    "\t\t\t\tif (PlatformName != FPlatformProperties::IniPlatformName() && !bIsHostEditorPlatform)\n")


def change_embree(s):
    anchor = 'PublicDefinitions.Add("USE_EMBREE=0");'
    if s.count(anchor) != 1:
        return None
    at = s.rfind("\t\telse\n", 0, s.index(anchor))
    return None if at < 0 else s[:at] + EMBREE + s[at:]


def change_nanite(s):
    return s.replace(NANITE_OLD, NANITE_NEW) if s.count(NANITE_OLD) == 1 else None


def change_tpm(s):
    return s.replace(TPM_OLD, TPM_NEW) if s.count(TPM_OLD) == 1 else None


def change_ddpi(s):
    a, b = "Linux:bIsEnabled=true\n", "Linux:bUsesHostCompiler=true\n"
    lines = s.splitlines(keepends=True)
    if lines.count(a) != 1 or lines.count(b) != 1:
        return None
    out = []
    for line in lines:
        out.append(line)
        if line == a:
            out.append("; " + MARK + "\nLinuxArm64:bIsEnabled=true\n")
        elif line == b:
            out.append("; " + MARK + "\nLinuxArm64:bUsesHostCompiler=true\n")
    return "".join(out)


CHANGES = [
    ("Embree on arm64", "Engine/Source/ThirdParty/Intel/Embree/Embree3.Build.cs", change_embree),
    ("Nanite streaming depth", "Engine/Source/Runtime/Engine/Private/Rendering/NaniteStreamingManager.cpp", change_nanite),
    ("-game: load the Linux editor platform", "Engine/Source/Developer/TargetPlatform/Private/TargetPlatformManagerModule.cpp", change_tpm),
    ("-game: LinuxArm64 host keys", "Engine/Config/LinuxArm64/DataDrivenPlatformInfo.ini", change_ddpi),
]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root, check_only = os.path.expanduser(sys.argv[1]), "--check" in sys.argv[2:]
    failed = False
    for title, rel, fn in CHANGES:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            print("MISSING  %-40s %s" % (title, rel)); failed = True; continue
        with open(path, newline="") as f:
            s = f.read()
        if MARK in s:
            print("present  %s" % title); continue
        new = fn(s)
        if new is None:
            print("NO MATCH %-40s %s (anchor not found exactly once; file left unchanged)" % (title, rel)); failed = True; continue
        if check_only:
            print("missing  %s" % title); continue
        with open(path, "w", newline="") as f:
            f.write(new)
        print("applied  %s" % title)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
