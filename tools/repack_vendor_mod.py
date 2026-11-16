#!/usr/bin/env python3
"""
Lenovo Tab M11 (TB311FU / 'poplar') Deep Dynamic Partition Modding Tool
Automated EROFS extraction, hardware asset injection, and LZ4 recompilation for /vendor.
"""

import os
import sys
import subprocess
import shutil

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
FEARLESS_DIR = os.path.abspath(r"C:\Users\BangerSoul\Documents\antigravity\fearless-maxwell")
GSI_SUITE_DIR = os.path.join(FEARLESS_DIR, "gsi_suite")

WIFI_ONLY_PROPS = """
# TB311FU Wi-Fi Only Power & Telephony Drain Fix
ro.radio.noril=yes
ro.carrier=wifi-only
ro.telephony.default_network=0
telephony.lteOnCdmaDevice=0

# SurfaceFlinger Display Optimization
debug.sf.latch_unsignaled=1
ro.surface_flinger.has_wide_color_display=true
ro.surface_flinger.has_HDR_display=false
ro.surface_flinger.max_frame_buffer_acquired_buffers=3
"""

def run_cmd(cmd, check=True):
    print(f"[*] Executing: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"[!] Command failed (code {res.returncode}):")
        print(res.stderr or res.stdout)
        sys.exit(res.returncode)
    return res

def run_adb(adb_cmd, check=True):
    return run_cmd(f"adb {adb_cmd}", check=check)

def run_adb_su(sh_cmd, check=True):
    escaped = sh_cmd.replace('"', '\\"')
    return run_cmd(f'adb shell "su -c \\"{escaped}\\""', check=check)

def main():
    print("=" * 70)
    print("TB311FU ('poplar') Dynamic Partition Modder: Vendor EROFS Stabilizer")
    print("=" * 70)

    # 1. Device check
    print("\n[Phase 1] Verifying connected device...")
    dev_out = run_adb("devices").stdout
    if "device" not in dev_out:
        print("[!] No ADB device detected. Ensure USB debugging is active.")
        sys.exit(1)

    disp = run_adb('shell "getprop ro.build.display.id"').stdout.strip()
    root_id = run_adb_su("id").stdout.strip()
    print(f"[+] Device Connected: {disp}")
    print(f"[+] Root Context: {root_id}")

    # 2. Stage workspace directories on device
    print("\n[Phase 2] Staging device temp workdirs...")
    run_adb_su("rm -rf /data/local/tmp/vendor_mod && mkdir -p /data/local/tmp/vendor_mod/extract")

    # 3. Dump baseline vendor_a
    print("\n[Phase 3] Dumping /dev/block/mapper/vendor_a...")
    run_adb_su("dd if=/dev/block/mapper/vendor_a of=/data/local/tmp/vendor_mod/vendor_stock.img bs=4M")
    stock_size = run_adb_su("stat -c%s /data/local/tmp/vendor_mod/vendor_stock.img").stdout.strip()
    print(f"[+] Baseline vendor dumped successfully ({stock_size} bytes)")

    # 4. Extract EROFS filesystem
    print("\n[Phase 4] Extracting EROFS filesystem on device via fsck.erofs...")
    run_adb_su("fsck.erofs --extract=/data/local/tmp/vendor_mod/extract /data/local/tmp/vendor_mod/vendor_stock.img")
    print("[+] Extraction complete.")

    # 5. Inject Hardware Stabilization Stack
    print("\n[Phase 5] Injecting Full Hardware Stabilization Stack...")

    # 5A. IDC files
    print("  -> Injecting Lenovo AP500U pen digitizer IDC files...")
    run_adb_su("mkdir -p /data/local/tmp/vendor_mod/extract/usr/idc")
    for idc in ["himax-touchscreen.idc", "NVT-ts.idc", "touch_tuning.conf"]:
        src = os.path.join(GSI_SUITE_DIR, "stylus", idc)
        if os.path.exists(src):
            run_adb(f'push "{src}" /data/local/tmp/vendor_mod/extract/usr/idc/{idc}')
            run_adb_su(f"chmod 644 /data/local/tmp/vendor_mod/extract/usr/idc/{idc}")
            print(f"     [+] Injected {idc}")

    # 5B. Discrete Quad Audio Policies
    print("  -> Injecting Discrete Quad-Speaker Audio Policies...")
    run_adb_su("mkdir -p /data/local/tmp/vendor_mod/extract/etc/audio")
    audio_policy = os.path.join(GSI_SUITE_DIR, "audio", "audio_policy_configuration.xml")
    audio_effects = os.path.join(GSI_SUITE_DIR, "audio", "audio_effects.xml")

    if os.path.exists(audio_policy):
        run_adb(f'push "{audio_policy}" /data/local/tmp/vendor_mod/extract/etc/audio_policy_configuration.xml')
        run_adb(f'push "{audio_policy}" /data/local/tmp/vendor_mod/extract/etc/audio/audio_policy_configuration.xml')
        run_adb_su("chmod 644 /data/local/tmp/vendor_mod/extract/etc/audio_policy_configuration.xml")
        run_adb_su("chmod 644 /data/local/tmp/vendor_mod/extract/etc/audio/audio_policy_configuration.xml")
        print("     [+] Injected audio_policy_configuration.xml")

    if os.path.exists(audio_effects):
        run_adb(f'push "{audio_effects}" /data/local/tmp/vendor_mod/extract/etc/audio_effects.xml')
        run_adb_su("chmod 644 /data/local/tmp/vendor_mod/extract/etc/audio_effects.xml")
        print("     [+] Injected audio_effects.xml")

    # 5C. Wi-Fi Only & Display Properties
    print("  -> Appending Wi-Fi Only & SurfaceFlinger properties to build.prop...")
    local_props_file = os.path.join(WORKSPACE_DIR, "wifi_only_props.txt")
    with open(local_props_file, "w", encoding="utf-8") as f:
        f.write(WIFI_ONLY_PROPS)
    run_adb(f'push "{local_props_file}" /data/local/tmp/vendor_mod/props.txt')
    run_adb_su("cat /data/local/tmp/vendor_mod/props.txt >> /data/local/tmp/vendor_mod/extract/build.prop")
    os.remove(local_props_file)
    print("     [+] Appended telemetry and performance properties.")

    # 6. Recompile EROFS
    print("\n[Phase 6] Recompiling stabilized EROFS image (LZ4 compressed)...")
    run_adb_su(
        "mkfs.erofs -zlz4 --mount-point=/vendor "
        "/data/local/tmp/vendor_mod/vendor_stabilized.img "
        "/data/local/tmp/vendor_mod/extract"
    )
    new_size = run_adb_su("stat -c%s /data/local/tmp/vendor_mod/vendor_stabilized.img").stdout.strip()
    print(f"[+] Recompilation complete! New image size: {new_size} bytes")

    # 7. Pull back to PC
    out_img = os.path.join(WORKSPACE_DIR, "vendor_stabilized.img")
    print(f"\n[Phase 7] Pulling generated image to {out_img}...")
    run_adb(f'pull /data/local/tmp/vendor_mod/vendor_stabilized.img "{out_img}"')
    
    # 8. Clean up on device
    run_adb_su("rm -rf /data/local/tmp/vendor_mod/extract /data/local/tmp/vendor_mod/vendor_stock.img")

    print("\n" + "=" * 70)
    print("SUCCESS: vendor_stabilized.img generated successfully!")
    print("=" * 70)
    print("\nTo flash this image to your tablet:")
    print("  1. adb reboot fastboot")
    print(f"  2. fastboot -S 64M flash vendor_a \"{out_img}\"")
    print("  3. fastboot reboot")
    print("\nSafety note: If recovery is ever needed, BROM restore via mtkclient is available.")

if __name__ == "__main__":
    main()
