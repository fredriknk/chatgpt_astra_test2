# Rev A fabrication and assembly

| Item | Specification |
|---|---|
| Outline | 100 x 80 mm; X=50-150 mm, Y=50-130 mm |
| Mounting | Four 3.2 mm NPTH M3 holes, 92 x 72 mm centre spacing |
| Stackup | Nominal 1.6 mm, four layers; JLC04161H-7628 reference construction |
| Finish | ENIG selected in board stackup |
| Outer / inner copper | 35 um / 15.2 um nominal |
| Outer prepreg | 0.2104 mm FR4 7628 each side, nominal Dk 4.4 |
| Core | 1.065 mm FR4, nominal Dk 4.6 |
| Minimum trace / clearance | 0.15 / 0.15 mm; ordinary nets use 0.2 mm clearance |
| Ordinary vias | 0.6 mm land / 0.3 mm drill |
| USB-area vias | 0.5 mm land / 0.25 mm drill, with ground returns |
| Copper-to-edge | At least 0.3 mm, except intentional component overhang |
| USB impedance | Request 90 ohms differential, +/-10%; 0.25 mm width / 0.15 mm gap on paired sections, with local fanout exceptions |

Dielectric/copper values follow the [JLCPCB published stackup](https://jlcpcb.com/impedance). Finished thickness includes process tolerances and coatings; constituent dimensions are not an exact finished-thickness promise. For another fabricator/stackup, recalculate USB geometry. Obtain fabricator impedance confirmation; KiCad width/gap settings and length checks are not a field-solver result.

F.Cu contains primary routing and local thermal copper. In1.Cu is ground with no signal tracks. In2.Cu carries secondary routing and a local ground reference beneath the bottom-layer USB crossover. B.Cu contains short secondary routes and heat-spreading copper.

The antenna overhangs the board by approximately 6.2 mm. Preserve its keepout and allow enclosure clearance for antenna, plugs, terminal access and cable bends. Keep metal away from the antenna region.

## Assembly

- U1's thermal pad/copper is **EF_RTN**, not GND. U3/U7 tabs/copper are their respective **OUT** nets. Top/bottom copper and adjacent vias spread their heat.
- U1/U4/U12 exposed-pad footprints have 0.3 mm plated holes with 0.6 mm lands. Review paste coverage and via tenting/filling with the assembler to manage solder wicking.
- Q3's tab is its drain. Any heatsink must respect insulation/clearance; none is included in the mechanical model.
- All 93 electrical components are on top. Mounting holes are mechanical-only. Assemble through-hole parts separately; the generic position CSV is not a filtered SMT machine program.
- R22/R26 require their stated precision and temperature coefficient. Ceramic capacitors must retain suitable effective capacitance under DC bias. L1 needs the required inductance, saturation/current rating and physical fit.

The engineering BOM retains value/rating specifications for several passives; manufacturer/MPN columns are not fully populated. Confirm purchasing parts and substitutions before ordering or using an assembly service. No vendor-specific assembly package or purchasing order was generated.

## Package and mechanical model

The successful output run is `PRODUCTION/20260907_1303_chatgpt_astra_test2/`. Its ZIP includes Gerbers and drill files. Check the fabricator preview for four copper layers, masks, silk, outline, plated drills and NPTH drills. Paste layers are included for stencil use.

The STEP/renders omit three unavailable library models: J4 USB-C, U11 DAC and U12 XTR111. Their electrical footprints/BOM entries are present. Use PCB/F.Fab geometry and component drawings for those positions; the STEP is not a complete enclosure collision check.

This is a routed prototype with passing CAD checks. [Bring-up and fault tests](DESIGN.md) establish actual operating limits before deployment.
