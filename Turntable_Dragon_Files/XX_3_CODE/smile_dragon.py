"""Smile switch for the turntable dragon (Mac).

The webcam watches your face. Smile -> the platter spins at full speed. No smile (or no face) -> it stops.
Sends "S100" or "S0" to the Uno at 15 Hz (dragon_motor.ino: S0 = stopped, laptop gone for 2 s = stopped).

Run (with the Python env from the old folder):
    .venv/bin/python smile_dragon.py              # finds the Uno automatically
    .venv/bin/python smile_dragon.py --no-serial  # test the camera without the Uno
Keys in the window: q = quit, c = calibrate (relaxed face, no smile, for 2 seconds), SPACE = force on for 3 s.

How a smile is measured: mouth width / face width, compared with your relaxed face from calibration.
A smile widens the mouth; talking or opening the mouth doesn't, so those don't trigger it.
"""
import argparse
import glob
import math
import sys
import time

import cv2
import numpy as np

try:
    import mediapipe as mp
except ImportError:
    sys.exit("mediapipe is missing: use the .venv python")

try:
    import serial
except ImportError:
    serial = None

# ---- tuning ----
SMILE_ON = 0.10    # mouth this much wider than relaxed (0.10 = +10%) turns the motor on
SMILE_OFF = 0.06   # ...and it turns off again below this (the gap stops flicker)
HOLD_ON = 0.15     # seconds a smile must last before the motor starts
HOLD_OFF = 0.30    # seconds without a smile before the motor stops
SEND_HZ = 15


def find_uno():
    ports = sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.wchusbserial*"))
    return ports[0] if ports else None


def smile_ratio(lm):
    """mouth width (corners 61/291) / face width (cheek edges 234/454), from MediaPipe face-mesh landmarks"""
    mouth = math.dist((lm[61].x, lm[61].y), (lm[291].x, lm[291].y))
    face = math.dist((lm[234].x, lm[234].y), (lm[454].x, lm[454].y)) + 1e-6
    return mouth / face


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", help="serial port of the Uno (default: auto)")
    ap.add_argument("--no-serial", action="store_true", help="don't talk to the Uno")
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args()

    link = None
    if not args.no_serial:
        if serial is None:
            sys.exit("pyserial is missing: use the .venv python")
        port = args.port or find_uno()
        if not port:
            sys.exit("No Uno found. Plug in the USB cable, or run with --no-serial to test.")
        link = serial.Serial(port, 115200, timeout=0)
        time.sleep(2.0)                       # the Uno resets when the port opens
        print("talking to the Uno on", port)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        sys.exit("Camera not available. Allow camera access in System Settings > Privacy & Security.")
    mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=False,
                                           min_detection_confidence=0.5, min_tracking_confidence=0.5)
    rest = None
    calib_until, calib = time.time() + 2.0, []
    on, since = False, time.time()            # motor state, and when the raw smile reading last flipped
    raw_prev = False
    forced_until, last_send, last_log = 0.0, 0.0, 0.0
    print("calibrating: relaxed face, no smile, for 2 seconds...")

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)
        res = mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        r = smile_ratio(res.multi_face_landmarks[0].landmark) if res.multi_face_landmarks else None

        now = time.time()
        if now < calib_until:
            if r is not None:
                calib.append(r)
        elif calib_until > 0:
            if len(calib) >= 5:
                rest = float(np.median(calib))
                calib_until, calib = 0.0, []
                print("calibrated: relaxed mouth/face ratio {:.3f}".format(rest), flush=True)
            else:                                 # saw no face: keep trying instead of giving up silently
                calib_until, calib = now + 2.0, []
                print("calibration saw no face - trying again (face the camera)", flush=True)

        if now - last_log > 0.5:
            last_log = now
            print("face {}  ratio {}  rest {}".format(
                "yes" if r is not None else "NO ", "{:.3f}".format(r) if r is not None else "-",
                "{:.3f}".format(rest) if rest else "-"), flush=True)

        widen = 0.0 if (r is None or rest is None) else r / rest - 1.0
        raw = widen > (SMILE_OFF if on else SMILE_ON)   # hysteresis
        if raw != raw_prev:
            raw_prev, since = raw, now
        if raw and not on and now - since >= HOLD_ON:
            on = True
        elif not raw and on and now - since >= HOLD_OFF:
            on = False
        motor = on or now < forced_until

        if link and now - last_send > 1.0 / SEND_HZ:
            link.write(b"S100\n" if motor else b"S0\n")
            last_send = now

        h, wd = frame.shape[:2]
        colour = (80, 200, 80) if motor else (80, 80, 230)
        cv2.rectangle(frame, (0, 0), (wd - 1, h - 1), colour, 12)
        if now < calib_until:
            txt = "calibrating: relaxed face..."
        elif r is None:
            txt = "no face -> OFF"
        else:
            txt = "{}   smile {:+.0%}  (on at {:+.0%}){}".format(
                "SPINNING" if motor else "off", widen, SMILE_ON, "  [SPACE]" if now < forced_until else "")
        cv2.putText(frame, txt, (24, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
        cv2.imshow("Dragon: smile to spin it (q quits, c recalibrates)", frame)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        if k == 32:
            forced_until = time.time() + 3.0
        if k == ord("c"):
            calib_until, calib = time.time() + 2.0, []
            print("calibrating: relaxed face, no smile, for 2 seconds...")

    if link:
        link.write(b"S0\n")
        link.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
