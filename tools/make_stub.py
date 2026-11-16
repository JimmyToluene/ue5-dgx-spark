#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 JimmyToluene (https://github.com/JimmyToluene)
"""Build an aarch64 placeholder for an x86-64-only library.

The placeholder exports the same function and data names as the original, so aarch64 code that links against
it resolves, but every function returns 0 and every data object is zero-filled: the feature it stands for does
NOT work. Use it only for optional engine features that have no aarch64 build (FBX SDK, Steam, EOS, ...).

    make_stub.py ORIGINAL OUTPUT        ORIGINAL: x86-64 .so / .a     OUTPUT: .so or .a (chosen by OUTPUT's name)

Never exported: names that the system C/C++ runtime libraries define, and the C++ runtime families
(std::, operator new/delete, __cxa_*, unwinder ...). Some x86 libraries carry copies of those (libfbxsdk.so ships
~430). A placeholder exporting them as "return 0" would interpose them for the whole process, and every other
library that relies on the GNU C++ runtime would then call the dummy — in UE that showed up as Embree crashing in
its static initialisers as soon as the editor loaded it.

Tools: llvm-nm (NM, default llvm-nm-18), clang (CLANG, default clang-18), llvm-ar (AR, default llvm-ar-18).
"""
import os
import re
import subprocess
import sys
import tempfile

NM = os.environ.get("NM", "llvm-nm-18")
CLANG = os.environ.get("CLANG", "clang-18")
AR = os.environ.get("AR", "llvm-ar-18")

SYSTEM_LIBS = ["libc.so.6", "libm.so.6", "libgcc_s.so.1", "libstdc++.so.6", "libc++.so.1", "libc++abi.so.1",
               "libz.so.1", "libdl.so.2", "libpthread.so.0", "librt.so.1"]
SYSTEM_DIR = "/lib/aarch64-linux-gnu"
RUNTIME = re.compile(r"^(_ZNK?St|_ZSt|_ZT[ISVT]N?K?St|_ZGVZ?NK?St|_Zn[wa]|_Zd[la]|__cxa_|__gxx_|__cxx|_Unwind_|__gnu_"
                     r"|_ZNK?9__gnu_cxx|_ZT[ISV]N9__gnu_cxx|_ZN10__cxxabiv|_ZT[ISV]N10__cxxabiv|__aarch64_|__libc_"
                     r"|__stack_chk)")
LINKER_OWNED = {"_DYNAMIC", "_GLOBAL_OFFSET_TABLE_", "_edata", "_end", "__bss_start", "_init", "_fini", "_start",
                "__data_start", "__dso_handle", "_IO_stdin_used", "__TMC_END__"}
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
FUNC_KINDS, DATA_KINDS = set("TWi"), set("DBGSVR")


def defined_symbols(path, dynamic):
    """{name: kind letter} of the global symbols a library defines (version suffixes removed)."""
    cmd = [NM, "--defined-only", "--extern-only"] + (["-D"] if dynamic else []) + [path]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    syms = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        kind, name = parts[1], parts[2].split("@")[0]
        syms.setdefault(name, kind)
    return syms


def is_archive(path):
    with open(path, "rb") as f:
        return f.read(8) == b"!<arch>\n"


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    system = set()
    for lib in SYSTEM_LIBS:
        p = os.path.join(SYSTEM_DIR, lib)
        if os.path.exists(p):
            system.update(defined_symbols(p, dynamic=True))

    syms = defined_symbols(src, dynamic=not is_archive(src))
    keep, dropped = {}, 0
    for name, kind in syms.items():
        if (not IDENT.match(name) or name in LINKER_OWNED or name.startswith("_GLOBAL__sub_I")
                or name in system or RUNTIME.match(name)):
            dropped += 1
            continue
        k = kind.upper() if kind != "i" else "i"
        if k in FUNC_KINDS or k in DATA_KINDS:
            keep[name] = k
    if not keep:
        sys.exit("no exportable symbols found in %s" % src)

    lines = [".text"]
    for name in sorted(n for n, k in keep.items() if k in FUNC_KINDS):
        lines += [".globl %s" % name, ".type %s,@function" % name, "%s:" % name, "\tmov x0, #0", "\tret"]
    lines.append(".data")
    for name in sorted(n for n, k in keep.items() if k in DATA_KINDS):
        lines += [".globl %s" % name, ".type %s,@object" % name, ".p2align 4", "%s:" % name, "\t.zero 64"]

    with tempfile.TemporaryDirectory() as tmp:
        asm, obj = os.path.join(tmp, "stub.s"), os.path.join(tmp, "stub.o")
        with open(asm, "w") as f:
            f.write("\n".join(lines) + "\n")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        tmp_out = os.path.join(tmp, os.path.basename(out))
        if out.endswith(".a"):
            subprocess.run([CLANG, "-c", "-fPIC", asm, "-o", obj], check=True)
            subprocess.run([AR, "rcs", tmp_out, obj], check=True)
        else:
            subprocess.run([CLANG, "-shared", "-fPIC", "-nostdlib", "-Wl,-soname," + os.path.basename(out), asm,
                            "-o", tmp_out], check=True)
        with open(tmp_out, "rb") as fi, open(out, "wb") as fo:
            fo.write(fi.read())
    nfunc = sum(1 for k in keep.values() if k in FUNC_KINDS)
    print("placeholder %s: %d functions, %d data objects, %d runtime/system/reserved names left out"
          % (os.path.basename(out), nfunc, len(keep) - nfunc, dropped))


if __name__ == "__main__":
    main()
