# vendor_lenovo_TB311FU

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Target: Lenovo Tab M11](https://img.shields.io/badge/Device-Lenovo%20Tab%20M11%20(TB311FU)-orange.svg)](https://www.lenovo.com)
[![Branch: main](https://img.shields.io/badge/Branch-main%20%2F%20lineage--23.2-success.svg)](https://github.com/BangerSoul/vendor_lenovo_TB311FU)

Proprietary vendor blobs, hardware configuration overlays, audio policies, active pen digitizer configs, and dynamic partition tools for the **Lenovo Tab M11** (`TB311FU`, codename `poplar`).

---

## 🌐 Lenovo Tab M11 (TB311FU / poplar) Open-Source Bringup Ecosystem

The complete open-source software stack for the **Lenovo Tab M11** (`TB311FU`, codename `poplar`, MediaTek Helio G88 / MT8786 / MT6768) is organized into five specialized, interconnected repositories under [@BangerSoul](https://github.com/BangerSoul):

| Repository | Role & Subsystem Scope | Target Stack | Key Deliverables & Artifacts | Badges & Links |
| :--- | :--- | :--- | :--- | :---: |
| [**`device_lenovo_TB311FU`**](https://github.com/BangerSoul/device_lenovo_TB311FU) | **Device Tree & RRO Overlays**<br>LineageOS device configuration, 90Hz display profiles, SystemUI/Framework RRO overlays, super partition budget management, and 5-tier diagnostic test suite. | Android 16 QPR2<br>LineageOS 23.2 / 22.1 | `TrebleOverlayLenovoTB311FU.apk`<br>`TrebleOverlayLenovoTB311FUSystemUI.apk`<br>`flash_lineage23_fastbootd.ps1`<br>E2E Diagnostic Test Suite | [![Device Tree](https://img.shields.io/badge/Repo-device__lenovo__TB311FU-blue.svg?logo=android)](https://github.com/BangerSoul/device_lenovo_TB311FU)<br>[![Releases](https://img.shields.io/badge/Releases-v1.0--lineage23-blue.svg)](https://github.com/BangerSoul/device_lenovo_TB311FU/releases) |
| [**`vendor_lenovo_TB311FU`**](https://github.com/BangerSoul/vendor_lenovo_TB311FU) | **Vendor Blobs & Hardware Policies**<br>Proprietary blobs, 4-speaker surround audio routing (`AUDIO_CHANNEL_OUT_QUAD`), Dolby Atmos DAP/DRC trees, AP500U active stylus IDC configs, and EROFS vendor repacking tools. | Android 16 QPR2<br>LineageOS 23.2 HALs | `vendor_stabilized.img` (EROFS LZ4)<br>`audio_policy_configuration.xml`<br>`audio_effects.xml`<br>`himax-touchscreen.idc` / `NVT-ts.idc` | [![Vendor Blobs](https://img.shields.io/badge/Repo-vendor__lenovo__TB311FU-orange.svg?logo=android)](https://github.com/BangerSoul/vendor_lenovo_TB311FU)<br>[![Releases](https://img.shields.io/badge/Releases-Assets-orange.svg)](https://github.com/BangerSoul/vendor_lenovo_TB311FU/releases) |
| [**`kernel_lenovo_TB311FU`**](https://github.com/BangerSoul/kernel_lenovo_TB311FU) | **PoplarKernel GKI 2.0 & AVB Vector**<br>Downstream Linux 6.6 LTS kernel, KernelSU-Next native integration, module signature bypass (`CONFIG_RFKILL=m`), permissive dm-verity, PWM >= 48 floor clamp, and 32MB LK AVB boot vector builder. | Linux 6.6 LTS GKI 2.0<br>Android 15 / 16 & Halium | PoplarKernel v1.2 AnyKernel3 Zip<br>32MB AVB Chained `boot.img`<br>Halium `Image.gz` / `dtbo.img`<br>CI/CD Automated Build Actions | [![Kernel](https://img.shields.io/badge/Repo-kernel__lenovo__TB311FU-teal.svg?logo=linux)](https://github.com/BangerSoul/kernel_lenovo_TB311FU)<br>[![Releases](https://img.shields.io/badge/Releases-v1.2-teal.svg)](https://github.com/BangerSoul/kernel_lenovo_TB311FU/releases) |
| [**`recovery_lenovo_TB311FU`**](https://github.com/BangerSoul/recovery_lenovo_TB311FU) | **TWRP 3.7+ Recovery & Slot B Vector**<br>Non-destructive custom recovery deployment to secondary slot `boot_b`, pristine factory `vendor_boot` & `vbmeta` preservation, BCB staging, and zero-risk slot switching. | Android Header v4<br>TWRP 3.7+ / OrangeFox | Slot B Chained `recovery_boot.img`<br>Turnkey Hybrid `vendor_boot.img`<br>Bootloader Control Block Tools<br>CI/CD Automated Build Actions | [![Recovery](https://img.shields.io/badge/Repo-recovery__lenovo__TB311FU-blueviolet.svg?logo=twrp)](https://github.com/BangerSoul/recovery_lenovo_TB311FU)<br>[![Releases](https://img.shields.io/badge/Releases-v1.0--twrp-blueviolet.svg)](https://github.com/BangerSoul/recovery_lenovo_TB311FU/releases) |
| [**`linux-lenovo-tb311fu`**](https://github.com/BangerSoul/linux-lenovo-tb311fu) | **Native Linux / PostmarketOS Port**<br>Alpine ARM64 + KDE Plasma Mobile 6 port, KWin Wayland 24-bit True Color fallback & rotation fix (`libkwin.so.6.7.5`), WMT Wi-Fi/BT daemons, quad ALSA UCM scenarios, and Fastbootd direct `system_a` flasher. | PostmarketOS<br>Alpine ARM64 / Plasma Mobile 6 | `device-lenovo-tb311fu` package<br>`linux-lenovo-tb311fu` package<br>`libkwin.so.6.7.5.patched`<br>Fastbootd `-S 64M` Rootfs Flasher | [![Linux Port](https://img.shields.io/badge/Repo-linux--lenovo--tb311fu-success.svg?logo=postmarketos)](https://github.com/BangerSoul/linux-lenovo-tb311fu)<br>[![Releases](https://img.shields.io/badge/Releases-v1.0--alpha-success.svg)](https://github.com/BangerSoul/linux-lenovo-tb311fu/releases) |

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
