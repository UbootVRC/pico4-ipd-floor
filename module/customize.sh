# Pico 4 IPD floor fix - Magisk install script.
#
# Copies libpxrhmdservice.so from the running system, checks that it is the
# exact build this patch was written for, and patches it in place. No Pico
# binary ships in this module.

LIB=system/lib64/libpxrhmdservice.so
STOCK_SHA=c290a9f51214ff37b415c309c5facf80542024d40c22e5ae3cdeff9825a31fef
PATCHED_SHA=09888ce082ede4f71b96d99f80bb0025439e0fc47c2dcea9e5b70e3b4bd565a2

sha_of() { sha256sum "$1" | cut -d' ' -f1; }

# poke <file> <decimal offset> <printf-escaped bytes>
poke() {
  printf "$3" | dd of="$1" bs=1 seek="$2" conv=notrunc 2>/dev/null
}

patch_lib() {
  f="$1"
  # ipd_result_cb: range check before saving pxr_ipd_position (6200..7200 -> 5700..7200)
  poke "$f" 195972 '\x68\xc8\x82\x12'   # 0x2fd84  mov w8, #-5700
  poke "$f" 195980 '\x1f\x71\x17\x71'   # 0x2fd8c  cmp w8, #1500
  # IPDMoveCallback: range check before publishing sdk_lens_lensSeparation
  poke "$f" 201068 '\x68\xc8\x82\x12'   # 0x3116c  mov w8, #-5700
  poke "$f" 201076 '\x1f\x71\x17\x71'   # 0x31174  cmp w8, #1500
  # auto-IPD clamp constants
  poke "$f" 97320 '\x00\x00\x00\x00\x00\x80\x4c\x40'  # 0x17c28  62.0  -> 57.0   (double)
  poke "$f" 97444 '\x00\x20\xb2\x45'                  # 0x17ca4  6200f -> 5700f
  poke "$f" 97464 '\x00\x00\x64\x42'                  # 0x17cb8  62f   -> 57f
}

# If an older copy of this module is already mounted, /system shows the
# patched file; that case is handled by the PATCHED_SHA branch below.
SRC=/$LIB

[ -f "$SRC" ] || abort "! $LIB not found - is this a Pico 4?"

mkdir -p "$MODPATH/system/lib64"
cp -f "$SRC" "$MODPATH/$LIB"

have=$(sha_of "$MODPATH/$LIB")
if [ "$have" = "$PATCHED_SHA" ]; then
  ui_print "- Library is already patched, reusing it"
elif [ "$have" = "$STOCK_SHA" ]; then
  ui_print "- Stock library matches (PICO OS 5.13.7), patching"
  patch_lib "$MODPATH/$LIB"
  [ "$(sha_of "$MODPATH/$LIB")" = "$PATCHED_SHA" ] || abort "! Patch result does not match the expected hash"
else
  abort "! Unsupported libpxrhmdservice.so build (sha256 $have). This patch only fits PICO OS 5.13.7."
fi

set_perm_recursive "$MODPATH/system" 0 0 0755 0644
set_perm "$MODPATH/$LIB" 0 0 0644 u:object_r:system_lib_file:s0
ui_print "- Done. Reboot, then adjust IPD once so the new value is published."
