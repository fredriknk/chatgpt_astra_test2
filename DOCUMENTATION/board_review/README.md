# Rev A layout verification

The prototype is fully routed: **0 DRC violations, 0 unconnected items and 0 schematic-parity errors**. See [native DRC JSON](drc.json), [CI DRC report](../chatgpt_astra_test2_drc.rpt) and [USB audit](usb_audit.json).

| Property | Final state |
|---|---|
| Board | 100 x 80 mm, nominal 1.6 mm, four copper layers |
| Components | 93 schematic components plus four M3 mounting holes |
| Copper | 1010 track segments and 106 vias |
| F.Cu / In2.Cu / B.Cu segments | 898 / 75 / 37 |
| In1.Cu | Ground-reference plane; no signal tracks |
| USB | Manual pair, top-layer protected section, symmetric connector joins |
| USB pair skew | Approximately 0.10 mm for both USB-C orientations |
| Thermal copper | U1 EF_RTN and U3/U7 OUT heat-spreading areas; correct nets verified |

[Top copper](routing.svg), [bottom copper](routing_bottom.svg), [top assembly render](../../PICTURES/chatgpt_astra_test2_top.png), [isometric render](../../PICTURES/chatgpt_astra_test2_iso.png), and [board-layer PDF](../chatgpt_astra_test2_board_prints.pdf).

USB data contacts use two through-board transitions per electrical path at the connector-side crossover. Ground return vias and a local In2.Cu ground area reference that bottom-layer section. The remainder runs on F.Cu above In1.Cu. The ESD device's equivalent channels were exchanged consistently in schematic and PCB, and the series resistors moved close to the module. The reported skew measures copper paths plus nominal via depth; internal component paths are excluded. Length matching does not certify impedance: order the specified stackup and have the fabricator confirm 90 ohms differential, +/-10%.

The overall prototype still needs the electrical, thermal and fault tests in [DESIGN.md](../DESIGN.md). CAD checks do not establish measured accuracy, surge immunity or continuous-fault survival. [FABRICATION.md](../FABRICATION.md) records procurement and mechanical-model limitations.

## Milestones

| Commit | Checkpoint |
|---|---|
| 26806e6 | Schematic |
| 2561262 | 100 x 80 mm placement |
| 73e48d3 | Initial buck and DAC routing |
| 2b1e08d | Feedback and analog sensing |
| 8d3c7f9 | Corrected persisted routing classes and fabrication constraints |
| 7b6780f | Bulk routing |
| ae18761 | Ground stitch and routing review |
| 490d238 | Fully connected, DRC-clean PCB |
| 024ed17 | USB refinement, thermal copper and named stackup |

The placement PNG/SVG/JSON and `board_3d.png` in this folder are historical placement-checkpoint artifacts. Use the current routing drawings and `PICTURES/` renders for Rev A.

The Python layout scripts record individual construction steps and expect their respective input checkpoints. **Do not run the placement/schematic generators over the finished project**: they can overwrite routed copper, local footprint refinements and later layout decisions. Open the current KiCad files for normal editing. The repeatable final output entry point is `generate_outputs.bat` or `generate_outputs.sh`.
