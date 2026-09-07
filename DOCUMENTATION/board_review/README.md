# PCB routing draft

The schematic checkpoint is **26806e6**. The serviceable 100 x 80 mm placement checkpoint is **2561262**. The first routing pass is committed as **73e48d3** (`Start buck converter and DAC PCB routing`). The working board contains a second routing pass.

[Open the board](../../CAD/chatgpt_astra_test2/chatgpt_astra_test2.kicad_pcb) · [Top placement drawing](placement.svg) · [3D preview](board_3d.png)

## Mechanical arrangement

- Base PCB: **100 x 80 mm**, four copper layers, nominal 1.6 mm thickness.
- Four 3.2 mm mounting holes for M3 fasteners; hole centres form a 92 x 72 mm rectangle.
- All 93 schematic components are placed on the top side, plus four board-only mounting holes.
- Field screw terminals face outward along the lower edge. USB-C, BOOT and RESET are on the opposite edge. UART is accessible along the right edge.
- The ESP32 antenna overhangs the upper PCB edge by approximately 6.2 mm. Allow space for this overhang, mating connectors, cable bends and enclosure clearance. The PCB outline dimensions do not include component overhangs.
- The switching supply is on the left, the current input and ADC are central, and the current output is on the right. The TO-220 output transistor has room around its body for handling; a particular heatsink has not been selected or collision-checked.
- Reference designators and terminal pin labels are on the silkscreen. The shunt, ADC and DAC test points have descriptive labels.

## Electrical layout state

This is a **partially routed board, not fabrication ready**. The first pass added 48 top-layer track segments for the buck input bypass, bootstrap, switch-to-inductor connection, output capacitor supply connections, VCC bypass, feedback resistor interconnect, and DAC reference/output filter. C4, C5 and C6 moved locally to improve buck routing.

The second pass adds buck feedback on B.Cu, output-voltage sensing, 23 local ground stitching connections, a dedicated input-shunt sense takeoff, input clamp connections, and the XTR111 set-resistor connection. There are now **104 track segments and 29 vias**. KiCad reports **162 unconnected items**, down from 190 after pass one and 208 at placement.

USB, power distribution, most controller connections, analog signal completion and additional ground/thermal connections remain required. The shunt ground and RSET ground connect to the continuous plane, but their full return-current environment still requires review after remaining routing. No completed functional block or controlled-impedance routing is claimed yet. [Current top copper drawing](routing.svg) and [bottom copper drawing](routing_bottom.svg). The placement and 3D images above show the earlier placement checkpoint.

The current DRC report has **zero geometry/rule violations** and **zero schematic parity issues**, with no exclusions introduced. This includes checking component courtyards, copper clearances, silkscreen and the schematic-to-board net assignments. The open connections are reported separately and remain required work. See [drc.json](drc.json).

The layer plan is:

| Layer | Intended use |
|---|---|
| F.Cu | Components, short analog paths, switching regulator local loops |
| In1.Cu | Continuous ground reference; plane is defined and filled |
| In2.Cu | Power distribution and secondary routing |
| B.Cu | Secondary signal routing and thermal copper |

The board has net classes for 24 V, 3.3 V, analog signals and USB. USB track width and gap are preliminary; select the manufacturer's actual dielectric stackup before calculating the 90-ohm differential pair geometry.

## Changes made for board design

The project-local thermal-hole footprints for U1, U4 and U12 now use 0.3 mm plated holes with 0.6 mm copper lands, matching the initial fabrication constraints. These changes preserve the component lead/pad numbering. Revisit solder wicking, via tenting/filling and thermal performance before manufacture.

Silkscreen segments that would cross the board edge at the ESP32 antenna and USB opening were moved to the fabrication layer in their local footprints. They remain available for assembly/mechanical review.

The 3D preview uses installed KiCad models. The **USB connector, DAC U11 and current driver U12 lack their corresponding installed models**, so those three locations show pads in the rendering. They are present in the PCB and netlist; the image is not a complete assembled-board model.

## Routing priorities

1. Tighten and route the buck converter input bypass, switch node, bootstrap capacitor, inductor and output return loop against the manufacturer layout guidance. Current placement is a starting point and may move locally during routing.
2. Route USB as a short controlled-impedance pair above the ground reference. Check the final connector and module pad transitions.
3. Kelvin-route the 100-ohm input shunt and XTR111 RSET. Keep their ground returns away from switching and output-stage currents.
4. Add thermal copper and vias on the correct nets: eFuse RTN is not GND; LT3092 tabs are their OUT nodes; the output MOSFET tab is its drain.
5. Complete the 24 V and 3.3 V distribution, signal routing, ground connections and stitching. Preserve the antenna keepout on all copper layers.
6. Run full connected-board DRC and schematic parity, review return paths and thermal regions, then produce fabrication outputs after the remaining schematic/protection review.

The circuit-level limits and fault/accuracy tests remain in the [schematic review](../schematic_review/README.md). The initial placement alone does not validate them.

## Reproduction

[build_board.py](../../CODE/build_board.py) uses KiCad 9's bundled Python and the exported schematic XML netlist. It regenerates the board and project net classes, so preserve manual layout changes before running it. Its coordinate table is measured in millimetres from the upper-left corner of the base PCB.

[start_routing.py](../../CODE/start_routing.py) applies this initial routing to an unrouted placement board using KiCad 9 Python. It refuses to overwrite existing tracks. Do not rerun the placement generator on the current board: it would discard routing. The placement JSON remains a record of the placement checkpoint; the PCB is authoritative for current positions.

[continue_routing.py](../../CODE/continue_routing.py) applies pass two to the 48-segment first-pass board. It checks the starting track count and must not be applied to later routing. The current PCB is the editable design deliverable; scripts are records of these specific layout passes.

The source XML netlist is ignored by this repository's existing `.gitignore`. Regenerate it with `kicad-cli sch export netlist --format kicadxml` from the root schematic into `DOCUMENTATION/schematic_review/netlist.xml` before building in a fresh checkout.

Placement references: [Espressif module layout guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html) and [LMR36510 manufacturer layout guidance](https://www.ti.com/lit/ds/symlink/lmr36510.pdf).
