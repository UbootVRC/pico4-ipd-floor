#!/usr/bin/env python3
"""Patch a stock libpxrhmdservice.so (PICO OS 5.13.7) on a PC.

Reference implementation of the same edits module/customize.sh makes on the
headset. Useful for checking the patch or porting it to another firmware.

    adb pull /system/lib64/libpxrhmdservice.so stock.so
    python tools/patch_lib.py stock.so patched.so
"""
import hashlib
import struct
import sys

STOCK_SHA = "c290a9f51214ff37b415c309c5facf80542024d40c22e5ae3cdeff9825a31fef"
PATCHED_SHA = "09888ce082ede4f71b96d99f80bb0025439e0fc47c2dcea9e5b70e3b4bd565a2"

OLD_MIN, NEW_MIN, MAX = 6200, 5700, 7200  # units of 0.01 mm


def movn_w(rd, value):
    """mov wN, #value for a negative value (MOVN encoding)."""
    return 0x12800000 | ((~value & 0xFFFF) << 5) | rd


def cmp_w_imm(rn, imm):
    return 0x7100001F | (imm << 10) | (rn << 5)


# (file offset, old bytes, new bytes, what it is). In this build the file
# offsets of .text and .rodata equal their virtual addresses.
EDITS = []
for site, name in ((0x2FD84, "ipd_result_cb"), (0x3116C, "IPDMoveCallback")):
    EDITS.append((site, struct.pack("<I", movn_w(8, -OLD_MIN)),
                  struct.pack("<I", movn_w(8, -NEW_MIN)), f"{name}: lower bound"))
    EDITS.append((site + 8, struct.pack("<I", cmp_w_imm(8, MAX - OLD_MIN)),
                  struct.pack("<I", cmp_w_imm(8, MAX - NEW_MIN)), f"{name}: range width"))
EDITS += [
    (0x17CB8, struct.pack("<f", 62.0), struct.pack("<f", 57.0), "auto-IPD clamp, mm (float)"),
    (0x17C28, struct.pack("<d", 62.0), struct.pack("<d", 57.0), "auto-IPD clamp, mm (double, log only)"),
    (0x17CA4, struct.pack("<f", 6200.0), struct.pack("<f", 5700.0), "auto-IPD clamp, 0.01 mm (float)"),
]


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())
    sha = hashlib.sha256(data).hexdigest()
    if sha != STOCK_SHA:
        sys.exit(f"Not the supported stock library (sha256 {sha}).")
    for off, old, new, what in EDITS:
        if data[off:off + len(old)] != old:
            sys.exit(f"Unexpected bytes at {off:#x} ({what}).")
        data[off:off + len(new)] = new
        print(f"{off:#07x}  {old.hex()} -> {new.hex()}  {what}")
    out = hashlib.sha256(data).hexdigest()
    assert out == PATCHED_SHA, out
    open(dst, "wb").write(data)
    print(f"Wrote {dst} (sha256 {out})")


if __name__ == "__main__":
    main()
