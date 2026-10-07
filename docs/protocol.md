> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G6 (proposal; no firmware implements it yet)

# Draft SDK ↔ drone link protocol

Proposal for the Wi-Fi (UDP) and BLE link between `microscout` and the firmware (M7). It mirrors the SDK calls one to one so the simulator and the drone behave the same.

| Direction | Message | Fields | Rate |
|---|---|---|---|
| SDK → drone | `ARM`, `DISARM`, `KILL` | - | on demand |
| SDK → drone | `TASK` | kind (takeoff, land, goto, turn, flip), arguments | on demand |
| SDK → drone | `SETPOINT` | kind (rates, attitude, velocity, position), 4 floats, sequence number | 50-100 Hz |
| SDK → drone | `STICKS` | roll, pitch, yaw, throttle | 50 Hz |
| SDK → drone | `MODE` | beginner, sport, acro | on demand |
| SDK → drone | `PARAM_GET` / `PARAM_SET` | name, value | on demand |
| drone → SDK | `TELEMETRY` | the fields of `microscout.Telemetry` | 100 Hz |
| drone → SDK | `TASK_DONE` / `REJECTED` | task, reason | on event |

Proposed framing: little-endian binary, 1-byte message id, 2-byte length, payload, CRC-16. A `SETPOINT` older than 0.5 s triggers the onboard watchdog (hover, then land after 3 s). UDP port 2390 (placeholder). To be settled with the firmware base decision (OQ-8).
