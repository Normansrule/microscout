> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3

# Autorouted nets (G3)

Every track on these boards was placed by Freerouting 1.9.0 from the KiCad DSN export (`tools/pcb/layout.py`), except the copper islands drawn by the board scripts (planes, battery path, motor phases) and the stitching vias. Nothing was hand-routed. **Every net below needs a human look** (VERIFY G3).

## Flight controller

98 nets carry Freerouting copper:

`+1V2`, `+2V8`, `+3V3`, `+5V`, `/Camera, LEDs, buzzer, receiver/BUZZER_DRV`, `/Camera, LEDs, buzzer, receiver/LED_D0`, `/Camera, LEDs, buzzer, receiver/LED_D1`, `/Camera, LEDs, buzzer, receiver/LED_D2`, `/Camera, LEDs, buzzer, receiver/LED_D3`, `/MCU and USB/BOOT_N`, `/MCU and USB/ESP_EN`, `/MCU and USB/MOT1_DSHOT`, `/MCU and USB/MOT2_DSHOT`, `/MCU and USB/MOT3_DSHOT`, `/MCU and USB/MOT4_DSHOT`, `/MCU and USB/SPARE_IO1`, `/MCU and USB/U0RXD`, `/MCU and USB/U0TXD`, `/MCU and USB/USB_CC1`, `/MCU and USB/USB_CC2`, `/MCU and USB/USB_C_DN`, `/MCU and USB/USB_C_DP`, `/MCU and USB/USB_DN`, `/MCU and USB/USB_DP`, `/Power/BAL_MID`, `/Power/BOOST_FB`, `/Power/BOOST_SW`, `/Power/CHG_BTST`, `/Power/CHG_CBSET`, `/Power/CHG_LED_A`, `/Power/CHG_MID`, `/Power/CHG_PMID`, `/Power/CHG_PSEL`, `/Power/CHG_REGN`, `/Power/CHG_SNS`, `/Power/CHG_STAT`, `/Power/CHG_SW`, `/Power/CHG_TS`, `/Power/DRV_CT`, `/Power/INA_INN`, `/Power/INA_INP`, `/Power/PG_3V3`, `/Power/PG_5V`, `/Power/PWR_BTN`, `/Power/PWR_EN`, `/Power/PWR_KILL_N`, `/Power/PWR_ONT`, `/Power/SS_5V`, `/Power/SW_3V3`, `/Power/SW_5V`, `/Power/UV_KILL_N`, `/Power/UV_SENSE`, `/Power/VBAT_RAW`, `/Power/VDRV_SW`, `/Sensors and expanders/BARO_INT`, `/Sensors and expanders/EXP_RESET_N`, `/Sensors and expanders/MAG_C1`, `/Sensors and expanders/TOF_FWD_LPN`, `/Sensors and expanders/TOF_LEFT_XSHUT`, `/Sensors and expanders/TOF_REAR_XSHUT`, `BUZZER`, `CAM_D0`, `CAM_D1`, `CAM_D2`, `CAM_D3`, `CAM_D4`, `CAM_D6`, `CAM_D7`, `CAM_HREF`, `CAM_PCLK`, `CAM_PWDN`, `CAM_RESET_N`, `CAM_VSYNC`, `CAM_XCLK`, `CHG_INT_N`, `CRSF_RX`, `CRSF_TX`, `EXP_INT_N`, `FLOW_CS_N`, `GND`, `I2C_SCL`, `I2C_SDA`, `IMU_CS_N`, `IMU_INT1`, `LED_DIN_3V3`, `MCU_KILL_N`, `MOT1_LINK`, `MOT2_LINK`, `MOT3_LINK`, `MOT4_LINK`, `SPI_MISO`, `SPI_MOSI`, `SPI_SCK`, `VBAT`, `VBUS`, `VBUS_DET`, `VDRV`, `VLOGIC`

## 4-in-1 ESC

110 nets carry Freerouting copper:

`+3V3_ESC`, `/Motor 1/M1_AH`, `/Motor 1/M1_AL`, `/Motor 1/M1_BEMF_A`, `/Motor 1/M1_BEMF_B`, `/Motor 1/M1_BEMF_C`, `/Motor 1/M1_BEMF_COM`, `/Motor 1/M1_BL`, `/Motor 1/M1_BOOT0`, `/Motor 1/M1_CL`, `/Motor 1/M1_GH_A`, `/Motor 1/M1_GH_B`, `/Motor 1/M1_GH_C`, `/Motor 1/M1_GL_A`, `/Motor 1/M1_GL_B`, `/Motor 1/M1_HO_A`, `/Motor 1/M1_HO_B`, `/Motor 1/M1_NRST`, `/Motor 1/M1_PH_A`, `/Motor 1/M1_PH_B`, `/Motor 1/M1_PH_C`, `/Motor 1/M1_SWCLK`, `/Motor 1/M1_VB_A`, `/Motor 1/M1_VB_B`, `/Motor 1/M1_VB_C`, `/Motor 2/M2_AL`, `/Motor 2/M2_BEMF_A`, `/Motor 2/M2_BEMF_B`, `/Motor 2/M2_BEMF_C`, `/Motor 2/M2_BEMF_COM`, `/Motor 2/M2_BH`, `/Motor 2/M2_BL`, `/Motor 2/M2_CH`, `/Motor 2/M2_CL`, `/Motor 2/M2_GH_A`, `/Motor 2/M2_GH_B`, `/Motor 2/M2_GH_C`, `/Motor 2/M2_GL_A`, `/Motor 2/M2_GL_B`, `/Motor 2/M2_GL_C`, `/Motor 2/M2_HO_A`, `/Motor 2/M2_HO_C`, `/Motor 2/M2_LO_B`, `/Motor 2/M2_LO_C`, `/Motor 2/M2_NRST`, `/Motor 2/M2_PH_A`, `/Motor 2/M2_PH_B`, `/Motor 2/M2_PH_C`, `/Motor 2/M2_SWCLK`, `/Motor 2/M2_SWDIO`, `/Motor 2/M2_VB_A`, `/Motor 2/M2_VB_B`, `/Motor 2/M2_VB_C`, `/Motor 3/M3_AL`, `/Motor 3/M3_BEMF_A`, `/Motor 3/M3_BEMF_B`, `/Motor 3/M3_BEMF_C`, `/Motor 3/M3_BEMF_COM`, `/Motor 3/M3_BH`, `/Motor 3/M3_BL`, `/Motor 3/M3_CH`, `/Motor 3/M3_CL`, `/Motor 3/M3_GH_A`, `/Motor 3/M3_GH_B`, `/Motor 3/M3_GH_C`, `/Motor 3/M3_GL_A`, `/Motor 3/M3_GL_B`, `/Motor 3/M3_GL_C`, `/Motor 3/M3_HO_A`, `/Motor 3/M3_HO_C`, `/Motor 3/M3_LO_B`, `/Motor 3/M3_LO_C`, `/Motor 3/M3_NRST`, `/Motor 3/M3_PH_A`, `/Motor 3/M3_PH_B`, `/Motor 3/M3_PH_C`, `/Motor 3/M3_SWCLK`, `/Motor 3/M3_SWDIO`, `/Motor 3/M3_VB_A`, `/Motor 3/M3_VB_B`, `/Motor 3/M3_VB_C`, `/Motor 4/M4_AH`, `/Motor 4/M4_AL`, `/Motor 4/M4_BEMF_A`, `/Motor 4/M4_BEMF_B`, `/Motor 4/M4_BEMF_C`, `/Motor 4/M4_BEMF_COM`, `/Motor 4/M4_BL`, `/Motor 4/M4_BOOT0`, `/Motor 4/M4_CL`, `/Motor 4/M4_GH_A`, `/Motor 4/M4_GH_B`, `/Motor 4/M4_GH_C`, `/Motor 4/M4_GL_A`, `/Motor 4/M4_GL_B`, `/Motor 4/M4_HO_A`, `/Motor 4/M4_HO_B`, `/Motor 4/M4_NRST`, `/Motor 4/M4_PH_A`, `/Motor 4/M4_PH_B`, `/Motor 4/M4_PH_C`, `/Motor 4/M4_SWCLK`, `/Motor 4/M4_VB_A`, `/Motor 4/M4_VB_B`, `/Motor 4/M4_VB_C`, `/Power and link/SW_3V3E`, `GND`, `MOT1_DSHOT`, `VBAT`, `VDRV`

## ToF side satellite (x3)

5 nets carry Freerouting copper:

`+3V3`, `/VL53L1X satellite/SCL`, `/VL53L1X satellite/SDA`, `/VL53L1X satellite/XSHUT`, `GND`

## ToF front satellite

8 nets carry Freerouting copper:

`+3V3`, `/VL53L5CX satellite/I2C_RST`, `/VL53L5CX satellite/INT_N`, `/VL53L5CX satellite/LPN`, `/VL53L5CX satellite/RSVD6`, `/VL53L5CX satellite/SCL`, `/VL53L5CX satellite/SDA`, `GND`
