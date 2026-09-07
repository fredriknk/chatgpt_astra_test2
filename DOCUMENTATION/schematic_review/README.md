# Revision A schematic review

Open [the KiCad project](../../CAD/chatgpt_astra_test2/chatgpt_astra_test2.kicad_pro), then its root schematic. The design has five A3 sheets and 93 physical components. Project-local symbol and footprint libraries are included.

## Sheet previews

1. [System interfaces](svg/chatgpt_astra_test2.svg)
2. [Power and sensor supply](svg/chatgpt_astra_test2-02%20_%20POWER%20AND%20SENSOR%20SUPPLY.svg)
3. [ESP32 and USB](svg/chatgpt_astra_test2-03%20_%20ESP32%20AND%20USB.svg)
4. [Current input](svg/chatgpt_astra_test2-04%20_%20PROTECTED%20CURRENT%20INPUT.svg)
5. [Current output](svg/chatgpt_astra_test2-05%20_%20PRECISION%20CURRENT%20OUTPUT.svg)

## Implemented decisions

- TPS26600 entry protection: approximately 399 mA current limit, 16.66 V nominal rising UV threshold and 33.80 V nominal rising OV threshold. RTN is deliberately separate from GND. Its exposed pad connects to RTN.
- LMR36510, 22 uH inductor, 100k/43.2k divider, three 22 uF output capacitors: nominal 3.315 V supply. Capacitor effective capacitance under bias and the exact inductor order code still require purchasing review.
- LT3092 sensor supply limiter: approximately 40.2 mA. LT3092 input limiter: approximately 30.1 mA. Both are configured as floating two-terminal limiters. This replaces the preliminary MAX14626 choice and avoids its bypass ground-current error.
- Input uses 100 ohm shunt, 1 kohm ADC series resistor, LM4040 3 V clamp, TMUX1511 powered-off isolation, and ADS1115.
- ESP32-S3-WROOM-1-N8, native USB-C data/programming, manual boot/reset, UART header and status LED. The board requires 24 V while programming. USB VBUS only serves USB-side ESD protection.
- TPS3839G33 supervises 3.3 V. Its SYS_OK signal inhibits the ADC switch and output enable during undervoltage. A diode couples the supervisor to ESP_EN without shorting the push-pull supervisor output when RESET is pressed.
- DAC80501Z is strapped to I2C address 0x49; ADS1115 uses 0x48. DAC firmware must select REF-DIV=1 and BUFF-GAIN=1 before enabling output.
- XTR111 uses 1.00 kohm RSET. Its local 3 V regulator pulls OD high independently of MCU power. Two series NMOS devices require both AO_ENABLE and SYS_OK to enable the output.
- IRF9540N TO-220 P-MOSFET, PNP current limiter, output RC and reverse-blocking diode. The PNP limit is approximately 33–37 mA per the reference approach, deliberately above the controlled output range. This supersedes the provisional 28–30 mA hardware-limit estimate.

## Checks completed

KiCad 9.0.7 loaded and exported all five sheets. ERC reports **zero errors and zero warnings**, with no exclusions introduced. The exported netlist contains 93 components and 97 nets. An independent export check matched 273 connected physical pins to the capture intent and checked every symbol pin against its assigned footprint's numbered pads. Results are in [verification.json](verification.json) and [erc.json](erc.json).

The schematic was rendered to SVG and PNG for visual review. Supply rails and return branches are connected visibly where aligned; named nets connect the remaining functional blocks. Labels marked as global connect between sheets.

## Engineering limits and bench work

This is a populated engineering prototype schematic, not a fabrication release. ERC does not prove analog performance or fault survival.

1. **Accuracy:** ±16 uA after calibration remains a room-temperature target. Quantify ADC gain/nonlinearity, shunt and RSET tolerance/drift, DAC/reference error, clamp leakage and ADC input loading. Validate independent midpoint readings after two-point calibration.
2. **Input protection:** test sustained +30 V and -30 V miswiring, limiter startup overshoot, 3 V clamp recovery and powered-off isolation. D6 and R19 provide transient limiting, but their pulse-energy coordination has not been qualified to an IEC surge level. The 33 V entry TVS likewise does not establish a downstream 33 V clamp.
3. **Thermal:** the input limiter may dissipate about 0.8 W during a positive miswire; the sensor limiter about 1.2 W into a short at 30 V. Allocate copper for each SOT-223 tab's own net. The output MOSFET dissipates roughly 0.6 W into a short at 20 mA/30 V. A -30 V externally forced output can roughly double this; assess heatsinking and DC SOA before promising continuous negative-output fault survival.
4. **Compliance:** at 18 V and 20 mA/500 ohms, 8 V remains for driver, resistors, diode, cable and entry losses. This looks feasible but requires worst-case and bench confirmation. Sensor voltage is reduced by BOTH sensor-supply and input protection drops; verify the actual sensor's minimum voltage, especially at 18 V.
5. **Startup/failure:** test reset, supply ramps and brownout. XTR111 OD does not guarantee absolutely zero startup glitch. No independent firmware watchdog is fitted; a firmware stall that leaves AO_ENABLE asserted can hold the last current command.
6. **Procurement/layout:** finalize exact fuse, inductor, precision resistor and capacitor manufacturer codes, verify package dimensions, and review the layout before manufacturing. Footprint pad coverage is checked; it is not a substitute for the final manufacturer land-pattern review. The PCB file remains the original empty template.

## Firmware pin assignment

| Function | ESP32 GPIO |
|---|---|
| I2C SDA / SCL | 8 / 9 |
| AO enable, active high | 10 |
| AO fault, active low | 11 |
| ADC ready | 12 |
| Status LED | 13 |
| USB D- / D+ | 19 / 20 |
| UART TX / RX | 43 / 44 |
| ROM boot strap | 0 |

## Reproducibility

[build_schematic.py](../../CODE/build_schematic.py) generated the schematic and local libraries. It overwrites generated schematic files when run; preserve manual KiCad edits before regenerating. It reads the existing local KiCad libraries specified near its top. [check_schematic.py](../../CODE/check_schematic.py) checks a freshly exported XML netlist and ERC report. The editable KiCad files do not require either script to open.

Manufacturer references are embedded in IC properties and linked in the [design plan](../esp32_4-20mA_design_plan.md). Additional references: [LT3092](https://www.analog.com/media/en/technical-documentation/data-sheets/lt3092.pdf), [LM4040](https://www.ti.com/lit/ds/symlink/lm4040-n.pdf), [TMUX1511](https://www.ti.com/lit/ds/symlink/tmux1511.pdf), [TPS3839](https://www.ti.com/lit/ds/symlink/tps3839.pdf).
