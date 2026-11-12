#!/usr/bin/env python3
"""Zip module/ into a Magisk-flashable build/pico4-ipd-floor.zip."""
import pathlib
import zipfile

root = pathlib.Path(__file__).resolve().parent
src = root / "module"
out = root / "build" / "pico4-ipd-floor.zip"
out.parent.mkdir(exist_ok=True)

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        # Shell scripts must keep LF line endings regardless of checkout settings.
        data = path.read_bytes().replace(b"\r\n", b"\n")
        info = zipfile.ZipInfo(path.relative_to(src).as_posix(), (2020, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, data)

print(f"Wrote {out.relative_to(root)}")
