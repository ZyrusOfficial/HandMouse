"""
AirMouse — Hand Tracker
Uses MediaPipe Tasks API (HandLandmarker) for hand landmark detection.
Auto-downloads the model file on first run.
"""

import os
import urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
import config

# Model download URL and local path
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")

# Hand connection pairs for drawing skeleton
# (matches the old mp.solutions.hands.HAND_CONNECTIONS)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),       # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),       # Index
    (0, 9), (9, 10), (10, 11), (11, 12),   # Middle  (wrist→MCP)
    (0, 13), (13, 14), (14, 15), (15, 16), # Ring    (wrist→MCP)
    (0, 17), (17, 18), (18, 19), (19, 20), # Pinky   (wrist→MCP)
    (5, 9), (9, 13), (13, 17),             # Palm connections
]


def _ensure_model():
    """Download the hand_landmarker.task model if it doesn't exist."""
    if not os.path.exists(MODEL_PATH):
        print(f"[INFO] Downloading hand landmarker model...")
        print(f"       → {MODEL_URL}")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print(f"[INFO] Model saved to {MODEL_PATH}")


class HandTracker:
    """
    Detects hand landmarks from webcam frames using MediaPipe HandLandmarker
    (Tasks API). Returns normalized (x, y, z) for all 21 landmarks.

    Uses VIDEO running mode for synchronous frame-by-frame processing.
    """

    # Landmark indices for quick reference
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_MCP = 5
    INDEX_PIP = 6
    INDEX_DIP = 7
    INDEX_TIP = 8
    MIDDLE_MCP = 9
    MIDDLE_PIP = 10
    MIDDLE_DIP = 11
    MIDDLE_TIP = 12
    RING_MCP = 13
    RING_PIP = 14
    RING_DIP = 15
    RING_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20

    def __init__(self):
        _ensure_model()

        base_options = mp_python.BaseOptions(
            model_asset_path=MODEL_PATH
        )
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=config.MP_MAX_HANDS,
            min_hand_detection_confidence=config.MP_DETECTION_CONFIDENCE,
            min_hand_presence_confidence=config.MP_TRACKING_CONFIDENCE,
            min_tracking_confidence=config.MP_TRACKING_CONFIDENCE,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._frame_timestamp_ms = 0

    def detect(self, frame):
        """
        Detect hand landmarks in a BGR frame.

        Args:
            frame: BGR image from OpenCV (numpy array)

        Returns:
            List of hand landmark lists. Each hand contains a list of
            NormalizedLandmark objects with .x, .y, .z (0–1 range).
            Returns empty list if no hands detected.
        """
        # Convert BGR → RGB for MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # Increment timestamp (must be monotonically increasing)
        self._frame_timestamp_ms += 33  # ~30 FPS
        result = self._landmarker.detect_for_video(mp_image, self._frame_timestamp_ms)

        if result.hand_landmarks:
            return result.hand_landmarks
        return []

    def draw_landmarks(self, frame, hand_landmarks):
        """
        Draw hand skeleton on the frame using OpenCV.

        Args:
            frame: BGR image to draw on (modified in-place)
            hand_landmarks: A single hand's landmark list from detect()
                           (list of NormalizedLandmark with .x, .y, .z)
        """
        h, w = frame.shape[:2]

        # Draw connections
        for start_idx, end_idx in HAND_CONNECTIONS:
            start = hand_landmarks[start_idx]
            end = hand_landmarks[end_idx]
            x1, y1 = int(start.x * w), int(start.y * h)
            x2, y2 = int(end.x * w), int(end.y * h)
            cv2.line(frame, (x1, y1), (x2, y2), config.COLOR_CYAN, 2, cv2.LINE_AA)

        # Draw landmark points
        for i, lm in enumerate(hand_landmarks):
            x, y = int(lm.x * w), int(lm.y * h)
            # Fingertips get a larger, orange circle
            if i in (4, 8, 12, 16, 20):
                cv2.circle(frame, (x, y), 6, config.COLOR_ORANGE, -1, cv2.LINE_AA)
                cv2.circle(frame, (x, y), 6, (255, 255, 255), 1, cv2.LINE_AA)
            else:
                cv2.circle(frame, (x, y), 3, config.COLOR_CYAN, -1, cv2.LINE_AA)

    def close(self):
        """Release MediaPipe resources."""
        self._landmarker.close()
