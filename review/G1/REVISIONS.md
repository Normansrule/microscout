> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)

# G1 revisions

| Rev | Date | Summary | Where |
|---|---|---|---|
| A | 2026-10-04 | Brushed 8520 motors, 1S 660 mAh JST-PH, PCB-as-frame, BMI270, BQ24074, fuse + P-FET protection. T/W 1.6-2.0. | git tag `g1-rev-a` |
| B | 2026-10-07 | Owner direction: high speed, flips, crash durability, easy to program and fly. 2S brushless EX1103 + AM32 4-in-1 ESC board, ducted one-piece PA11 frame with soft-mounted boards, TPU canopy, ICM-42688-P, BQ25887 2S charger, buck regulators, firmware current limit instead of a fuse. T/W 4.1-5.9. Added concept CAD + renders (D-039) and the Python SDK + simulator (D-038). | this package |

## Rev A → rev B, item by item

| Item | Rev A | Rev B | Decision |
|---|---|---|---|
| Motors | 4x 8520 brushed | 4x EX1103 11000KV brushless | D-028 |
| Props | 55 mm open, printed guards | 2-inch 3-blade in ducts | D-028, D-030 |
| Motor drive | AO3400A + Schottky on the main PCB | Separate AM32 4-in-1 ESC board | D-029 |
| Battery | 1S 660 mAh, JST-PH 2.0 | 2S 550 mAh LiHV, XT30 + balance lead | D-028, OQ-2 |
| Charger | BQ24074 (1S power path) | BQ25887 (2S boost + balancing) | D-033 |
| 3.3 V / 5 V | TPS63802 buck-boost / TPS61023 boost | TPS62162 buck / TPS62133 buck | D-034 |
| Protection | 15 A fuse, P-FET reverse, P-FET motor switch | Firmware 30 A limit, keyed connectors instead of a reverse FET (OQ-10), soft switch on logic rails + ESC driver supply | D-035, D-036 |
| IMU | BMI270 | ICM-42688-P | D-032 |
| Frame | PCB is the frame | One-piece ducted PA11 frame, soft-mounted boards | D-030, D-031 |
| Firmware base | esp-drone | Reopened: esp-drone / esp-fc / own | D-037, OQ-8 |
| Pins | MOTx_PWM gate drive | MOTx_DSHOT to the ESC board | pin-allocation.md |
| Unchanged | ESP32-S3-WROOM-1-N8R2, camera, ToF/flow/baro/mag sensors, expanders, LEDs, buzzer, USB-C, ELRS | | |
