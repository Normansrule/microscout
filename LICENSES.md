> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G1 (rev B)

# Licences

MicroScout uses a different licence per area. The licence file in each directory applies to everything beneath it unless a file says otherwise.

| Area | Licence | File |
|---|---|---|
| Hardware design (`hardware/`, `bom/`) | CERN Open Hardware Licence v2 - Strongly Reciprocal (CERN-OHL-S-2.0) | `hardware/LICENSE`, `bom/LICENSE` |
| Mechanical design incl. the concept CAD and its exports (`mechanical/`) | CERN-OHL-S-2.0 | `mechanical/LICENSE` |
| Firmware (`firmware/`) | GNU General Public License v3.0 (GPL-3.0) | `firmware/LICENSE` |
| Software (`software/`, `tools/`, and the `review/*/calc/` scripts, which carry `SPDX-License-Identifier: MIT` headers overriding the `review/` default) | MIT | `software/LICENSE`, `tools/LICENSE` |
| Documentation, figures, animations and review packages (`docs/`, `review/`, top-level Markdown) | Creative Commons Attribution-ShareAlike 4.0 (CC-BY-SA-4.0); the inline script in `docs/index.html` is MIT (SPDX header in the file) | `docs/LICENSE`, `review/LICENSE` |
| Visualization and render scripts (`tools/viz/`, `docs/viewer/scene.js`) | MIT (SPDX headers) | `tools/LICENSE` |
| Flight Lab code and policies (`docs/lab/`) | MIT (SPDX headers in every source file) | `tools/LICENSE` (same MIT text) |
| Bundled KiCad 7 library parts (`hardware/libraries/kicad7-*`) | CC-BY-SA-4.0 with the KiCad libraries exception (third party, KiCad project) | `hardware/libraries/README.md` |
| three.js (loaded by the 3D viewer and the Flight Lab from jsDelivr, not stored here) | MIT (third party) | - |

Licence texts are verbatim copies and carry no status header (D-025). Third-party components keep their own licences; the tracking table and audit plan are in `review/G1/license-plan.md`. This summary is draft guidance, not legal advice.
