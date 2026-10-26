> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2

# Sources read for G2 (2026-10-07)

The agent's shell could not reach vendor sites. Every datasheet below was read through a web-fetch text extractor, which loses figures and some tables. Anything that came only from a figure is marked UNCONFIRMED in `reference-designs.md`.

## Datasheets and reference designs

| Part | Source | Used for |
|---|---|---|
| TI BQ25887 | https://www.ti.com/lit/ds/symlink/bq25887.pdf (SLUSD89); EVM guide https://www.ti.com/lit/pdf/sluuc12 | Pins, capacitors, inductor, ILIM, TS, CBSET, I²C address, defaults. Section 9.2 (typical application) did not extract. |
| TI TPS62162 / TPS62133 / TPS6213x family | https://www.ti.com/lit/ds/symlink/tps62162.pdf, https://www.ti.com/lit/ds/symlink/tps62133.pdf, TPS62130 datasheet SLVSAG7F | Pins, typical applications, fixed-output versions |
| ADI LTC2954-1 | https://www.analog.com/media/en/technical-documentation/data-sheets/2954fb.pdf | Pins, EN/INT/KILL behaviour, ONT/PDT formula, Fig. 5/6/9 |
| TI INA226 | https://www.ti.com/lit/ds/symlink/ina226.pdf | Address table, input filter, VBUS range |
| TI TPS22810 | https://www.ti.com/lit/ds/symlink/tps22810.pdf | DBV pins, EN, CT, QOD, C_IN : C_L |
| TI TLV6700 | https://www.ti.com/lit/ds/symlink/tlv6700.pdf | Pins, thresholds, open-drain outputs |
| TDK ICM-42688-P | DS-000347 v1.6, https://product.tdk.com/system/files/dam/doc/product/sensor/mortion-inertial/imu/data_sheet/ds-000347-icm-42688-p-v1.6.pdf | Pins, supplies, decoupling (Table 11) |
| ST VL53L1X | https://www.st.com/resource/en/datasheet/vl53l1x.pdf | Pins, Fig. 3 application circuit |
| ST VL53L5CX | DS13754 Rev 13, https://www.st.com/resource/en/datasheet/vl53l5cx.pdf | Pins (Table 3), supplies (Table 12), Fig. 5 |
| TI TCA6408A | https://www.ti.com/lit/ds/symlink/tca6408a.pdf | Pins, address, RESET/INT |
| QST QMC5883P | https://cdn-shop.adafruit.com/product-files/6388/C2847467.pdf | Pins, C1 capacitor, address 0x2C |
| Bosch BMP390 / BMP388 | https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp390-ds002.pdf; BMP388 DS001-07 | Pins (identical), I²C wiring |
| Bitcraze Flow deck v2 | https://www.bitcraze.io/products/flow-deck-v2/; deck pinout https://www.bitcraze.io/documentation/system/platform/cf2-expansiondecks/; breakout and Flow v1 schematics | Size, weight, price, which deck pins it uses. The v2 schematic was not found. |
| Espressif ESP32-S3-WROOM-1 | https://documentation.espressif.com/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf; https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html | Pin table, peripheral schematic, strapping, USB |
| Espressif ESP32-S3-EYE main board v2.2 | https://dl.espressif.com/dl/schematics/SCH_ESP32-S3-EYE-MB_20211201_V2.2.pdf | OV2640 24-pin FPC pinout, camera rails |
| OmniVision OV2640 | https://www.uctronics.com/download/cam_module/OV2640DS.pdf (v1.6) | Supply ranges (core 1.14-1.26 V) |
| Microne ME6211 | https://datasheet.lcsc.com/datasheet/pdf/d15331d096a848ac81a26b001a32d4e3.pdf | Pins, input range, CE |
| ST USBLC6-2 | https://www.st.com/resource/en/datasheet/usblc6-2.pdf (DS4260 Rev 7) | Pins, connection |
| Worldsemi WS2812B-2020 | LCSC C965555 datasheet V1.5 | Pins, VIH = 0.65 VDD |
| TI SN74AHCT1G125 | https://www.ti.com/lit/ds/symlink/sn74ahct1g125.pdf | Pins, 2 V VIH at 5 V |
| Artery AT32F421 | Datasheet V2.02 (mirror https://macrogroup.ru/upload/iblock/05c/ltnkuvqbxdy1gvf9o1d4y5yjnm8vonqk/DS_AT32F421_V2.02_EN.pdf) | QFN-28 pin table, supply, BOOT0, NRST |
| Fortior FD6288 | Datasheet V1.6, https://shop.mev-elektronik.com/wp-content/uploads/FD6288.pdf | Pins, VCC range, UVLO, logic levels, dead time, bootstrap |
| HL 60N03D | https://datasheet.lcsc.com/datasheet/pdf/bd8b126d6ff95c77de6f200dd9f0ad95.pdf?productCode=C7471100 | Vds, Rds(on), Qg (typ/max split read from garbled text) |
| AM32 firmware | https://github.com/am32-firmware/AM32 at commit 50234143 (`Inc/targets.h` target OPENESC_20_F421, `Mcu/f421/Src/*.c`) | ESC pin map, PWM polarity, dividers, flashing |
| OpenESC-20x20 | https://github.com/incutec-hw/OpenESC_20X20 (CERN-OHL-S-2.0) | Back-EMF network topology (traced from wire coordinates) |

## Part availability (LCSC / JLCPCB pages, 2026-10-07)

All new G2 part numbers, prices and stock are in `bom/drone-bom-g2.csv` (columns `unit_usd`, `price_break`, `stock_seen`, `fetched_utc`). Notable findings:

- **BMP390** C5124834, **DPS310** C3232509 and **SPL06-001** C2684428 are out of stock. **BMP388** C779278 is in stock (~5,000).
- **Fortior FD6288Q** C328453 is out of stock. **JSMSEMI FD6288Q** C7466367 is in stock (11,431) but its listing says VCC 8-20 V (OQ-13).
- **TPS62132RGTR** C81563 is out of stock, which is why D-048 is used instead.
- **TPS3710DDCR** C140262 is out of stock; the TLV6700DDCR C2868382 is used instead.
- Passives: UNI-ROYAL and Samsung parts, mostly JLCPCB Basic (JLCPCB stock from jlcsearch.tscircuit.com).
