# Pico 4 IPD floor fix

A Magisk module that lets a rooted Pico 4 report an IPD below 62 mm to apps.

## The problem

The Pico 4's lens motor can physically go down to roughly 58 mm, and the
settings slider lets you move it there. But every app, and anything streaming
to a PC (SteamVR and so on), still sees 62 mm as the minimum.

The cause is a hard-coded range check in Pico's HMD service
(`/system/lib64/libpxrhmdservice.so`):

- When a lens move finishes, `IPDMoveCallback` only publishes the new value
  (`sdk_lens_lensSeparation`, which the compositor and apps read) if the motor
  position is between 62.00 and 72.00 mm. Anything lower is dropped silently,
  so everything keeps the last value at or above 62 mm.
- The eye-tracking auto-IPD callback (`ipd_result_cb`) clamps results under
  62 mm up to 62 mm and applies the same range check before saving.

## The fix

The module lowers that floor from 62 mm to 57 mm. The 72 mm ceiling is left
alone. It changes 15 bytes:

| Offset    | Stock                | Patched              | Meaning                              |
|-----------|----------------------|----------------------|--------------------------------------|
| `0x2fd84` | `mov w8, #-6200`     | `mov w8, #-5700`     | `ipd_result_cb` lower bound          |
| `0x2fd8c` | `cmp w8, #1000`      | `cmp w8, #1500`      | `ipd_result_cb` range width          |
| `0x3116c` | `mov w8, #-6200`     | `mov w8, #-5700`     | `IPDMoveCallback` lower bound        |
| `0x31174` | `cmp w8, #1000`      | `cmp w8, #1500`      | `IPDMoveCallback` range width        |
| `0x17cb8` | `62.0f`              | `57.0f`              | auto-IPD clamp (mm)                  |
| `0x17c28` | `62.0` (double)      | `57.0`               | same clamp, value used in the log    |
| `0x17ca4` | `6200.0f`            | `5700.0f`            | auto-IPD clamp (0.01 mm)             |

No Pico binary is included in this repository. The module copies the library
from your own headset at install time, checks its SHA-256, and patches the
copy. Magisk then overlays it; `/system` itself is never modified.

## Compatibility

Only **PICO OS 5.13.7** on the Pico 4 / Pico 4 Enterprise (stock library
SHA-256 `c290a9f5…a31fef`). The installer refuses any other build. After a
firmware update, remove the module; the patch has to be ported to the new
library before it can be used again.

## Install

1. Build the zip: `python build.py` (writes `build/pico4-ipd-floor.zip`).
2. Copy it to the headset and install it in the Magisk app, or:

   ```bash
   adb push build/pico4-ipd-floor.zip /data/local/tmp/
   adb shell su -c "magisk --install-module /data/local/tmp/pico4-ipd-floor.zip"
   ```

3. Reboot.
4. Move the IPD slider once. The reported value only refreshes when a lens
   move finishes, so until then apps still see the old one.

To check it worked, watch the log while adjusting IPD below 62 mm:

```bash
adb logcat | grep -E "sdk_lens_lensSeparation|hard ipd notify"
```

You should see values like `0.058010` instead of nothing.

## Uninstall

Disable or remove the module in the Magisk app and reboot. If the headset ever
fails to reach the home screen with the module installed, adb still works:

```bash
adb shell su -c "rm -rf /data/adb/modules/pico4-ipd-floor"
adb reboot
```

## Caveats

- Pico officially supports 62–72 mm. Lens distortion correction may only be
  calibrated for that range, so image geometry below 62 mm could be slightly
  off even though the eye separation is now correct.
- Whether the sub-62 value survives a reboot without touching the slider
  again has not been confirmed.
- This replaces a system library with a patched copy. Use it at your own risk.

## Porting to another firmware

`tools/patch_lib.py` is a PC-side reference for the same edits, with the
instruction encodings spelled out. To port, find the two
`mov w8, #-0x1838` / `cmp w8, #0x3e8` pairs (next to the strings
`pxr_gd32ipd_position` and `pxr_ipd_position`) and the constants used beside
the log string `set ipd force %f to %f avoid less min`, then update the
offsets and hashes in both `tools/patch_lib.py` and `module/customize.sh`.

## License

MIT, see [LICENSE](LICENSE). This covers the scripts in this repository only; the library they patch belongs to Pico and is not distributed here.
