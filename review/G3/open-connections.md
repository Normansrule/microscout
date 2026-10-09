> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3

# Connections still open (G3)

Taken from KiCad's DRC reports in `drc/`. Each line is one missing connection between two copper items of the same net (KiCad picks the nearest pair). They must be routed (for example with KiCad's interactive router) before G4. On the ESC, channels 3 and 4 are copies of channels 2 and 1, so most items appear twice.

## Flight controller: 29 open

| Net | From | To | Near (x, y) mm from board centre |
|---|---|---|---|
| `+5V` | Pad 1 of C68 on F.Cu | Pad 5 of U21 on B.Cu | (1.5, 12.0) |
| `+5V` | Pad 5 of U21 on B.Cu | Track on In2.Cu, length 2.3193 mm | (-3.6, 19.6) |
| `+5V` | Track on In3.Cu, length 0.1000 mm | Pad 1 of C68 on F.Cu | (3.8, 12.0) |
| `/Camera, LEDs, buzzer, receiver/LED_D0` | Track on In3.Cu, length 2.0243 mm | Pad 4 of U21 on B.Cu | (-0.5, 4.3) |
| `/MCU and USB/MOT2_DSHOT` | Track on In3.Cu, length 4.0800 mm | Pad 1 of R35 on F.Cu | (5.7, -2.5) |
| `/Power/CHG_ILIM` | Pad 8 of U2 on F.Cu | Pad 1 of R4 on F.Cu | (2.0, -10.8) |
| `/Power/PWR_EN` | Pad 6 of U8 on B.Cu | Track on B.Cu, length 1.6884 mm | (-7.4, 16.4) |
| `/Power/PWR_KILL_N` | Track on B.Cu, length 0.1202 mm | Pad 2 of D5 on B.Cu | (-8.1, 15.3) |
| `/Power/PWR_KILL_N` | Track on B.Cu, length 1.7395 mm | Pad 2 of D5 on B.Cu | (-5.5, 9.5) |
| `/Power/PWR_PDT` | Pad 7 of U8 on B.Cu | Pad 1 of C13 on B.Cu | (-7.4, 17.1) |
| `/Sensors and expanders/TOF_FWD_INT_N` | Pad 2 of U11 on B.Cu | Pad 6 of J14 on B.Cu | (6.8, -4.8) |
| `/Sensors and expanders/TOF_RIGHT_XSHUT` | Pad 4 of U10 on B.Cu | Pad 5 of J12 on B.Cu | (2.0, -8.8) |
| `CAM_D5` | Pad 17 of U1 on F.Cu | Pad 16 of J3 on F.Cu | (6.8, 4.4) |
| `CAM_PWDN` | Pad 8 of U10 on B.Cu | Pad 8 of J3 on F.Cu | (4.2, -9.5) |
| `CAM_RESET_N` | Pad 9 of U10 on B.Cu | Pad 6 of J3 on F.Cu | (5.0, -8.8) |
| `GND` | Zone on B.Cu | Track on B.Cu, length 0.0016 mm | (25.7, -7.7) |
| `GND` | Zone on B.Cu | Zone on B.Cu | (25.7, -7.7) |
| `GND` | Zone on B.Cu | Zone on B.Cu | (25.7, -7.7) |
| `GND` | Zone on B.Cu | Zone on B.Cu | (25.7, -7.7) |
| `I2C_SDA` | Track on In2.Cu, length 0.3690 mm | Track on In2.Cu, length 2.5803 mm | (2.8, 7.7) |
| `LED_DIN_3V3` | Track on In3.Cu, length 2.4400 mm | Pad 2 of U21 on B.Cu | (-1.7, 11.1) |
| `MCU_KILL_N` | Track on In3.Cu, length 0.4797 mm | Pad 1 of D5 on B.Cu | (-1.4, 6.7) |
| `PWR_BTN_INT_N` | Pad 2 of R15 on B.Cu | Pad 5 of U11 on B.Cu | (3.8, -0.4) |
| `PWR_BTN_INT_N` | Pad 5 of U8 on B.Cu | Pad 2 of R15 on B.Cu | (-7.4, 15.8) |
| `VBAT` | Track on B.Cu, length 0.5369 mm | Via on F.Cu - B.Cu | (6.3, 17.0) |
| `VDRV` | Pad 1 of TP14 on F.Cu | Track on In3.Cu, length 0.1034 mm | (-6.7, 15.8) |
| `VDRV` | Track on B.Cu, length 0.4543 mm | Pad 1 of R25 on B.Cu | (-0.7, 12.8) |
| `VDRV` | Track on B.Cu, length 0.5069 mm | Pad 1 of TP14 on F.Cu | (-4.0, 12.0) |
| `VLOGIC` | Track on In3.Cu, length 0.7303 mm | Pad 1 of R13 on B.Cu | (4.2, 12.0) |

## 4-in-1 ESC: 51 open

| Net | From | To | Near (x, y) mm from board centre |
|---|---|---|---|
| `+3V3_ESC` | Pad 1 of C401 on B.Cu | Pad 1 of C403 on B.Cu | (8.8, -6.8) |
| `+3V3_ESC` | Pad 1 of TP1 on B.Cu | Track on B.Cu, length 0.2438 mm | (18.4, -8.0) |
| `+3V3_ESC` | Pad 17 of U101 on B.Cu | Track on B.Cu, length 0.5119 mm | (-4.9, 8.2) |
| `+3V3_ESC` | Track on B.Cu, length 0.4819 mm | Pad 1 of C103 on B.Cu | (-8.8, 6.8) |
| `+3V3_ESC` | Track on B.Cu, length 0.5119 mm | Pad 17 of U401 on B.Cu | (6.5, -9.8) |
| `/Motor 1/M1_BH` | Pad 19 of U101 on B.Cu | Pad 23 of U102 on B.Cu | (-5.7, 8.2) |
| `/Motor 1/M1_CH` | Pad 18 of U101 on B.Cu | Pad 24 of U102 on B.Cu | (-5.3, 8.2) |
| `/Motor 1/M1_GL_C` | Pad 2 of R115 on B.Cu | Pad 1 of R135 on B.Cu | (4.5, 18.6) |
| `/Motor 1/M1_GL_C` | Pad 4 of Q106 on F.Cu | Pad 2 of R115 on B.Cu | (-0.4, 7.9) |
| `/Motor 1/M1_HO_C` | Pad 13 of U102 on B.Cu | Pad 1 of R114 on B.Cu | (-0.8, 13.9) |
| `/Motor 1/M1_LO_A` | Pad 1 of R111 on B.Cu | Pad 11 of U102 on B.Cu | (-11.6, 14.2) |
| `/Motor 1/M1_LO_B` | Pad 1 of R113 on B.Cu | Pad 10 of U102 on B.Cu | (-3.7, 19.1) |
| `/Motor 1/M1_LO_C` | Pad 9 of U102 on B.Cu | Pad 1 of R115 on B.Cu | (-0.1, 11.7) |
| `/Motor 1/M1_SWDIO` | Pad 1 of TP101 on B.Cu | Pad 21 of U101 on B.Cu | (-16.5, 4.0) |
| `/Motor 2/M2_AH` | Pad 20 of U201 on B.Cu | Pad 22 of U202 on B.Cu | (7.2, 7.1) |
| `/Motor 2/M2_BEMF_C` | Pad 11 of U201 on B.Cu | Track on B.Cu, length 0.1102 mm | (5.3, 4.4) |
| `/Motor 2/M2_BEMF_COM` | Pad 2 of R228 on B.Cu | Pad 7 of U201 on B.Cu | (8.2, 15.4) |
| `/Motor 2/M2_BOOT0` | Pad 1 of R201 on B.Cu | Pad 1 of U201 on B.Cu | (-0.9, 8.0) |
| `/Motor 2/M2_HO_B` | Pad 1 of R212 on B.Cu | Pad 16 of U202 on B.Cu | (9.7, -0.3) |
| `/Motor 2/M2_LO_A` | Pad 11 of U202 on B.Cu | Pad 1 of R211 on B.Cu | (11.7, 1.1) |
| `/Motor 2/M2_PH_B` | Pad 15 of U202 on B.Cu | Pad 5 of Q204 on F.Cu | (12.9, 2.8) |
| `/Motor 2/M2_VB_C` | Pad 1 of C209 on B.Cu | Track on B.Cu, length 0.4769 mm | (4.4, 11.1) |
| `/Motor 3/M3_AH` | Pad 22 of U302 on B.Cu | Pad 20 of U301 on B.Cu | (-10.7, -5.0) |
| `/Motor 3/M3_BEMF_B` | Track on In2.Cu, length 0.2206 mm | Pad 10 of U301 on B.Cu | (-9.7, 1.2) |
| `/Motor 3/M3_BEMF_COM` | Pad 7 of U301 on B.Cu | Pad 2 of R328 on B.Cu | (-3.4, -5.1) |
| `/Motor 3/M3_BOOT0` | Pad 1 of U301 on B.Cu | Pad 1 of R301 on B.Cu | (-3.4, -7.5) |
| `/Motor 3/M3_HO_B` | Pad 16 of U302 on B.Cu | Pad 1 of R312 on B.Cu | (-12.9, -3.3) |
| `/Motor 3/M3_LO_A` | Pad 1 of R311 on B.Cu | Pad 11 of U302 on B.Cu | (-15.7, -3.2) |
| `/Motor 3/M3_PH_B` | Pad 5 of Q304 on F.Cu | Pad 15 of U302 on B.Cu | (-15.5, -1.5) |
| `/Motor 3/M3_VB_C` | Pad 1 of C309 on B.Cu | Track on B.Cu, length 0.4769 mm | (-4.4, -11.1) |
| `/Motor 4/M4_BH` | Pad 23 of U402 on B.Cu | Pad 19 of U401 on B.Cu | (4.0, -11.2) |
| `/Motor 4/M4_CH` | Pad 24 of U402 on B.Cu | Pad 18 of U401 on B.Cu | (4.0, -10.7) |
| `/Motor 4/M4_GL_C` | Pad 2 of R415 on B.Cu | Pad 1 of R435 on B.Cu | (-4.5, -18.6) |
| `/Motor 4/M4_GL_C` | Pad 4 of Q406 on F.Cu | Pad 2 of R415 on B.Cu | (0.4, -7.9) |
| `/Motor 4/M4_HO_C` | Pad 1 of R414 on B.Cu | Pad 13 of U402 on B.Cu | (-2.2, -18.2) |
| `/Motor 4/M4_LO_A` | Pad 11 of U402 on B.Cu | Pad 1 of R411 on B.Cu | (0.1, -12.7) |
| `/Motor 4/M4_LO_B` | Pad 10 of U402 on B.Cu | Pad 1 of R413 on B.Cu | (0.1, -12.2) |
| `/Motor 4/M4_LO_C` | Pad 1 of R415 on B.Cu | Pad 9 of U402 on B.Cu | (-3.5, -18.6) |
| `/Motor 4/M4_SWDIO` | Pad 21 of U401 on B.Cu | Pad 1 of TP401 on B.Cu | (6.5, -8.2) |
| `GND` | Zone on B.Cu | Zone on B.Cu | (19.9, -9.1) |
| `GND` | Zone on B.Cu | Zone on B.Cu | (19.9, -9.1) |
| `MOT2_DSHOT` | Pad 4 of J1 on B.Cu | Pad 25 of U201 on B.Cu | (-0.5, 2.0) |
| `MOT3_DSHOT` | Pad 25 of U301 on B.Cu | Pad 5 of J1 on B.Cu | (-5.3, -8.2) |
| `MOT4_DSHOT` | Pad 6 of J1 on B.Cu | Pad 25 of U401 on B.Cu | (1.5, 2.0) |
| `VBAT` | Pad 1 of C110 on B.Cu | Pad 1 of C111 on B.Cu | (-11.8, 5.3) |
| `VBAT` | Pad 1 of C410 on B.Cu | Pad 1 of C411 on B.Cu | (11.8, -5.3) |
| `VBAT` | Pad 1 of C410 on B.Cu | Track on F.Cu, length 0.4600 mm | (11.8, -5.3) |
| `VBAT` | Track on F.Cu, length 0.3394 mm | Pad 1 of C110 on B.Cu | (-9.9, 3.8) |
| `VBAT` | Zone on F.Cu | Zone on F.Cu | (19.9, -9.1) |
| `VBAT` | Zone on F.Cu | Zone on F.Cu | (19.9, -9.1) |
| `VBAT` | Zone on F.Cu | Zone on F.Cu | (19.9, -9.1) |

## ToF side satellite (x3): 0 open


## ToF front satellite: 0 open


