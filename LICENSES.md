# Licences

Wisp uses a different licence per area. The licence file in each directory applies to everything beneath it
unless a file says otherwise (an `SPDX-License-Identifier` header).

| Area | Licence | File |
|---|---|---|
| Hardware designs (none yet for Wisp; frames, mounts and any future boards) | CERN Open Hardware Licence v2, Strongly Reciprocal (CERN-OHL-S-2.0) | added with the first design |
| Firmware (none yet; ArduPilot and the Crazyflie firmware keep their own GPL-3.0 licences) | GNU General Public License v3.0 (GPL-3.0) | added with the first firmware |
| Software (`software/`, `tools/`, the `review/*/calc/` scripts, the Flight Lab, Control Lab and concept code in `docs/`) | MIT (SPDX headers in each source file) | `software/LICENSE`, `tools/LICENSE` |
| Documentation, figures and review packages (`docs/`, `review/`, top-level Markdown) | Creative Commons Attribution-ShareAlike 4.0 (CC-BY-SA-4.0) | `docs/LICENSE`, `review/LICENSE` |
| Fonts in `docs/concepts/fonts/` (Overpass, Saira, Barlow) | SIL Open Font License 1.1 (third party) | `docs/concepts/fonts/README.md` |
| three.js (loaded by the Flight Lab from jsDelivr, not stored here) | MIT (third party) | - |
| The archived MicroScout project (`archive/microscout/`) | As listed in its own folders (hardware CERN-OHL-S-2.0, firmware GPL-3.0, software MIT, documents CC-BY-SA-4.0) | `archive/microscout/*/LICENSE` |

This summary is draft guidance, not legal advice.
