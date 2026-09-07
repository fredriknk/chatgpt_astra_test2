# ESP32 24 V / 4–20 mA controller — preliminary design

Status: revision A schematic captured, 2026-09-07. Five sheets, 93 components, zero KiCad ERC violations. See the [schematic review](schematic_review/README.md) for implemented component choices, verification and remaining bench work. The preliminary choices below are retained as planning context; the schematic review supersedes them where noted.

## Scope and provisional requirements

Confirmed: ESP32 controller, nominal 24 V input, read and generate 4–20 mA.

Accepted architecture: one input and one output; common ground; input accepts an externally powered transmitter or a two-wire transmitter powered from a dedicated board terminal; output sources current into a passive receiver. The output is not a passive two-wire loop-powered transmitter. Exact connected equipment is not yet specified.

## Protection recommendation, 2026-09-07

- Main entry: fuse, bidirectional TVS, TPS26600-class eFuse with reverse polarity blocking, adjustable overvoltage cutoff, current limiting and soft start. Provisional cutoff about 33 V and current limit about 0.4 A; finalize tolerances and inrush. Coordinate TVS clamping at the specified pulse current with eFuse ratings and downstream transient exposure. A nominal TVS voltage is not its clamping voltage.
- Sensor supply: separate current-limited switch, provisionally 35–50 mA, so a cable short does not reset the controller; verify sensor startup current.
- Analog input: MAX14626 is a purpose-built candidate with 27–33 mA current limit, reverse-input blocking and thermal protection. It requires additional transient coordination and ADC protection. Its ground current (40 µA typical, 56 µA maximum under specified conditions) can bypass the shunt in the conventional connection, exceeding the 16 µA accuracy target before calibration. Do not freeze this part until residual error and drift are budgeted; use a lower-leakage limiter/disconnect arrangement if needed. Allow up to 2.8 V protector drop at 24 mA per datasheet. At 33 mA, the 100 ohm shunt develops 3.3 V, so resistor tolerance, limiter overshoot and ADC power-off protection matter.
- ADC branch: series resistance, RC filtering and low-leakage voltage clamps or a fault-protected switch that remains protective with 3.3 V off. Do not rely on internal ADC diodes or a rail clamp that back-powers 3.3 V.
- Analog output: datasheet XTR111 external current-limit network, thermally sized P-MOSFET, reverse-current blocking toward the driver and coordinated terminal transient clamp. Check both polarities of externally applied terminal voltage, including when the board is off. Provisional hardware current limit about 28–30 mA, subject to tolerance and thermal analysis.
- USB: low-capacitance data-line ESD array at connector; keep VBUS out of board power path for this revision.

Protection targets are sustained ±30 V field miswiring where applicable, output/sensor shorts and ordinary handling/hot-plug transients. No IEC surge or ESD compliance is claimed without a selected test level and validation.

Sources: [TPS2660 family](https://www.ti.com/product/TPS2660), [MAX14626 datasheet](https://www.analog.com/media/en/technical-documentation/data-sheets/max14626.pdf), and XTR111 reference below. Component values remain preliminary.

- Supply target: 18–30 V DC continuous.
- Input measurement range: 0–25 mA, nominal signal 4–20 mA.
- Output nominal range: 4–20 mA; allow controlled diagnostic overrange up to about 24 mA.
- Load target: 0–500 ohms including cable resistance, across supply range.
- Update target: 10 readings/s and 10 output updates/s.
- Initial accuracy target: ±16 µA (0.1% of 16 mA span), after individual two-point calibration at room temperature. Temperature range and drift requirement remain open; resolution alone does not establish accuracy.
- Provisional boot/reset behavior: output disabled until DAC configuration and application initialization succeed. Running-firmware failure requires an independent watchdog if guaranteed shutdown is required.

## Circuit blocks and candidate parts

1. Power: fused/current-limited entry, reverse-polarity protection and coordinated TVS clamp; LMR36510-class 65 V / 1 A buck to 3.3 V. Filter the analog supply locally. Choose final clamp and surge circuitry against the lowest rated downstream part, not only the buck rating. XTR111 operating supply tops out at 44 V.
2. MCU: ESP32-S3-WROOM-1 module; select memory variant later. USB data programming, ESD protection, boot/reset controls and UART test pads. Initially require 24 V board power while programming; USB VBUS must not backfeed the board. Follow Espressif supply, strap-pin and antenna rules.
3. Input: protected low-side 100 ohm precision shunt, Kelvin sensing, RC filtering, ADS1115 at 3.3 V. Start with ±4.096 V PGA range to preserve overrange measurement; analog pins still must remain within their supply limits.
4. Output: DAC80501 at 3.3 V with 2.5 V output range, XTR111, external P-channel MOSFET and datasheet current-limiting circuit. Use RSET = 1.00 kohm, preferably 0.01%, low temperature coefficient. Filter DAC output with settling time appropriate for 10 Hz operation.
5. Diagnostics: route XTR111 error flag to MCU with compatible pull-up; hardware default-disable on OD with sequencing checked. Add test points for shunt voltage, DAC voltage, protected supply and 3.3 V. Error flag does not replace measured output-current feedback.

## Calculations

Input: V = I × 100 ohms. At 4 / 20 / 25 mA, voltage is 0.4 / 2.0 / 2.5 V. Shunt dissipation at 25 mA is 62.5 mW; start with a 0.25 W precision part and verify derating. At ±4.096 V ADC range, nominal LSB is 125 µV, equivalent to 1.25 µA. Noise and error budget must be assessed separately.

A direct 24 V miswire across 100 ohms would dissipate 5.76 W. Therefore the bare shunt plus ADC clamp is insufficient. Select a series fault-current limiter/disconnect and coordinated clamps; verify continuous 30 V miswire, reverse voltage, leakage error and power-off behavior before schematic release. Extra series voltage drop reduces available sensor voltage.

Output: XTR111 transfer is IOUT = 10 × VIN / RSET. With 1.00 kohm, 0.4 V gives 4 mA and 2.0 V gives 20 mA; 2.4 V gives 24 mA. A 2.5 V / 16-bit DAC gives approximately 0.381 µA per code. Firmware shall clamp the normal command range and calibration results.

At 20 mA through 500 ohms, the load consumes 10 V. At 18 V input, 8 V remains before supply protection, cable and driver losses. At 24 mA it leaves 6 V. Complete the worst-case compliance calculation using the chosen transistor and protection network.

At 30 V and a near-zero-ohm load, total linear output-stage dissipation approaches 0.60 W at 20 mA or 0.72 W at 24 mA. Select the MOSFET using DC safe operating area and thermal resistance, not only on-resistance; allocate PCB copper and test short-circuit temperatures.

Reserve 3.3 V × 1 A = 3.3 W supply capacity for MCU and local electronics; this is a design allowance, not a measured consumption. Two 24 mA loops add up to 48 mA from the field supply. At 18 V and assumed 85% buck efficiency the combined allowance is about 0.264 A before margin and auxiliary loads. Start with a 24 V / 0.5 A bench supply; finalize fuse, inrush and sensor-power limits separately.

## Proposed terminals and wiring

| Connector | Pins | Purpose |
|---|---|---|
| J1 | VIN24, GND | Board power |
| J2 | SENSOR_PWR, AI_IN, GND | Protected sensor supply and current input |
| J3 | AO_OUT, GND | Sourcing current output |
| J4 | USB | Programming/data; 24 V required initially |

Two-wire input sensor: SENSOR_PWR → sensor +; sensor − → AI_IN. Current returns through the board shunt. Sensor-power terminal needs its own current limit. Minimum sensor voltage is protected supply minus shunt, protection and cable drops.

Externally powered current transmitter: signal current output → AI_IN, signal return → GND, provided the transmitter supports this common-ground connection. Leave SENSOR_PWR unused.

Output: AO_OUT → passive receiver +; receiver − → GND. Do not connect this sourcing output to a receiver terminal that supplies loop power.

All GND terminals and USB ground are electrically common. Isolation remains an architectural decision before schematic capture.

## KiCad structure and layout

Use existing CAD/chatgpt_astra_test2 project. Proposed sheets: top-level interfaces; power/protection; ESP32/USB; analog input; analog output.

Four-layer PCB with continuous ground plane. Keep switch-node copper compact and away from ADC, shunt and DAC. Kelvin-route the shunt and RSET ground return. Place terminal protection near connectors. Keep output transistor heat away from precision resistors. Follow module antenna copper/component keepout. Final dimensions and mounting holes remain open.

## Verification and remaining design work

Before capture: settle channel count/isolation/receiver type; choose exact protection parts and MOSFET; complete worst-case error, compliance and thermal budgets; check all pin logic levels, DAC startup variant, watchdog behavior and power sequencing.

After capture: verify symbols/footprints against manufacturer pinouts, run ERC and review loop paths. After layout: DRC, thermal/return-path review and fabrication outputs.

Bench acceptance: current-limited power-up at 18/24/30 V; input readings at 0/4/12/20/25 mA; output measurements at 4/12/20 mA into 0/250/500 ohms; two-point calibration with independent midpoint checks; open-loop and short-load behavior; reset/brownout/firmware-stall behavior; controlled miswire tests after protection analysis; Wi-Fi activity noise check. Temperature accuracy requires a separately agreed range and test.

## Manufacturer references

- [XTR111 datasheet](https://www.ti.com/lit/ds/symlink/xtr111.pdf): transfer function, compliance, external transistor and protection recommendations.
- [ADS1115](https://www.ti.com/product/ADS1115): ADC ranges and specifications.
- [DAC80501](https://www.ti.com/product/DAC80501): DAC supply, range, reference and startup variants.
- [LMR36510](https://www.ti.com/product/LMR36510): buck candidate.
- [ESP32-S3 schematic checklist](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html): MCU implementation requirements.
