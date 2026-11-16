# vendor_lenovo_TB311FU

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Target: Lenovo Tab M11](https://img.shields.io/badge/Device-Lenovo%20Tab%20M11%20(TB311FU)-orange.svg)](https://www.lenovo.com)
[![Branch: main](https://img.shields.io/badge/Branch-main%20%2F%20lineage--23.2-success.svg)](https://github.com/BangerSoul/vendor_lenovo_TB311FU)

Proprietary vendor blobs, hardware configuration overlays, audio policies, active pen digitizer configs, and dynamic partition tools for the **Lenovo Tab M11** (`TB311FU`, codename `poplar`).

---

## Branches

- **`main`**: Master branch containing the latest Android 16 QPR2 / LineageOS 23.2 vendor assets and stabilization fixes.
- **`lineage-23.2`**: Dedicated branch targeting LineageOS 23.2 (Android 16 QPR2 GSI / ROM) bringup and dynamic partition integration.
- **`lineage-22.1`**: Stable baseline snapshot for LineageOS 22.1 (Android 15).

---

## Key Hardware Remediations & Inclusions

### 1. Discrete Quad-Speaker Audio & Dolby Atmos DAP Chain
- **File:** `proprietary/vendor/etc/audio_policy_configuration.xml`
  - Replaces default 2-channel stereo downmix with full 4-channel surround (`AUDIO_CHANNEL_OUT_QUAD`) across both Awinic AW883xx smart power amplifiers.
  - Enables Global Speaker DRC (`speaker_drc_enabled="true"`).
- **File:** `proprietary/vendor/etc/audio_effects.xml`
  - Binds Lenovo OEM Dolby Atmos Digital Audio Processing (`libswdap.so`, `libdolby.so`) and hardware DRC limiter (`libdrc.so`) to eliminate GSI volume double-scaling clipping.

### 2. Active Pen Digitizer (Lenovo AP500U) Input Device Configurations
- **Files:** `proprietary/vendor/usr/idc/himax-touchscreen.idc` and `proprietary/vendor/usr/idc/NVT-ts.idc`
  - Physical 12-bit pressure sensitivity (`touch.pressure.scale = 0.000244140625` for 4096 levels).
  - Hover distance telemetry up to ~12mm (`touch.distance.scale = 0.00390625`).
  - Spatial and temporal palm rejection filtering (`touch.filter.level = 2`).

### 3. PWM Backlight Minimum Brightness Clamp & Display Calibration
- Enforces `persist.sys.phh.backlight54=1` and `persist.vendor.sys.pq.disp.aal.bypass=1` to prevent 0-nit panel blackouts at low brightness slider positions.
- Enforces 90Hz refresh rate profiles (`persist.vendor.dfps.force_fps=90`) and unsignaled SurfaceFlinger latching (`debug.sf.latch_unsignaled=1`).

### 4. Telephony Wakelock Suppression & Power Optimization
- **Files:** `TB311FU-vendor.mk` and `proprietary/vendor/etc/init/hw/init.connectivity.rc`
  - Injects `ro.radio.noril=yes` and `ro.carrier=wifi-only` to stop baseband daemon loops (`ccci_fsd`, `ccci_mdinit`, `mtk-ril`).
  - Completely eliminates battery drain from modem activity polling on this Wi-Fi-only tablet.

### 5. EROFS Dynamic Partition Extraction & Stabilization Tools
- **Files:** `tools/build_vendor_stabilized.py` and `tools/repack_vendor_mod.py`
  - Full automation suite for extracting stock EROFS vendor images via `fsck.erofs`, injecting hardware assets and IDC configs, and recompiling with `mkfs.erofs -zlz4 --mount-point=/vendor`.

---

## Maintainer

- **Maintainer:** Azmathulla Shaik ([@BangerSoul](https://github.com/BangerSoul))
- **Email:** `iamshaikhazmathulla@outlook.com`
