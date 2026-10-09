> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G3

# Stackups (G3)

The thicknesses below are the drafts the layout was drawn for. The fabricator's exact build-up (prepreg type, dielectric constant, copper weights) is chosen at G4, and the impedance note below must be recomputed with it.

## Flight controller: 6 layers, 1.0 mm (D-062)

| Layer | Use | Copper |
|---|---|---|
| L1 (top) | ESP32 module, USB-C, charger, camera FPC, buttons, battery pigtail pads; signals; GND pour | 1 oz (35 um) |
| L2 | **solid GND plane**, the reference for every signal on L1 (no tracks allowed) | 0.5 oz (17.5 um) |
| L3 | signals; GND pour in the space left | 0.5 oz |
| L4 | signals; **+3V3 pour** in the space left | 0.5 oz |
| L5 | **solid GND plane**, the reference for every signal on L6 (no tracks allowed) | 0.5 oz |
| L6 (bottom) | IMU, barometer, magnetometer, regulators, IO expanders, wire pads; signals; GND pour | 1 oz |

The 30 A battery path is a copper island on L1, L3, L4 and L6 (see `trace-widths.md`).

Why 6 layers: on 4 layers the autorouter left 24 connections open even with tracks allowed on the L2 ground plane (which then had long cuts through it), and 66 open once L2 was kept solid. JLCPCB lists 6-layer boards at 1.0 mm (inner copper 0.5, 1 or 2 oz) with free via-in-pad; the price for this board is UNCONFIRMED until the G4 quote.

## ESC: 4 layers, 1.0 mm

| Layer | Use | Copper |
|---|---|---|
| L1 (top) | power MOSFETs, motor pads, bulk capacitor, battery pads; signals; per-phase pours; VBAT pour | 2 oz (70 um) |
| L2 | **solid GND plane** (motor return current; no tracks allowed) | 1 oz |
| L3 | **VBAT plane under the power stages** (FETs, bulk capacitor, battery pads); signals and a GND pour in the logic area. In this draft about 570 mm of signal tracks cross the VBAT plane (to be cleared, README) | 1 oz |
| L4 (bottom) | MCUs, gate drivers, passives; signals; GND pour | 2 oz |

The ESC copper weights are the ones the G1 mass budget and `trace-widths.md` assume. Heavier copper is a special order that costs more and may raise the minimum track and space (check at G4). All copper weights here are UNCONFIRMED.

## Notes for both

- **Thickness:** 1.0 mm keeps the boards light (concept, D-039).
- **Dielectric:** the L1-L2 dielectric matters most on the FC, because the USB pair is meant to run on L1 over the L2 GND plane (it does not yet, see below). On a typical 1.0 mm build it is about 0.1 mm of prepreg (UNCONFIRMED).

## USB differential pair

USB 2.0 Full Speed (12 Mbit/s) is what the ESP32-S3's built-in USB uses. It does not need controlled impedance at these lengths. Freerouting has no differential-pair support, so D+ and D- were routed as two separate 0.2 mm nets. In this draft, connector to protector is about 25 mm per line (mostly L1) and protector to module about 36 to 38 mm per line (mostly L4, over the L5 GND plane), with 4 or 5 vias per line, and the two lines are not kept together. Full Speed should tolerate that, but it is UNCONFIRMED and not good practice. The plan is to re-route the pair by hand as a coupled pair on L1 over the L2 plane, connector to USBLC6-2 to module, when the open connections are finished (README, OQ-19). A 90 ohm geometry (field-solver estimate needed) can be applied then if wanted.

## ToF satellites: 2 layers, 0.8 mm

The sensor sits on the top side and faces out. The passives and the wire pads are on the bottom. Both layers carry a GND pour after routing. There is no impedance-sensitive net on these boards (I2C at 400 kHz or 1 MHz).
