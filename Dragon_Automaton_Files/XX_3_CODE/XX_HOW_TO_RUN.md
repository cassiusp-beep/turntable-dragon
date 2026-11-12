# Scream → dragon: how to run it

## 1. Upload the Arduino code (once)
1. Open `dragon_motor/dragon_motor.ino` in the Arduino IDE.
2. At the top, set `SUPPLY_V` to the **OUTPUT** volts printed on your wall adapter's label. It's the "OUTPUT: __V" line, not the "100-240V" input line.
3. Board: **Arduino Uno**. Port: the one named `usbmodem…`. Click **Upload**.
4. **Close the Serial Monitor** afterwards. Only one program can talk to the Uno at a time.

## 2. Run the scream detector
Open **Terminal** and paste:
```
cd "/Users/cassiuspalacio/Documents/UC Berkeley TDF/PhysComp/Nov 9/Dragon_Automaton_Files/XX_3_CODE"
.venv/bin/python scream_dragon.py
```
- The first time, macOS asks to let Terminal use the **camera** and **microphone**. Click **Allow** for both, then run it again.
- For the first 2 seconds, **look calm and stay quiet**. It learns what "normal" looks like.
- **Scream** (mouth wide open, loud): the bar fills and the dragon speeds up. Calm down and it slows to idle.
- Press **c** to recalibrate, for example in a new room. Press **q** to quit.
- **Backup button:** tap the **space bar** for full-speed "scream" for 3 seconds (tap again to keep going). Use it if the camera or mic struggles during the demo.
- To test without the Uno plugged in: `.venv/bin/python scream_dragon.py --no-serial`

## How it decides
- **Anguish score:** 65% how wide your mouth opens (camera) and 35% how loud you are (mic). It gets a boost when you're doing both.
- **Laptop to Uno:** the score (0–100) goes to the Uno 15 times a second.
- **Speed knob:** optional. It's off in the code (`USE_KNOB = false`); turn it on only if you wire one to A0.
- **Laptop disconnected:** if the laptop stops sending, the dragon idles slowly (`IDLE_PCT` in the Arduino code).

## Tuning (top of each file)
| Problem | Change |
|---|---|
| Dragon too fast even when calm | Lower `IDLE_PCT` (Arduino) |
| Motor hums but doesn't turn at low speed | Raise `MIN_PWM` (Arduino) |
| Too hard to reach full speed | Lower `MOUTH_FULL` or `LOUD_FULL_DB` (Python) |
| Too jumpy | Lower `SMOOTH` (Python) |
| Wave runs head → tail | Swap the two motor wires on OUT1/OUT2 |

## Quick motor test without a barrel jack (USB power only)
The laptop USB can power a short test: the motor is small. Don't leave it stalled.
| From | To |
|---|---|
| Uno 5V | H-bridge 12V terminal and H-bridge 5V terminal (5V-EN jumper pulled off) |
| Uno GND | H-bridge GND |
| D9, D7, D8 | ENA, IN1, IN2 (ENA jumper cap pulled off) |
| OUT1, OUT2 | Motor |

Upload the code. Within 2 seconds the motor should start turning at idle speed. Count how long one turn of the shaft takes.
