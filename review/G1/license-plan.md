> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)

# License plan

Draft guidance only - not legal advice. License compatibility of reused code and CAD must be confirmed by the human (brief section 1).

| Area | Directories | License | File | Notes |
|---|---|---|---|---|
| Hardware (schematics, PCB, libraries, fab outputs) | `hardware/`, `bom/` | CERN-OHL-S-2.0 | `hardware/LICENSE`, `bom/LICENSE` | Strongly reciprocal: modified designs must be shared under the same licence. |
| Mechanical (CadQuery source, STEP/STL/3MF) | `mechanical/` | CERN-OHL-S-2.0 | `mechanical/LICENSE` | Treated as hardware design source. |
| Firmware | `firmware/` | GPL-3.0 | `firmware/LICENSE` | Required: esp-drone is GPL-3.0 (ported from Crazyflie). Keep esp-drone's own notices and LICENSE inside its imported tree. |
| Software (SDK, simulator, notebooks, tools, calc scripts) | `software/`, `tools/`, `review/*/calc/` | MIT | `software/LICENSE`, `tools/LICENSE`; calc scripts carry SPDX MIT headers | The SDK talks to firmware over a network/BLE protocol, not by linking, so MIT is expected to be fine - **confirm** if any firmware code is copied into the SDK. |
| Documentation, renders, review packages | `docs/`, `review/`, README files | CC-BY-SA-4.0 | `docs/LICENSE`, `review/LICENSE` | |

## Third-party material to track (filled in as it is added)

| Item | License | Where | Compatibility note |
|---|---|---|---|
| esp-drone (Espressif) | GPL-3.0 | `firmware/drone/` (M7) | Same as firmware licence. |
| esp32-camera (Espressif) | Apache-2.0 (UNCONFIRMED - check the repo LICENSE at M7) | ESP-IDF component | Apache-2.0 is generally considered compatible with GPL-3.0 - confirm. |
| ESP-IDF | Apache-2.0 (UNCONFIRMED - check at M7) | build dependency | - |
| AM32 ESC firmware | GPL-3.0 (repo page) | flashed to the ESC board MCUs (D-029) | Separate firmware image; ships under its own licence. |
| OpenESC 30x30 (reference design only) | CERN-OHL-S-2.0 (AllSpice mirror page) | not copied | If any of its design is reused, the ESC board stays CERN-OHL-S-2.0 - compatible. |
| three.js | MIT (package LICENSE file, v0.169.0) | loaded from a CDN by `docs/index.html`; npm copy used only for local renders (not committed) | Permissive. |
| esp-fc (if chosen, OQ-8) | UNCONFIRMED | `firmware/` | Must be GPL-3.0-compatible to combine with esp-drone or GPL code. |
| ST VL53L1X / VL53L5CX ULD drivers | UNCONFIRMED (ST licence terms vary by package) | `firmware/` | **Must be checked before import** - some ST packages are BSD-3-Clause, others proprietary. |
| Bosch BMI270 / BMP3 Sensor APIs | UNCONFIRMED (believed BSD-3-Clause - check) | `firmware/` | Check before import. |
| KiCad standard libraries | CC-BY-SA-4.0 with a design exception (UNCONFIRMED - check kicad.org) | `hardware/` | Check the exception wording covers fabricated designs. |
| Manufacturer STEP models | Varies, often restrictive | `hardware/libraries/` | Only link confirmed manufacturer files; do not redistribute unless the licence allows. |

A full audit is scheduled for G8.
