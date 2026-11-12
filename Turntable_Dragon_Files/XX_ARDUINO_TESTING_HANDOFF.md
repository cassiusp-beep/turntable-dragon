# Handoff: Arduino testing for the turntable dragon

**Goal:** prove the electronics work end to end before the demo (today, Nov 12):
1. The Uno drives the motor through the H-bridge.
2. The platter turns at idle.
3. The laptop's "anguish" score (camera + mic) makes it spin faster.

This file is for whoever picks up testing in VS Code, human or agent.

---

## 1. What the system is
- **Mechanism:** a 150 mm printed platter with an **internal ring gear** (80 teeth, module 1.5) spins on a centre post. A **pinion on the motor** drives it: 28 teeth (2.86:1) or 17 teeth (4.7:1). A D3Craft Flexi Dragon is glued on top (personal use only, don't share).
- **Motor:** generic **Mini-300 gearmotor**. Spec values (from a web lookup, not measured): 3–7.2 V, about 5–20 rpm, 5 mm dual-D shaft. It's slow, so the 28T pinion is the default.
- **Electronics:**
  - **Elegoo Uno R3** (ATmega328P, shows up as `/dev/cu.usbmodem*`)
  - **L298N** dual H-bridge module (only channel A is used)
  - **Power:** a **6 V wall adapter** for the motor (section 3b). The laptop USB powers the Uno and carries the serial data. USB-only mode (section 3) is the fallback.
- **Laptop:** Mac running `scream_dragon.py` (OpenCV + MediaPipe FaceMesh + sounddevice). It sends `S<0-100>\n` to the Uno at 15 Hz.

## 2. Files
| What | Path |
|---|---|
| Uno firmware | `Turntable_Dragon_Files/XX_3_CODE/dragon_motor/dragon_motor.ino` |
| Scream detector | `Turntable_Dragon_Files/XX_3_CODE/scream_dragon.py` |
| Python env (already set up) | `Dragon_Automaton_Files/XX_3_CODE/.venv/` (Python 3.9.6, mediapipe 0.10.14, opencv, pyserial, sounddevice, numpy) |
| Mechanical read-me | `Turntable_Dragon_Files/XX_READ_ME_FIRST.md` |
| CAD source (Rhino) | `turntable_dragon.py`, `turntable_plates.py` |

The `.venv` only lives in the old folder. In VS Code, pick that interpreter (`…/Nov 9/Dragon_Automaton_Files/XX_3_CODE/.venv/bin/python`) or run with its full path. Don't `pip install` into the system Python.

**Firmware comments are out of date.** The `.ino` header still talks about the old camshaft and a wall adapter. The logic is correct for the turntable; only the comments are stale.

## 3. Wiring (USB power only)
| From | To | Wire | Note |
|---|---|---|---|
| Uno **GND** | L298N **GND** terminal | black | Connect first. Ground must be shared. |
| Uno **5V** | L298N **12V** terminal | red | Motor supply. |
| L298N **12V** terminal | L298N **5V** terminal | red, short | Logic supply. **5V-EN jumper cap removed.** |
| Uno **D9** (PWM) | L298N **ENA** | M–F jumper | **ENA jumper cap removed.** Use the outer ENA pin, not the 5V pin beside it. |
| Uno **D7** | L298N **IN1** | M–F jumper | Direction |
| Uno **D8** | L298N **IN2** | M–F jumper | Direction |
| L298N **OUT1 / OUT2** | Motor terminals | — | Polarity doesn't matter. Swap wires to reverse. |
| Uno USB-B | Mac | USB cable | Powers everything |

**Electrical facts to keep in mind:**
- The L298N drops about **2 V**, so the motor sees roughly **2.7–3 V** from USB's ~4.8 V. That's slow but expected.
- The Uno R3 has a **500 mA polyfuse** on USB power. If the motor stalls (jammed gear), the fuse trips and the Uno resets or disconnects. That's protection, not damage. Unplug, clear the jam and wait about 30 s.
- The L298N module has onboard flyback diodes.

## 3b. Wall power (6 V adapter) — current plan
| From | To | Note |
|---|---|---|
| Adapter + (via female barrel jack-to-terminal) | L298N **12V** terminal | motor supply only |
| Adapter − | L298N **GND** terminal | shares the terminal with the Uno GND wire |
| Uno **5V** | L298N **5V** terminal | logic only (a few mA). **No 12V→5V bridge wire. 5V-EN cap OFF.** |
| D9/D7/D8, OUT1/OUT2, Uno GND | unchanged | |

- **Why not the bridge:** the L298N's 5V regulator needs about 7 V or more, so at 6 V it's marginal. Feeding 6 V straight into the logic terminal is also out of spec. The Uno 5V → logic and adapter → motor split keeps both sides clean, and the two supplies only meet at GND.
- **Firmware:** `SUPPLY_V = 6.0`, `MOTOR_V = 6.0`. That means `topPwm = 255`, and about 4 V reaches the motor (vs about 3 V on USB). If idle is too fast, lower `MIN_PWM` toward 120.
- **Check polarity:** the adapter label should show the centre-positive symbol. Or measure the plug: centre = +6 V.
- **Power order:** USB first, then wall. To unplug, pull the wall adapter first.

## 4. Safety checklist (before every power-up)
- [ ] Red goes only to 5V/12V/5V-terminal. Black goes only to GND. The 3 power terminals are adjacent, so recheck them.
- [ ] No loose strands in the screw terminals. Tug-test each wire.
- [ ] 5V-EN and ENA jumper caps are **off**.
- [ ] The boards sit on a non-conductive surface: not the laptop body, foil or loose screws.
- [ ] **Wall-power mode:** the adapter touches only 12V and GND, and the Uno 5V touches only the 5V terminal. **No bridge wire between 12V and 5V.** USB-only mode is the reverse: no adapter, Uno 5V → 12V plus the bridge.
- [ ] Optional: multimeter continuity between Uno 5V and GND with USB unplugged should **not** beep.

## 5. Firmware behaviour (`dragon_motor.ino`)
- **Serial:** 115200 baud. Command format `S<n>\n`, where n is 0–100 and clamped. Anything else is ignored. The line buffer holds 8 characters.
- **Speed choice:**
  - Laptop message received in the last 2 s: `pct = max(IDLE_PCT, anguish)`.
  - No message for 2 s: `pct = IDLE_PCT` (idle, not stop).
- **PWM:**
  - `target = map(pct, 0, 100, MIN_PWM, topPwm)`.
  - `topPwm = 255` here, because `SUPPLY_V - DROP_V` is 4 V on 6 V wall power (3 V on USB), which is ≤ `MOTOR_V`.
  - Ramp: ±4 PWM every 10 ms, so 0→255 takes about 0.65 s.
- **Direction:** fixed, IN1 HIGH and IN2 LOW.
- **Knob on A0:** disabled (`USE_KNOB = false`).
- **Tunables at the top of the file:**
  - `IDLE_PCT = 25`: calm speed
  - `MIN_PWM = 150`: below this the motor hums instead of turning
  - `SUPPLY_V`, `MOTOR_V`, `DROP_V`: only used to cap the PWM
- **Opening the serial port resets the Uno.** `scream_dragon.py` waits 2 s after opening; any test script must do the same.
- **Not implemented yet:** there's no reply or echo over serial. If you want feedback while testing, add a debug print (e.g. `Serial.println(currentPwm)` every 250 ms), but remove it or rate-limit it afterwards.

## 6. Test plan (in order; stop at the first failure)
| # | Test | How | Pass if |
|---|---|---|---|
| 0 | Mechanics alone | Turn the platter by hand with the motor connected but unpowered | It turns all the way round with no tight spot. The pinion meshes with slight play. |
| 1 | Compile | Arduino IDE or `arduino-cli compile --fqbn arduino:avr:uno dragon_motor` | Builds. It was about 4.5 KB last time. |
| 2 | Upload | Board **Arduino Uno**, port `/dev/cu.usbmodem*` | Upload succeeds |
| 3 | Idle with no laptop | Close every serial tool and wait 2–3 s | The platter creeps at idle. Time one platter turn. |
| 4 | Manual commands | Serial Monitor at 115200, line ending **Newline**. Send `S0`, `S50`, `S100`, `S0` | `S0` holds idle, `S100` is clearly faster, and speed changes ramp smoothly |
| 5 | Timeout | Send `S100`, then stop sending | It drops back to idle within about 2 s |
| 6 | Python, no board | `.venv/bin/python scream_dragon.py --no-serial` | The window opens, it calibrates, and the bar rises when you scream. macOS asks for camera and mic once; allow both. |
| 7 | Full loop | Close Serial Monitor, then `.venv/bin/python scream_dragon.py` | It prints `talking to the Uno on …`. The platter speeds up when you scream and settles back to idle. **Space** forces full speed for 3 s. |
| 8 | Stall safety | Hold the platter briefly (1–2 s max) | The motor stalls and may hum, and nothing gets hot. If the Uno resets, that's the polyfuse working. |

**Serial test without the camera** (useful for test 4 from VS Code). Close Serial Monitor first:
```bash
"/Users/cassiuspalacio/Documents/UC Berkeley TDF/PhysComp/Nov 9/Dragon_Automaton_Files/XX_3_CODE/.venv/bin/python" -c "
import serial,glob,time
s=serial.Serial(sorted(glob.glob('/dev/cu.usbmodem*'))[0],115200); time.sleep(2)
for v in (0,25,50,75,100,50,0):
    print('S',v); t=time.time()
    while time.time()-t<3: s.write(f'S{v}\n'.encode()); time.sleep(1/15)
s.close()"
```

## 7. Tuning guide
| Symptom | Change |
|---|---|
| Motor hums at idle and doesn't turn | Raise `MIN_PWM` (try 170, 190, 210) |
| Idle too fast | Lower `IDLE_PCT`, or swap to the 17T pinion (slower) |
| Still slow even at S100 | On 6 V wall power the motor gets about 4 V; that's the ceiling for this setup. Use the 28T pinion. |
| Hard to reach full speed by screaming | Lower `MOUTH_FULL` or `LOUD_FULL_DB` in `scream_dragon.py` |
| Jumpy | Lower `SMOOTH` in `scream_dragon.py` |
| Uno keeps resetting under load | It's stalling. Check the gear mesh: back the carriage off a hair. |
| `Resource busy` or no port | Serial Monitor or another script is holding the port. Close it. |

## 8. Known unknowns
- **Motor rpm and current aren't measured.** The datasheet values came from a web lookup. Test 3's seconds per turn is the first real number.
- **Motor ear position is assumed** to be at the shaft end of the gearbox, which sets the pinion height. If the pinion sits low, the ring teeth (12.5 mm tall) still cover about ±2 mm.
- **USB current headroom is unknown.** If the polyfuse trips during normal running, not just stalls, the motor needs its own supply.

## 9. Don't
- Don't leave the motor stalled or humming for long.
- Don't power the H-bridge from two sources at once.
- Don't glue the pinion. The dual-D bore drives it, and it can be removed for gear swaps.
- Don't share the dragon STL; it's D3Craft's design, personal use only.
