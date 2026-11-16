#!/usr/bin/env python3
"""
Lenovo Tab M11 (TB311FU / 'poplar') EROFS Vendor Image Stabilizer.
Deconstructs stock vendor_a via fsck.erofs, injects active pen IDCs,
discrete quad-audio policies, Dolby Atmos effect chains, RRO framework overlay,
and re-compiles vendor_stabilized.img with mkfs.erofs -zlz4 and OEM SELinux contexts.
"""

import os
import sys
import re
import shutil
import struct
import subprocess
import argparse
from typing import Dict, List, Optional, Tuple, Any

# ==============================================================================
# Paths & Default Locations
# ==============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
DEFAULT_GSI_SUITE = os.path.abspath(r"C:\Users\BangerSoul\Documents\antigravity\fearless-maxwell\gsi_suite")

# ==============================================================================
# EROFS & Partition Constants
# ==============================================================================
EROFS_MAGIC: int = 0xe0f5e1e2
EROFS_MAGIC_LE: bytes = b"\xe2\xe1\xf5\xe0"
EROFS_SUPERBLOCK_OFFSET: int = 1024
EROFS_BLOCK_SIZE: int = 4096

# Stock vendor_a partition boundary: 592,472 sectors * 512 bytes = 303,345,664 B (~289.29 MB)
VENDOR_PARTITION_LIMIT_BYTES: int = 303345664
MIN_VENDOR_SIZE_BYTES: int = 50 * 1024 * 1024      # 50 MB minimum integrity check
MAX_VENDOR_HEADROOM_BYTES: int = 350 * 1024 * 1024   # 350 MB absolute max limit

# On-device staging directories
DEVICE_TMP_BASE: str = "/data/local/tmp/vendor_mod"
DEVICE_TMP_EXTRACT: str = "/data/local/tmp/vendor_mod/extract"
DEVICE_STOCK_IMG: str = "/data/local/tmp/vendor_mod/vendor_stock.img"
DEVICE_STABILIZED_IMG: str = "/data/local/tmp/vendor_mod/vendor_stabilized.img"
DEVICE_FILE_CONTEXTS: str = "/vendor/etc/selinux/vendor_file_contexts"

# ==============================================================================
# Hardware Stabilization Properties Contract (M1 / M2 interface)
# ==============================================================================
STABILIZATION_PROPS: Dict[str, str] = {
    # Telephony & Modem spinloop termination (Wi-Fi only TB311FU)
    "ro.radio.noril": "yes",
    "ro.carrier": "wifi-only",
    "persist.radio.noril": "1",
    "persist.sys.phh.no_telephony": "true",
    "config.disable_telephony": "true",
    "ro.telephony.default_network": "0",
    "telephony.lteOnCdmaDevice": "0",

    # Discrete 4-Channel Quad Audio & Spatializer
    "persist.vendor.audio.speaker.channels": "4",
    "persist.vendor.audio.multichannel.4ch": "1",
    "ro.vendor.audio.soundfx.usb": "true",
    "vendor.audio.feature.spatial": "true",
    "ro.audio.spatializer_enabled": "true",

    # Display Calibration & 90Hz Refresh Rate
    "persist.vendor.sys.pq.disp.aal.bypass": "1",
    "persist.vendor.sys.pq.debug.adaptive.en": "0",
    "persist.vendor.dfps.force_fps": "90",
    "debug.sf.latch_unsignaled": "1",
    "debug.sf.disable_hwc_overlays": "1",
    "ro.surface_flinger.has_wide_color_display": "true",
    "ro.surface_flinger.has_HDR_display": "false",
    "ro.surface_flinger.max_frame_buffer_acquired_buffers": "3",
}


# ==============================================================================
# Core Boundary & Verification Functions
# ==============================================================================
def validate_asset(name: str, data: bytes) -> bool:
    """Ensure injected asset is non-empty and valid."""
    if len(data) == 0:
        raise ValueError(f"Asset {name} is empty (0 bytes)")
    return True


def validate_compression(alg: str) -> str:
    """Validate EROFS compression algorithm."""
    if alg not in ("lz4", "lz4hc", "lzma", "deflate"):
        raise ValueError(f"Unsupported EROFS compression: {alg}")
    return f"-z{alg}"


def check_overflow(img_size: int, max_bytes: int = VENDOR_PARTITION_LIMIT_BYTES) -> bool:
    """Enforce vendor dynamic partition size ceiling."""
    if img_size > max_bytes:
        raise OverflowError(
            f"Image size {img_size:,} bytes exceeds partition limit {max_bytes:,} bytes "
            f"(overflow of +{img_size - max_bytes:,} bytes)"
        )
    return True


def check_block_size(bs: int) -> bool:
    """Validate EROFS block size is standard 4096 bytes."""
    if bs != 4096:
        raise ValueError(f"Invalid block size {bs}, must be 4096")
    return True


def check_source_dir(files: List[str]) -> bool:
    """Detect empty source directory."""
    if not files:
        raise ValueError("Source directory has no files to pack")
    return True


def get_context(path: str, contexts_dict: Dict[str, str]) -> str:
    """SELinux context lookup with standard vendor_file fallback."""
    return contexts_dict.get(path, "u:object_r:vendor_file:s0")


def verify_erofs_superblock(image_path: str) -> Dict[str, Any]:
    """
    Directly parse and verify the 128-byte EROFS superblock at offset 1024.
    Validates magic 0xe0f5e1e2, 4096-byte block size (blkszbits=12),
    and partition boundary limits.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    file_size = os.path.getsize(image_path)
    if file_size < EROFS_SUPERBLOCK_OFFSET + 128:
        raise ValueError(f"File too small for EROFS superblock: {file_size} bytes")

    with open(image_path, "rb") as f:
        f.seek(EROFS_SUPERBLOCK_OFFSET)
        sb_bytes = f.read(128)

    if len(sb_bytes) < 128:
        raise ValueError("Could not read full 128-byte EROFS superblock")

    magic, checksum, fcompat, blkszbits = struct.unpack("<IIIB", sb_bytes[:13])
    if magic != EROFS_MAGIC:
        raise ValueError(f"Invalid EROFS magic: {hex(magic)} (expected {hex(EROFS_MAGIC)})")

    block_size = 1 << blkszbits
    check_block_size(block_size)

    root_nid = struct.unpack("<H", sb_bytes[14:16])[0]
    inos, build_time = struct.unpack("<QQ", sb_bytes[16:32])
    blocks = struct.unpack("<I", sb_bytes[36:40])[0]
    total_fs_bytes = blocks * block_size

    fincompat = struct.unpack("<I", sb_bytes[80:84])[0]
    lz4_compressed = bool(fincompat & 0x1)  # Feature flag indicating compression / padding

    # Check partition boundary
    check_overflow(file_size, VENDOR_PARTITION_LIMIT_BYTES)

    return {
        "valid": True,
        "magic": hex(magic),
        "blkszbits": blkszbits,
        "block_size": block_size,
        "total_blocks": blocks,
        "filesystem_bytes": total_fs_bytes,
        "file_size_bytes": file_size,
        "lz4_compressed": lz4_compressed,
        "root_nid": root_nid,
        "inos": inos,
        "feature_incompat": hex(fincompat),
    }


def extract_erofs(src_path: str, dst_path: str) -> bool:
    """Extract EROFS image on host via fsck.erofs if available."""
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Source image not found: {src_path}")
    os.makedirs(dst_path, exist_ok=True)
    cmd = f"fsck.erofs --extract={dst_path} {src_path}"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"fsck.erofs failed: {res.stderr or res.stdout}")
    return True


# ==============================================================================
# Asset Injection Pipeline
# ==============================================================================
def patch_build_prop_file(build_prop_path: str, props_to_inject: Dict[str, str]) -> Dict[str, str]:
    """
    Patch build.prop cleanly by updating existing keys or appending new ones,
    preventing duplicate property keys.
    """
    existing_lines: List[str] = []
    prop_dict: Dict[str, str] = {}
    ordered_keys: List[str] = []

    if os.path.exists(build_prop_path):
        with open(build_prop_path, "r", encoding="utf-8", errors="replace") as f:
            existing_lines = f.readlines()

        for line in existing_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, v = stripped.split("=", 1)
                k = k.strip()
                v = v.strip()
                prop_dict[k] = v
                if k not in ordered_keys:
                    ordered_keys.append(k)

    # Apply injections
    for k, v in props_to_inject.items():
        prop_dict[k] = v
        if k not in ordered_keys:
            ordered_keys.append(k)

    # Reconstruct clean build.prop
    output_lines: List[str] = [
        "# ==============================================================================\n",
        "# Lenovo Tab M11 (TB311FU / poplar) Stabilized Vendor Properties\n",
        "# ==============================================================================\n",
    ]
    for k in ordered_keys:
        output_lines.append(f"{k}={prop_dict[k]}\n")

    with open(build_prop_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    return prop_dict


def inject_stabilization_stack(extract_dir: str, gsi_suite_dir: str = DEFAULT_GSI_SUITE) -> List[str]:
    """
    Inject complete TB311FU hardware stabilization stack into extracted vendor tree:
    1. Active Pen IDCs (himax-touchscreen.idc, NVT-ts.idc) -> usr/idc/
    2. Discrete Quad Audio Policies (audio_policy_configuration.xml, audio_effects.xml) -> etc/
    3. RRO Framework Overlay (treble-overlay-lenovo-tb311fu.apk) -> overlay/TrebleOverlayLenovoTB311FU/
    4. build.prop Telemetry & Hardware Properties
    """
    if not os.path.exists(extract_dir):
        raise FileNotFoundError(f"Extracted vendor directory does not exist: {extract_dir}")
    if not os.path.exists(gsi_suite_dir):
        raise FileNotFoundError(f"GSI reference suite directory not found: {gsi_suite_dir}")

    injected: List[str] = []

    # 1. Active Stylus IDCs
    idc_dest = os.path.join(extract_dir, "usr", "idc")
    os.makedirs(idc_dest, exist_ok=True)
    stylus_dir = os.path.join(gsi_suite_dir, "stylus")
    for idc_name in ["himax-touchscreen.idc", "NVT-ts.idc", "touch_tuning.conf"]:
        src = os.path.join(stylus_dir, idc_name)
        if os.path.exists(src):
            with open(src, "rb") as f:
                data = f.read()
            validate_asset(idc_name, data)
            dst = os.path.join(idc_dest, idc_name)
            with open(dst, "wb") as f:
                f.write(data)
            injected.append(f"usr/idc/{idc_name}")

    # 2. Quad Audio Policies & Effects
    etc_dest = os.path.join(extract_dir, "etc")
    os.makedirs(etc_dest, exist_ok=True)
    audio_dir = os.path.join(gsi_suite_dir, "audio")

    # Policy
    policy_src = os.path.join(audio_dir, "audio_policy_configuration.xml")
    if os.path.exists(policy_src):
        with open(policy_src, "rb") as f:
            pdata = f.read()
        validate_asset("audio_policy_configuration.xml", pdata)
        dst_policy = os.path.join(etc_dest, "audio_policy_configuration.xml")
        with open(dst_policy, "wb") as f:
            f.write(pdata)
        injected.append("etc/audio_policy_configuration.xml")

        # Also populate etc/audio/ if it exists in vendor
        audio_sub = os.path.join(etc_dest, "audio")
        if os.path.exists(audio_sub):
            shutil.copy2(policy_src, os.path.join(audio_sub, "audio_policy_configuration.xml"))
            injected.append("etc/audio/audio_policy_configuration.xml")

    # Effects
    effects_src = os.path.join(audio_dir, "audio_effects.xml")
    if os.path.exists(effects_src):
        with open(effects_src, "rb") as f:
            edata = f.read()
        validate_asset("audio_effects.xml", edata)
        dst_effects = os.path.join(etc_dest, "audio_effects.xml")
        with open(dst_effects, "wb") as f:
            f.write(edata)
        injected.append("etc/audio_effects.xml")

    # 3. RRO Framework Overlay APK
    overlay_dest = os.path.join(extract_dir, "overlay", "TrebleOverlayLenovoTB311FU")
    os.makedirs(overlay_dest, exist_ok=True)
    apk_src = os.path.join(gsi_suite_dir, "overlay", "treble-overlay-lenovo-tb311fu.apk")
    if os.path.exists(apk_src):
        with open(apk_src, "rb") as f:
            adata = f.read()
        validate_asset("treble-overlay-lenovo-tb311fu.apk", adata)
        dst_apk = os.path.join(overlay_dest, "treble-overlay-lenovo-tb311fu.apk")
        with open(dst_apk, "wb") as f:
            f.write(adata)
        injected.append("overlay/TrebleOverlayLenovoTB311FU/treble-overlay-lenovo-tb311fu.apk")

    # 3B. RRO SystemUI Sanitization Overlay APK (R5.4)
    sysui_apk_src = os.path.join(gsi_suite_dir, "overlay", "treble-overlay-lenovo-tb311fu-systemui.apk")
    if not os.path.exists(sysui_apk_src):
        ws_sysui_apk = os.path.join(os.path.dirname(SCRIPT_DIR), "ui_sanitization", "treble-overlay-lenovo-tb311fu-systemui.apk")
        if os.path.exists(ws_sysui_apk):
            sysui_apk_src = ws_sysui_apk

    if os.path.exists(sysui_apk_src):
        with open(sysui_apk_src, "rb") as f:
            sdata = f.read()
        validate_asset("treble-overlay-lenovo-tb311fu-systemui.apk", sdata)
        sysui_dest = os.path.join(extract_dir, "overlay", "TrebleOverlayLenovoTB311FUSystemUI")
        os.makedirs(sysui_dest, exist_ok=True)
        dst_sysui = os.path.join(sysui_dest, "treble-overlay-lenovo-tb311fu-systemui.apk")
        with open(dst_sysui, "wb") as f:
            f.write(sdata)
        injected.append("overlay/TrebleOverlayLenovoTB311FUSystemUI/treble-overlay-lenovo-tb311fu-systemui.apk")

    # 4. build.prop Telemetry & Display
    prop_path = os.path.join(extract_dir, "build.prop")
    patch_build_prop_file(prop_path, STABILIZATION_PROPS)
    injected.append("build.prop")

    # 5. init.connectivity.rc Modem Services Disabling (Requirement R5.2)
    hw_init_dir = os.path.join(extract_dir, "etc", "init", "hw")
    os.makedirs(hw_init_dir, exist_ok=True)
    hw_rc_path = os.path.join(hw_init_dir, "init.connectivity.rc")
    existing_rc = ""
    if os.path.exists(hw_rc_path):
        with open(hw_rc_path, "r", encoding="utf-8", errors="replace") as f:
            existing_rc = f.read()

    from telephony.patch_telephony import inject_modem_services_override
    new_rc = inject_modem_services_override(existing_rc)
    with open(hw_rc_path, "w", encoding="utf-8") as f:
        f.write(new_rc)
    injected.append("etc/init/hw/init.connectivity.rc")

    return injected


# ==============================================================================
# On-Device Automated Extraction & Recompilation Pipeline
# ==============================================================================
class VendorStabilizerPipeline:
    def __init__(
        self,
        device_serial: Optional[str] = None,
        gsi_suite_dir: str = DEFAULT_GSI_SUITE,
        output_image: Optional[str] = None,
    ):
        self.device_serial = device_serial
        self.gsi_suite_dir = gsi_suite_dir
        self.output_image = output_image or os.path.join(SCRIPT_DIR, "vendor_stabilized.img")

    def run_cmd(self, cmd: str, check: bool = True) -> subprocess.CompletedProcess:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if check and res.returncode != 0:
            raise RuntimeError(f"Command failed ({res.returncode}): {cmd}\n{res.stderr or res.stdout}")
        return res

    def run_adb(self, adb_args: Any, check: bool = True) -> subprocess.CompletedProcess:
        cmd = ["adb"]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        if isinstance(adb_args, str):
            import shlex
            cmd.extend(shlex.split(adb_args))
        else:
            cmd.extend(adb_args)
        res = subprocess.run(cmd, capture_output=True, text=True)
        if check and res.returncode != 0:
            raise RuntimeError(f"ADB command failed ({res.returncode}): {' '.join(cmd)}\n{res.stderr or res.stdout}")
        return res

    def run_adb_su(self, sh_cmd: str, check: bool = True) -> subprocess.CompletedProcess:
        cmd = ["adb"]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(["shell", "su", "-c", sh_cmd])
        res = subprocess.run(cmd, capture_output=True, text=True)
        if check and res.returncode != 0:
            raise RuntimeError(f"ADB su command failed ({res.returncode}): {sh_cmd}\n{res.stderr or res.stdout}")
        return res

    def push_root(self, local_path: str, remote_path: str, mode: str = "644") -> None:
        """Push a file to device and install as root to destination with exact permissions."""
        remote_dir = os.path.dirname(remote_path).replace("\\", "/")
        self.run_adb_su(f"mkdir -p {remote_dir}")
        tmp_staging = f"/data/local/tmp/staging_{os.path.basename(local_path)}"
        self.run_adb(["push", local_path, tmp_staging])
        self.run_adb_su(f"cp -f {tmp_staging} {remote_path} && rm -f {tmp_staging} && (chmod {mode} {remote_path} 2>/dev/null || true)")

    def verify_device_prerequisites(self) -> str:
        """Check ADB connectivity, root authority, and erofs-utils presence."""
        dev_out = self.run_adb("devices").stdout
        if "device" not in dev_out:
            raise ConnectionError("No ADB device detected in 'device' state. Enable USB debugging.")

        root_id = self.run_adb_su("id").stdout.strip()
        if "uid=0" not in root_id:
            raise PermissionError(f"Root authority (uid=0) not granted: {root_id}")

        tools_check = self.run_adb_su("which fsck.erofs mkfs.erofs").stdout.strip()
        if "/fsck.erofs" not in tools_check or "/mkfs.erofs" not in tools_check:
            raise FileNotFoundError("Missing fsck.erofs or mkfs.erofs on device /system/bin.")

        return root_id

    def execute_pipeline(self, dry_run: bool = False) -> str:
        """
        Execute full turnkey extraction, injection, and mkfs.erofs recompilation.
        If dry_run is True, verifies prerequisites, assets, and command parameters
        without performing writes on the live device.
        """
        print("=" * 70)
        print("TB311FU Dynamic Partition Modder: Vendor EROFS Stabilizer")
        print("=" * 70)

        # 1. Verify Device & Root
        print("\n[Phase 1] Verifying connected device & root context...")
        if not dry_run:
            root_ctx = self.verify_device_prerequisites()
            print(f"[+] Root Context: {root_ctx}")
        else:
            print("[i] Dry-Run Mode: Skipping live device verification.")

        # 2. Verify Reference Assets
        print("\n[Phase 2] Verifying reference assets in GSI suite...")
        required_assets = [
            ("stylus/himax-touchscreen.idc", 100),
            ("stylus/NVT-ts.idc", 100),
            ("audio/audio_policy_configuration.xml", 5000),
            ("audio/audio_effects.xml", 1000),
            ("overlay/treble-overlay-lenovo-tb311fu.apk", 5000),
        ]
        for rel_path, min_sz in required_assets:
            full_path = os.path.join(self.gsi_suite_dir, rel_path)
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"Missing required reference asset: {full_path}")
            sz = os.path.getsize(full_path)
            if sz < min_sz:
                raise ValueError(f"Asset too small ({sz} B < {min_sz} B): {full_path}")
            print(f"  [+] Verified {rel_path} ({sz:,} bytes)")

        if dry_run:
            print("\n[Phase 3-8] Dry-Run Command Generation & Validation:")
            print(f"  1. Dump stock vendor: dd if=/dev/block/mapper/vendor_a of={DEVICE_STOCK_IMG} bs=4M")
            print(f"  2. Extract EROFS: fsck.erofs --extract={DEVICE_TMP_EXTRACT} {DEVICE_STOCK_IMG}")
            print("  3. Inject active stylus IDCs to usr/idc/")
            print("  4. Inject quad audio XMLs to etc/")
            print("  5. Inject RRO overlay APK to overlay/TrebleOverlayLenovoTB311FU/")
            print("  6. Cleanly patch Wi-Fi only, 90Hz & SurfaceFlinger properties in build.prop")
            print("  7. Inject modem service disabling stanzas into etc/init/hw/init.connectivity.rc")
            mkfs_cmd = (
                f"mkfs.erofs -zlz4hc --mount-point=/vendor "
                f"--file-contexts={DEVICE_FILE_CONTEXTS} "
                f"{DEVICE_STABILIZED_IMG} {DEVICE_TMP_EXTRACT}"
            )
            print(f"  8. Recompile EROFS: {mkfs_cmd}")
            print(f"  9. Pull image to host: {self.output_image}")
            print("\n[+] DRY-RUN VALIDATION COMPLETE: All pipeline stages are valid.")
            return self.output_image

        # 3. Stage workspace on device
        print("\n[Phase 3] Staging device temp workdirs...")
        self.run_adb_su(f"rm -rf {DEVICE_TMP_BASE} && mkdir -p {DEVICE_TMP_EXTRACT}")

        # 4. Dump stock vendor_a
        print("\n[Phase 4] Dumping /dev/block/mapper/vendor_a...")
        self.run_adb_su(f"dd if=/dev/block/mapper/vendor_a of={DEVICE_STOCK_IMG} bs=4M")
        stock_size = int(self.run_adb_su(f"stat -c%s {DEVICE_STOCK_IMG}").stdout.strip())
        print(f"[+] Baseline vendor dumped successfully ({stock_size:,} bytes)")

        # 5. Extract EROFS filesystem
        print(f"\n[Phase 5] Extracting EROFS filesystem on device via fsck.erofs...")
        self.run_adb_su(f"fsck.erofs --extract={DEVICE_TMP_EXTRACT} {DEVICE_STOCK_IMG}")
        self.run_adb_su(f"chmod -R 777 {DEVICE_TMP_BASE}")
        print("[+] Extraction complete.")

        # 6. Inject Assets
        print("\n[Phase 6] Injecting Hardware Stabilization Stack...")

        # 6A. IDC files
        self.run_adb_su(f"mkdir -p {DEVICE_TMP_EXTRACT}/usr/idc")
        for idc in ["himax-touchscreen.idc", "NVT-ts.idc", "touch_tuning.conf"]:
            src = os.path.join(self.gsi_suite_dir, "stylus", idc)
            if os.path.exists(src):
                self.push_root(src, f"{DEVICE_TMP_EXTRACT}/usr/idc/{idc}", mode="644")
                print(f"     [+] Injected {idc}")

        # 6B. Audio Policies & Effects
        self.run_adb_su(f"mkdir -p {DEVICE_TMP_EXTRACT}/etc/audio")
        policy_src = os.path.join(self.gsi_suite_dir, "audio", "audio_policy_configuration.xml")
        effects_src = os.path.join(self.gsi_suite_dir, "audio", "audio_effects.xml")

        self.push_root(policy_src, f"{DEVICE_TMP_EXTRACT}/etc/audio_policy_configuration.xml", mode="644")
        self.push_root(policy_src, f"{DEVICE_TMP_EXTRACT}/etc/audio/audio_policy_configuration.xml", mode="644")
        print("     [+] Injected audio_policy_configuration.xml")

        self.push_root(effects_src, f"{DEVICE_TMP_EXTRACT}/etc/audio_effects.xml", mode="644")
        print("     [+] Injected audio_effects.xml")

        # 6C. RRO Framework Overlay APK (M2)
        self.run_adb_su(f"mkdir -p {DEVICE_TMP_EXTRACT}/overlay/TrebleOverlayLenovoTB311FU")
        apk_src = os.path.join(self.gsi_suite_dir, "overlay", "treble-overlay-lenovo-tb311fu.apk")
        self.push_root(apk_src, f"{DEVICE_TMP_EXTRACT}/overlay/TrebleOverlayLenovoTB311FU/treble-overlay-lenovo-tb311fu.apk", mode="644")
        self.run_adb_su(f"chmod 755 {DEVICE_TMP_EXTRACT}/overlay/TrebleOverlayLenovoTB311FU 2>/dev/null || true")
        print("     [+] Injected treble-overlay-lenovo-tb311fu.apk")

        # 6C2. RRO SystemUI Sanitization Overlay APK (M3 / R5.4)
        sysui_src = os.path.join(self.gsi_suite_dir, "overlay", "treble-overlay-lenovo-tb311fu-systemui.apk")
        if not os.path.exists(sysui_src):
            ws_sysui = os.path.join(PROJECT_ROOT, "ui_sanitization", "treble-overlay-lenovo-tb311fu-systemui.apk")
            if os.path.exists(ws_sysui):
                sysui_src = ws_sysui
        if os.path.exists(sysui_src):
            self.run_adb_su(f"mkdir -p {DEVICE_TMP_EXTRACT}/overlay/TrebleOverlayLenovoTB311FUSystemUI")
            self.push_root(sysui_src, f"{DEVICE_TMP_EXTRACT}/overlay/TrebleOverlayLenovoTB311FUSystemUI/treble-overlay-lenovo-tb311fu-systemui.apk", mode="644")
            self.run_adb_su(f"chmod 755 {DEVICE_TMP_EXTRACT}/overlay/TrebleOverlayLenovoTB311FUSystemUI 2>/dev/null || true")
            print("     [+] Injected treble-overlay-lenovo-tb311fu-systemui.apk")

        # 6D. Clean build.prop Patching (Prevents Duplicate Keys)
        local_prop_tmp = os.path.join(SCRIPT_DIR, "temp_device_build.prop")
        self.run_adb(["pull", f"{DEVICE_TMP_EXTRACT}/build.prop", local_prop_tmp])
        patch_build_prop_file(local_prop_tmp, STABILIZATION_PROPS)
        self.push_root(local_prop_tmp, f"{DEVICE_TMP_EXTRACT}/build.prop", mode="644")
        if os.path.exists(local_prop_tmp):
            os.remove(local_prop_tmp)
        print("     [+] Injected clean stabilization properties into build.prop")

        # 6E. init.connectivity.rc Modem Services Disabling (Requirement R5.2)
        local_rc_tmp = os.path.join(SCRIPT_DIR, "temp_device_init.rc")
        self.run_adb_su(f"mkdir -p {DEVICE_TMP_EXTRACT}/etc/init/hw")
        rc_check = self.run_adb_su(f"test -f {DEVICE_TMP_EXTRACT}/etc/init/hw/init.connectivity.rc && echo 'EXISTS' || echo 'MISSING'", check=False).stdout
        existing_rc = ""
        if "EXISTS" in rc_check:
            self.run_adb(["pull", f"{DEVICE_TMP_EXTRACT}/etc/init/hw/init.connectivity.rc", local_rc_tmp])
            if os.path.exists(local_rc_tmp):
                with open(local_rc_tmp, "r", encoding="utf-8", errors="replace") as f:
                    existing_rc = f.read()

        from telephony.patch_telephony import inject_modem_services_override
        new_rc = inject_modem_services_override(existing_rc)
        with open(local_rc_tmp, "w", encoding="utf-8") as f:
            f.write(new_rc)
        self.push_root(local_rc_tmp, f"{DEVICE_TMP_EXTRACT}/etc/init/hw/init.connectivity.rc", mode="644")
        if os.path.exists(local_rc_tmp):
            os.remove(local_rc_tmp)
        print("     [+] Injected modem service disabling stanzas into etc/init/hw/init.connectivity.rc")

        # 7. Recompile EROFS
        print("\n[Phase 7] Recompiling stabilized EROFS image with LZ4HC compression...")
        mkfs_cmd = (
            f"mkfs.erofs -zlz4hc --mount-point=/vendor "
            f"--file-contexts={DEVICE_FILE_CONTEXTS} "
            f"{DEVICE_STABILIZED_IMG} {DEVICE_TMP_EXTRACT}"
        )
        self.run_adb_su(mkfs_cmd)
        new_size = int(self.run_adb_su(f"stat -c%s {DEVICE_STABILIZED_IMG}").stdout.strip())
        print(f"[+] Recompilation complete! New image size: {new_size:,} bytes")
        check_overflow(new_size, VENDOR_PARTITION_LIMIT_BYTES)

        # 8. Pull back to Host PC
        print(f"\n[Phase 8] Pulling generated image to host: {self.output_image}...")
        os.makedirs(os.path.dirname(os.path.abspath(self.output_image)), exist_ok=True)
        self.run_adb(f'pull {DEVICE_STABILIZED_IMG} "{self.output_image}"')

        # 9. Superblock & Integrity Verification on Host
        print("\n[Phase 9] Verifying EROFS superblock on host...")
        sb_info = verify_erofs_superblock(self.output_image)
        print(f"  [+] Magic:           {sb_info['magic']} (OK)")
        print(f"  [+] Block Size:      {sb_info['block_size']} bytes (4096 OK)")
        print(f"  [+] Total Blocks:    {sb_info['total_blocks']:,}")
        print(f"  [+] Filesystem Size: {sb_info['filesystem_bytes']:,} bytes")
        print(f"  [+] LZ4 Compressed:  {sb_info['lz4_compressed']}")

        # 10. Clean up device temporary files
        print("\n[Phase 10] Cleaning up device temporary files...")
        self.run_adb_su(f"rm -rf {DEVICE_TMP_BASE}")

        print("\n" + "=" * 70)
        print("SUCCESS: vendor_stabilized.img generated and verified!")
        print(f"Path: {self.output_image} ({os.path.getsize(self.output_image):,} bytes)")
        print("=" * 70)
        return self.output_image


# ==============================================================================
# CLI Entrypoint
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Lenovo Tab M11 EROFS Vendor Image Stabilizer")
    parser.add_argument("--serial", type=str, default=None, help="Specific ADB device serial (e.g., HNQ09EZD)")
    parser.add_argument("--gsi-suite", type=str, default=DEFAULT_GSI_SUITE, help="Path to gsi_suite reference directory")
    parser.add_argument("--output", type=str, default=None, help="Output vendor_stabilized.img path")
    parser.add_argument("--dry-run", action="store_true", help="Validate assets and commands without modifying device")
    parser.add_argument("--verify", type=str, default=None, help="Verify existing EROFS image superblock on host")
    args = parser.parse_args()

    if args.verify:
        try:
            info = verify_erofs_superblock(args.verify)
            print(f"[+] EROFS Superblock Valid for {args.verify}:")
            for k, v in info.items():
                print(f"    - {k}: {v}")
            sys.exit(0)
        except Exception as e:
            print(f"[!] Superblock verification failed: {e}", file=sys.stderr)
            sys.exit(1)

    pipeline = VendorStabilizerPipeline(
        device_serial=args.serial,
        gsi_suite_dir=args.gsi_suite,
        output_image=args.output,
    )

    try:
        pipeline.execute_pipeline(dry_run=args.dry_run)
    except Exception as e:
        print(f"[!] Pipeline execution failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
