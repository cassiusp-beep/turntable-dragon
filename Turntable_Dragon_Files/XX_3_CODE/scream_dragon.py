"""Scream detector for the dragon automaton (Mac).

The webcam watches your face: the wider your mouth opens, the higher the "anguish". The microphone adds to it:
louder = more anguish. The score (0-100) goes to the Uno over USB, and the dragon moves faster the more you scream.

Setup (Terminal, once):
    python3 -m pip install opencv-python mediapipe pyserial sounddevice numpy
Run:
    python3 scream_dragon.py            # finds the Uno automatically
    python3 scream_dragon.py --no-serial  # test the camera/mic without the Uno plugged in
The first run, macOS asks for camera and microphone access for Terminal: allow both.
Keys in the window: q = quit, c = calibrate (look calm and stay quiet for 2 seconds),
SPACE = backup scream button (full speed for 3 seconds; tap again to keep it going).
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
    sys.exit("mediapipe is missing: python3 -m pip install mediapipe")

try:
    import serial
except ImportError:
    serial = None

try:
    import sounddevice as sd
except Exception:
    sd = None

# ---- tuning ----
MOUTH_WEIGHT = 0.65        # how much the open mouth counts (the rest is loudness)
MOUTH_FULL = 0.55          # mouth-open ratio that counts as a full scream (lip gap / mouth width)
LOUD_FULL_DB = 25.0        # dB above your quiet room that counts as a full scream
SMOOTH = 0.25              # 0..1, lower = smoother but slower to react
SEND_HZ = 15


def find_uno():
    ports = sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.wchusbserial*"))
    return ports[0] if ports else None


class Mic:
    """running loudness in dB (relative to full scale) from the default microphone"""

    def __init__(self):
        self.db = -90.0
        self.stream = None
        if sd is None:
            print("sounddevice missing: running on the camera only")
            return
        try:
            self.stream = sd.InputStream(channels=1, samplerate=16000, blocksize=800, callback=self._cb)
            self.stream.start()
        except Exception as e:
            print("microphone unavailable ({}): running on the camera only".format(e))
            self.stream = None

    def _cb(self, data, frames, t, status):
        rms = float(np.sqrt(np.mean(np.square(data)))) + 1e-9
        self.db = 20.0 * math.log10(rms)


def mouth_ratio(lm):
    """vertical lip gap / mouth width, from MediaPipe face-mesh landmarks (13/14 inner lips, 61/291 corners)"""
    gap = math.dist((lm[13].x, lm[13].y), (lm[14].x, lm[14].y))
    width = math.dist((lm[61].x, lm[61].y), (lm[291].x, lm[291].y)) + 1e-6
    return gap / width


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", help="serial port of the Uno (default: auto)")
    ap.add_argument("--no-serial", action="store_true", help="don't talk to the Uno")
    ap.add_argument("--camera", type=int, default=0)
    args = ap.parse_args()

    link = None
    if not args.no_serial:
        if serial is None:
            sys.exit("pyserial is missing: python3 -m pip install pyserial")
        port = args.port or find_uno()
        if not port:
            sys.exit("No Uno found. Plug in the USB cable, or run with --no-serial to test.")
        link = serial.Serial(port, 115200, timeout=0)
        time.sleep(2.0)                       # the Uno resets when the port opens
        print("talking to the Uno on", port)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        sys.exit("Camera not available. Allow camera access for Terminal in System Settings > Privacy & Security.")
    mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=False,
                                           min_detection_confidence=0.5, min_tracking_confidence=0.5)
    mic = Mic()
    mouth_rest, quiet_db = 0.05, -60.0
    score, last_send = 0.0, 0.0
    calib_until, calib_m, calib_db = time.time() + 2.0, [], []
    forced_until = 0.0                    # space bar: backup scream
    print("calibrating: look calm and stay quiet for 2 seconds...")

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)
        res = mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        m = mouth_ratio(res.multi_face_landmarks[0].landmark) if res.multi_face_landmarks else None

        now = time.time()
        if now < calib_until:
            if m is not None:
                calib_m.append(m)
            calib_db.append(mic.db)
        elif calib_m or calib_db:
            if calib_m:
                mouth_rest = float(np.median(calib_m))
            if calib_db:
                quiet_db = float(np.median(calib_db))
            calib_m, calib_db = [], []
            print("calibrated: mouth at rest {:.2f}, room {:.0f} dB".format(mouth_rest, quiet_db))

        mouth = 0.0 if m is None else np.clip((m - mouth_rest) / max(1e-3, MOUTH_FULL - mouth_rest), 0, 1)
        loud = np.clip((mic.db - quiet_db) / LOUD_FULL_DB, 0, 1) if mic.stream else 0.0
        w = MOUTH_WEIGHT if mic.stream else 1.0
        raw = w * mouth + (1 - w) * loud
        if m is not None and mic.stream and mouth > 0.6 and loud > 0.6:
            raw = min(1.0, raw * 1.25)        # open mouth AND loud = a real scream: boost it
        if now < forced_until:
            raw = 1.0
        score += SMOOTH * (raw - score)
        pct = int(round(score * 100))

        if link and now - last_send > 1.0 / SEND_HZ:
            link.write("S{}\n".format(pct).encode())
            last_send = now

        h, wd = frame.shape[:2]
        cv2.rectangle(frame, (20, h - 40), (20 + int((wd - 40) * score), h - 20), (60, 60, 230), -1)
        cv2.rectangle(frame, (20, h - 40), (wd - 20, h - 20), (230, 230, 230), 2)
        txt = "calibrating..." if now < calib_until else "anguish {}%  mouth {:.0%}  loud {:.0%}{}".format(
            pct, mouth, loud, "  [SPACE]" if now < forced_until else "")
        cv2.putText(frame, txt, (20, h - 52), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        if m is None and now >= calib_until:
            cv2.putText(frame, "no face", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (80, 80, 255), 2)
        cv2.imshow("Dragon: scream to wake it (q quits, c recalibrates)", frame)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        if k == 32:
            forced_until = time.time() + 3.0
        if k == ord("c"):
            calib_until = time.time() + 2.0
            print("calibrating: look calm and stay quiet for 2 seconds...")

    if link:
        link.write(b"S0\n")
        link.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
