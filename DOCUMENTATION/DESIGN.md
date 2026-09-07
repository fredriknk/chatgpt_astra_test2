# Rev A design and bring-up guide

## Purpose and status

This board accepts nominal 24 V DC, measures one 4-20 mA process signal, and generates one sourcing 4-20 mA signal under ESP32-S3 control. The schematic and PCB are complete and the output pipeline passes. Firmware is not included.

The intended input range is 18-30 V DC. The room-temperature accuracy target is approximately +/-16 uA after calibration; this is not a measured specification. There is no galvanic isolation or system-level IEC qualification.

## Connector wiring

Pin numbers refer to the schematic and square/pin-1 PCB pads. Field terminals also have silkscreen labels.

| Connector | Pin | Function |
|---|---:|---|
| J1, DC input | 1 | Positive nominal 24 V |
| J1 | 2 | GND |
| J2, current input | 1 | Current-limited sensor supply, approximately 40 mA limit |
| J2 | 2 | AI_IN: positive current input |
| J2 | 3 | GND |
| J3, current output | 1 | AO_OUT: sourcing current output |
| J3 | 2 | GND / receiver return |
| J4 | USB-C | Native ESP32 USB data; does not power the board |
| J5 | 1 | GND |
| J5 | 2 | ESP32 UART TX, GPIO43 |
| J5 | 3 | ESP32 UART RX, GPIO44 |
| J5 | 4 | Board 3.3 V; logic reference, not a second power input |

For a two-wire loop-powered transmitter, connect J2.1 to its positive supply terminal and its negative/current return terminal to J2.2. For an independently powered current output, connect its output to J2.2 and its reference to J2.3; leave J2.1 unused. Do not parallel J2.1 with another supply.

Connect J3.1 to a passive receiver's current-input positive terminal and its return to J3.2. This output supplies loop current; it is not a two-wire passive transmitter. Available load compliance depends on supply voltage, cable resistance and driver/transistor/protection drops. Verify it at minimum supply voltage and maximum intended load. All field and USB grounds are common.

## Power and protection

| Block | Devices and intended behavior |
|---|---|
| Input protection | F1 500 mA fuse, D1 SMBJ33CA TVS and U1 TPS26600 eFuse |
| eFuse settings | R1/R2: nominal 16.66 V undervoltage threshold; R3/R4: nominal 33.80 V overvoltage threshold; R5: approximately 399 mA current limit; C2: controlled startup ramp |
| Protected rail | V24_PROT, with bulk capacitance and D2 negative-output clamp |
| Logic regulator | U2 LMR36510, L1 22 uH and R6/R7 feedback; nominal 3.315 V |
| Sensor supply | U3 LT3092 and R8/R9 limit J2.1 current to approximately 40.2 mA |
| Reset supervision | U5 TPS3839 monitors 3.3 V; D3 couples its output to ESP_EN without shorting the supervisor's push-pull output when RESET is pressed |

Thresholds/current limits are nominal calculations; tolerances, hysteresis and transients matter. Protection must be verified with a current-limited source before deployment. The eFuse's RTN/thermal pad is its own net, not GND. LT3092 tabs are OUT. Q3's tab is its drain. The layout preserves these net assignments.

## Current input

The path is J2.2 -> D5 -> R19 -> D6/U7 protection -> R22 shunt -> GND. U7 limits abnormal positive input current to approximately 30.1 mA. R22 is 100 ohms, 0.01%, target 10 ppm/degree C. It develops 0.4 V at 4 mA and 2.0 V at 20 mA.

R23, U8 LM4040-3.0 and D7 clamp the measurement node. U9 TMUX1511 disconnects the ADC path when SYS_OK is low. U10 ADS1115 measures AI_ADC single-ended against ground. The shunt has a dedicated sense takeoff and a return to the reference plane.

For ADS1115 configured to +/-4.096 V full scale:

```text
Vshunt = signed_adc_code * 125 uV
Iinput = Vshunt / 100 ohms = signed_adc_code * 1.25 uA
```

Ideal readings are approximately 3200 counts at 4 mA and 16000 counts at 20 mA. The ADC range setting does not permit the input pin to exceed its supply rails. Reject communication failures and out-of-range readings in firmware; choose filtering/data rate for the required response and noise level.

## Current output

U11 DAC80501Z drives U12 XTR111. R26 is 1 kohm, 0.01%, target 10 ppm/degree C:

```text
Ioutput = 10 * Vdac / R26 = 10 mA/V * Vdac
```

Configure the DAC for an effective 2.5 V full-scale span: internal reference enabled, REF-DIV=1 and BUFF-GAIN=1. Nominal 4 mA and 20 mA codes are approximately 10486 and 52429. Confirm register programming and actual DAC span during bring-up before enabling the output.

R25/C22 filter the DAC output. Q3 IRF9540 provides high-side drive. Q4/R30 add a fallback current limit, nominally 33-37 mA rather than a precision limit. R31/C25, D8 and D9 provide output filtering and fault/transient protection. Load compliance must account for their series drops.

R27 pulls XTR_OD high, disabling output independently of the MCU supply. Q1/Q2 pull it low only when AO_ENABLE and SYS_OK are high. AO_FAULT_N reports the driver's active-low error output. The design defaults to disabled at reset, but startup/shutdown current glitches still require measurement. There is no independent watchdog that forces zero current if firmware stalls with AO_ENABLE high.

## Firmware interface

| Signal | ESP32-S3 GPIO | Notes |
|---|---:|---|
| I2C SDA / SCL | 8 / 9 | 4.7 kohm pull-ups to 3.3 V |
| AO_ENABLE | 10 | Active high; keep low until analog configuration is verified |
| AO_FAULT_N | 11 | Active-low XTR111 fault |
| ADC_RDY | 12 | ADS1115 ALERT/RDY, with pull-up |
| Status LED | 13 | Green LED through R14 |
| USB D- / D+ | 19 / 20 | Native USB, 22 ohm series resistors and ESD protection |
| UART TX / RX | 43 / 44 | J5, 3.3 V logic |
| BOOT | 0 | BOOT button / download strap |

ADS1115 uses 7-bit address **0x48**; DAC80501 uses **0x49**. Select ESP32 firmware/USB settings appropriate to the module and programming method.

Startup sequence:

1. Hold AO_ENABLE low, initialize GPIOs/I2C, and verify both analog devices respond.
2. Configure the DAC reference/divider/gain and write a safe code while output remains disabled.
3. Configure ADS1115 channel/range/rate and discard unsettled readings.
4. Load valid calibration coefficients, check supply state and AO_FAULT_N, then enable output deliberately.
5. Clamp normal commands to the supported range. Disable output on detected analog communication or supply faults and define recovery behavior explicitly.

## Calibration

Calibrate at stable temperature using instruments comfortably more accurate than the target board accuracy. For input calibration, apply known currents I1/I2 near 4/20 mA and record codes C1/C2. Use `I = I1 + (C-C1)*(I2-I1)/(C2-C1)`. Check intermediate points and repeat after power cycling.

For output calibration, measure currents at two safe DAC codes and derive code-versus-current slope/offset. Validate at 4, 8, 12, 16 and 20 mA with representative loads. Store coefficients with a version/checksum, board serial number, date, temperature and reference instrument. Reject missing/corrupt calibration rather than presenting calibrated accuracy.

## Bring-up and acceptance tests

| Step | Check |
|---|---|
| Unpowered inspection | Orientation, bridges, exposed-pad joints, precision grades, polarity and rail resistance |
| First power | Current-limited source, no field loads; inspect V24_PROT, 3.3 V, consumption and temperature |
| Programming | RESET/BOOT, UART, both USB-C orientations, enumeration, sustained transfers and reconnects |
| Analog supplies | XTR regulator and DAC reference/span; AO_ENABLE low must leave output disabled |
| Input transfer | 0, 4, 12, 20 and modest overrange current, noise/settling, power-off injection |
| Output transfer | Representative loads, minimum-supply compliance, open/short load and fault indication |
| Sequencing | Ramps, brownouts, rapid cycling, USB-only connection, loss of MCU supply, reset during output |
| Faults | Incremental current-limited field miswiring/reversal; record clamp waveforms and temperature |
| Thermal | Maximum normal load and sensor/output shorts at intended ambient/enclosure conditions |

TP1 is the shunt node, TP2 the ADC-side node, and TP3 the filtered DAC voltage. Use a nearby ground when probing fast clamp behavior.

U3 can dissipate approximately 1.2 W during a 30 V sensor-supply short; U7 can approach 0.8 W during a positive input fault. Copper spreads heat but does not replace thermal testing. Q3 dissipates roughly 0.6 W at 20 mA into a short from a 30 V rail; externally forcing the output negative increases dissipation. Establish fault duration and any heatsink/ambient derating before sustained-fault use.

## References

- [Espressif layout guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/pcb-layout-design.html): reference plane and USB requirements.
- [TPS2660](https://www.ti.com/lit/ds/symlink/tps2660.pdf), [LMR36510](https://www.ti.com/lit/ds/symlink/lmr36510.pdf): power/protection.
- [LT3092](https://www.analog.com/media/en/technical-documentation/data-sheets/3092fc.pdf): current limiting/thermal behavior.
- [ADS1115](https://www.ti.com/lit/ds/symlink/ads1115.pdf), [DAC80501](https://www.ti.com/lit/ds/symlink/dac80501.pdf), [XTR111](https://www.ti.com/lit/ds/symlink/xtr111.pdf): conversion and configuration.
- [ST USBLC6-2](https://www.st.com/resource/en/datasheet/usblc6-2.pdf): equivalent ESD channels and short reference connections.

Earlier planning notes retain calculation history. This guide and the current CAD files describe final Rev A.
