> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2

# ESD and protection summary (G2)

This lists what each protection covers and what is left unprotected. Nothing here has been tested. FC means the flight-controller board; ESC means the electronic speed controller board.

| Hazard | Protection in the schematic | Where | Residual risk / check |
|---|---|---|---|
| ESD (electrostatic discharge) on USB | USBLC6-2SC6 on D+/D− and VBUS: 15 kV air / 8 kV contact (IEC 61000-4-2 level 4) | FC U22 at J1 | Layout: put U22 next to the connector with the shortest ground path (G3). The CC lines have no ESD part (5.1 k to GND only). |
| ESD on other exposed contacts | None: ELRS pads, debug pads, ToF and Flow-deck wire pads, balance plug, buttons | – | They sit inside the frame and canopy and are touched only during assembly. Handle with ESD precautions. |
| Reverse battery | **None.** Keyed XT30 and keyed JST-XH only (D-035, OQ-10) | – | A reversed home-made pigtail would destroy the electronics. Buy packs with factory-fitted XT30. |
| Short circuit or overcurrent | **No fuse.** INA226 measures battery current; firmware limits motor output to keep current ≤ 30 A (DR-06); AM32 limits each motor | FC U9 + RS1; ESC firmware | A shorted MOSFET or wiring fault is not interrupted. Unplug after every flight (README, `fly.md`). |
| Over-discharge | Firmware lands at 3.4 V/cell; **hardware cut-off** U23 TLV6700 pulls KILL at 5.77 V (2.89 V/cell), filtered (τ 0.48 s) so load sag does not cut power; disabled while USB is present (Q5) | FC U23, Q5, U8 | The motor power stage stays connected when off (D-036). A pack left plugged in still drains slowly through the off-state leakage (see below). |
| Off-state battery drain | Soft switch turns off the logic rails and the ESC driver supply | FC U8, U24 | Always-on currents, each UNCONFIRMED at G6: LTC2954 about 6 µA, TLV6700 plus divider about 10 µA, TPS62162/TPS62133/TPS22810 shutdown currents, D2 reverse leakage, ESC MOSFET leakage. Rough total < 100 µA, so a 550 mAh pack lasts months, but unplug anyway. |
| Overcharge | BQ25887 regulates 4.20 V/cell by default; the 40 s watchdog falls back to 4.2 V; 12 h safety timer; automatic cell balancing | FC U2 | **No pack thermistor**: TS uses a fixed resistor, so the charger cannot sense pack temperature. Never charge unattended (README). The LiHV pack could take 4.35 V/cell, but 4.20 V is the safe default. |
| USB overvoltage | BQ25887 VBUS over-voltage trip at 6.2-6.6 V; VBUS absolute maximum 20 V (not switching) | FC U2 | D2 passes VBUS into VLOGIC: a 20 V fault charger would reach the 3.3 V and 5 V bucks (rated 17 V operating, 20 V absolute maximum). USB-C sinks with only Rd get 5 V from compliant chargers. |
| Back-powering the camera via I²C | Camera rails always on with 3V3 (D-049) | FC U6, U7 | DOVDD 2.8 V with 3.3 V I²C pull-ups: about 0.5 V above the rail through ~2.2 k. Check against the module's I/O ratings at G2. |
| Motor-driver cross-conduction | FD6288 internal dead time (100-300 ns) plus the AM32 dead-time setting | ESC U102 etc. | Gate resistors (10 Ω) shape the edges; tune at G6. |
| Driver undervoltage | FD6288 UVLO on VCC and the bootstrap supply (4.6 V typ / 5.0 V max on); VDRV boosted to 9.6 V (D-054) | FC U25, ESC | The boost holds 9.6 V while its input sags; the TPS22810 in front of it works down to 2.7 V, far below where the logic browns out. |
| FETs floating while off | 47 k gate-source resistor on every FET (the bridge stays on VBAT when off, D-036) | ESC | – |
| Motors spinning at boot | 100 k pull-downs on the DShot lines; ESC drivers unpowered until the soft switch turns on; 1 k series resistors limit current into an unpowered ESC MCU; no DShot without a battery (DR-08) | FC R34-R37, R42-R45, U24 | Bidirectional DShot idles high when running. AM32's boot behaviour with a low line is a G6 check. |
| Arming while on USB | Firmware rules DR-02 and DR-08; VDRV comes from VBAT only | FC D2/D3, U24 | Without a battery VBAT is not 0 V (charger battery detection, D3 leakage), so VDRV may partly rise: firmware is the interlock in every case. |
| Firmware holding KILL high | GPIO48 reaches KILL only through Schottky D5 (D-055) | FC D5 | – |
| Load-dump / disconnect transients on VBAT | ESC 100 µF polymer + ceramics; no TVS | ESC C1 | No TVS: BQ25887 BAT absolute maximum is 12 V. A TVS that clamps below 12 V would conduct near the 8.8 V pack maximum. Check transients on the bench (G6). |
| Thermal (power stage) | 2 oz outer copper (G1 assumption); 2 × 10 µF + 100 µF polymer bulk capacitance | ESC | 9.2 A per motor gives 0.80 W typical / 1.0 W maximum conduction loss per channel with 9.6 V gate drive (budgets 4c), in bursts. Thermal check at G6. |
