"""
AirMouse — Main Entry Point
Iron Man-style air mouse using webcam hand tracking.

Usage:
    python main.py

Controls:
    q — Quit
    p — Pause/Resume tracking
    Move mouse to top-left corner (0,0) — Emergency stop (PyAutoGUI failsafe)
"""

import sys
import cv2
import time

from hand_tracker import HandTracker
from gesture_recognizer import GestureRecognizer, Gesture
from mouse_controller import MouseController
from overlay import OverlayHUD
from camera_picker import pick_camera
import config

import os
# Suppress MediaPipe clearcut/glog spam
os.environ['GLOG_minloglevel'] = '2'

def main():
    print("=" * 55)
    print("  AirMouse — Iron Man Gesture Control")
    print("=" * 55)
    print()
    print("  Starting webcam...")
    print("  Controls:")
    print("    q  — Quit")
    print("    p  — Pause / Resume tracking")
    print("    Emergency: move mouse to screen corner (0,0)")
    print()

    # ── Camera Selection GUI ──
    print("  Launching camera picker GUI...")
    cam_info = pick_camera()
    
    if cam_info is None:
        print("\n[INFO] Camera selection cancelled. Exiting.")
        sys.exit(0)
        
    idx, backend = cam_info
    print(f"  [SUCCESS] Selected Camera {idx}")
    
    # ── Initialize components ──
    cap = cv2.VideoCapture(idx, backend)
    
    if not cap.isOpened():
        print("[ERROR] Could not open selected webcam.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

    tracker = HandTracker()
    recognizer = GestureRecognizer()
    mouse = MouseController()
    hud = OverlayHUD()

    is_paused = False
    gesture = Gesture.NONE

    print(f"  Camera opened: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
          f"{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    print(f"  Screen size:   {mouse._screen_w}x{mouse._screen_h}")
    print()
    print("  Show your hand to begin! ✋")
    print("-" * 55)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[WARN] Frame capture failed, retrying...")
                time.sleep(0.01)
                continue

            # Mirror the frame horizontally for intuitive control
            frame = cv2.flip(frame, 1)

            hand_landmarks = None

            if not is_paused:
                # ── Detect hands ──
                hands = tracker.detect(frame)

                if hands:
                    hand_lm = hands[0]  # Use first detected hand

                    # Draw hand skeleton
                    tracker.draw_landmarks(frame, hand_lm)

                    # ── Classify gesture ──
                    gesture = recognizer.classify(hand_lm)

                    # ── Execute mouse action ──
                    mouse.execute(gesture, hand_lm, recognizer.scroll_delta)

                    hand_landmarks = hand_lm
                else:
                    gesture = recognizer.classify(None)

            # ── Draw HUD overlay ──
            if config.SHOW_OVERLAY:
                hud.draw(
                    frame,
                    gesture=gesture,
                    landmarks=hand_landmarks,
                    is_dragging=mouse.is_dragging,
                    is_paused=is_paused,
                )
                cv2.imshow(config.OVERLAY_WINDOW_NAME, frame)

            # ── Handle keyboard input ──
            key = cv2.waitKey(1) & 0xFF

            if key == config.KEY_QUIT:
                print("\n[INFO] Quitting AirMouse...")
                break
            elif key == config.KEY_PAUSE:
                is_paused = not is_paused
                state = "PAUSED" if is_paused else "RESUMED"
                print(f"[INFO] Tracking {state}")

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
    except pyautogui.FailSafeException:
        print("\n[SAFETY] Mouse moved to corner — emergency stop triggered!")
    finally:
        # ── Cleanup ──
        cap.release()
        tracker.close()
        cv2.destroyAllWindows()
        print("[INFO] AirMouse shut down cleanly.")


if __name__ == "__main__":
    # Import pyautogui here to check for FailSafeException
    import pyautogui
    main()
