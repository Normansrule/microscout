> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1

# Remote control - preliminary outline (full remote G1 package deferred to start of M5, D-024)

**Default remote:** any ExpressLRS 2.4 GHz transmitter bound to the drone's ELRS receiver (CRSF). Setup guide will be written in `docs/` at M5.

**DIY remote (second PCB), planned architecture:**

| Function | Candidate | Status |
|---|---|---|
| MCU + radio (ESP-NOW link to drone) | ESP32-S3-WROOM-1 (same family as the drone; variant chosen at remote G1) | Candidate |
| Sticks | 2x analog dual-axis gimbals on ADC1 pins | Part not chosen |
| Buttons | 4x tactile | Part not chosen |
| Display | Small I2C OLED (e.g. 0.96 in, 128x64) | Part not chosen - UNCONFIRMED |
| Battery and charging | 1S LiPo + USB-C, reuse BQ24074 + TPS63802 from the drone | Candidate |
| Shell | CadQuery, printable | M6 |

Open points for the remote G1: link budget and latency of ESP-NOW vs ELRS, whether the drone can serve CRSF and ESP-NOW simultaneously (ESP-NOW shares the Wi-Fi radio with the MJPEG stream - **UNCONFIRMED**), and gimbal part selection with datasheets.
