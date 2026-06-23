"""
run_webcam.py
-------------
Standalone script – no browser needed.
Opens your laptop webcam and shows the annotated feed in a CV2 window.

Usage:
  python run_webcam.py
  python run_webcam.py --exercise squat
  python run_webcam.py --exercise bicep_curl --camera 1

Keys:
  q      – quit
  r      – reset rep counter
  1-8    – switch exercise (see list on screen)
  SPACE  – pause / resume
"""

import cv2
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from models.blazepose_processor import GymPoseProcessor
from exercises.exercise_db      import list_exercises

EXERCISE_KEYS = list(list_exercises().keys())
KEY_MAP = {ord(str(i+1)): k for i, k in enumerate(EXERCISE_KEYS[:9])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exercise", default="bicep_curl",
                        choices=EXERCISE_KEYS)
    parser.add_argument("--camera",   type=int, default=0)
    parser.add_argument("--width",    type=int, default=1280)
    parser.add_argument("--height",   type=int, default=720)
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS,          30)

    if not cap.isOpened():
        print(f"ERROR: Cannot open camera {args.camera}")
        sys.exit(1)

    processor = GymPoseProcessor(exercise_key=args.exercise, model_complexity=1)
    paused    = False

    print("\n=== Smart Gym Assistant (Webcam Mode) ===")
    for i, (k, v) in enumerate(list_exercises().items(), 1):
        print(f"  [{i}] {v}")
    print("  [r] Reset reps  [SPACE] Pause  [q] Quit\n")

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)
            annotated, feedback = processor.process_frame(frame)
        
        cv2.imshow("Smart Gym Assistant – press Q to quit", annotated)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            processor.reset_reps()
            print("Reps reset!")
        elif key == ord(' '):
            paused = not paused
            print("PAUSED" if paused else "RESUMED")
        elif key in KEY_MAP:
            ex = KEY_MAP[key]
            processor.change_exercise(ex)
            print(f"Exercise → {ex}")

    # Session summary
    stats = processor.session_stats()
    if stats:
        print("\n=== Session Summary ===")
        for k, v in stats.items():
            print(f"  {k}: {v}")

    cap.release()
    cv2.destroyAllWindows()
    processor.close()


if __name__ == "__main__":
    main()
