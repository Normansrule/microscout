# MicroScout (archived)

MicroScout was this repository's first project: a palm-sized ESP32-S3 camera drone on custom printed circuit
boards (PCBs), built through review gates G1-G3. In October 2026 the owner turned the project into **Wisp**
(see `../../wisp-project-context.md`), which starts from off-the-shelf parts and puts the effort into flight
software, control theory and follow-me. Custom PCBs come back later only if they beat the bought parts.

What carried over to Wisp: the Python simulator and SDK (`software/`), the Flight Lab (`docs/lab/`), the control
and reinforcement-learning material, and the gate process.

What is here, frozen:

| Folder | Content | Last state |
|---|---|---|
| `review/G1`-`G3` | Requirements, budgets, schematics, PCB layout review packages | G1 and G2 approved; G3 draft, routing incomplete |
| `hardware/` | KiCad projects: flight controller, ESC (electronic speed controller), ToF (time-of-flight) satellites, remote | G3 draft |
| `bom/`, `mechanical/`, `firmware/` | Bills of materials, concept mechanics, firmware placeholders | G2 |
| `tools-pcb/`, `tools-sch/`, `tools-viz/` | Layout, schematic and figure generators | The ESC power-cell rework in `tools-pcb/esc.py` is unfinished |
| `docs/` | Decisions log, protocol, setup and publishing notes | G3 |

The scripts expect the original folder layout. To rebuild anything, check out branch `archive/microscout-g3-draft`
(commit 45a016a, the last gate deliverable) or commit 9e2e074 (the last one before the move). The MicroScout design explorer page is kept at
`docs/microscout/`.

STATUS: DRAFT - UNVERIFIED. Nothing here was built or tested.
