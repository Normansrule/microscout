> STATUS: DRAFT - UNVERIFIED - requires human review at Gate G2

# hardware/libraries

- `microscout.kicad_sym` - project symbols (parts missing from KiCad 7, custom power rails), built by `tools/sch/customsyms.py`.
- `kicad7-symbols/`, `kicad7-footprints/` - copies of the KiCad 7.0 library symbols and footprints this project uses, made by `tools/sch/vendor.py`. The project `sym-lib-table` / `fp-lib-table` files point at them, so KiCad 7, 8 and 9 all see the same parts.
  Licence: CC-BY-SA-4.0 with the KiCad libraries exception (https://www.kicad.org/libraries/license/).
- `kicad7-template.kicad_pro` - the KiCad 7 default project settings used for every generated project.
