"""
AirMouse — Gesture Recognizer
Classifies hand gestures from MediaPipe landmarks using pure geometry.
No ML — just distances and finger-up/down checks.
"""

import math
from enum import Enum, auto
from collections import deque

import config


class Gesture(Enum):
    """All recognized gestures."""
    NONE = auto()       # No hand detected
    IDLE = auto()       # Open palm — cursor paused
    POINT = auto()      # Index finger pointing — move cursor
    PINCH = auto()      # Thumb + index pinch — left click
    RIGHT_CLICK = auto()  # Thumb + middle pinch — right click
    FIST = auto()       # All fingers curled — drag
    SCROLL = auto()     # Index + middle up — scroll mode


class GestureRecognizer:
    """
    Classifies hand gestures from a set of 21 MediaPipe landmarks.

    Uses:
    - Finger tip vs. MCP (knuckle) Y-positions to detect "finger up"
    - Euclidean distances between thumb/index/middle tips for pinch detection
    - Gesture stabilization buffer to prevent flickering
    """

    # Finger definitions: (tip_index, pip_index, mcp_index)
    THUMB = (4, 3, 2)
    INDEX = (8, 6, 5)
    MIDDLE = (12, 10, 9)
    RING = (16, 14, 13)
    PINKY = (20, 18, 17)

    def __init__(self, stability_frames: int = 3):
        """
        Args:
            stability_frames: Number of consecutive frames a gesture must
                              be detected before it's confirmed (prevents flicker)
        """
        self._history = deque(maxlen=stability_frames)
        self._current_gesture = Gesture.NONE
        self._prev_index_y = None  # For scroll delta tracking

    @property
    def scroll_delta(self) -> float:
        """Y-delta of index finger since last frame (for scroll gesture)."""
        return self._scroll_dy

    def classify(self, landmarks) -> Gesture:
        """
        Classify the current gesture from hand landmarks.

        Args:
            landmarks: List of NormalizedLandmark objects from MediaPipe Tasks API

        Returns:
            Stabilized Gesture enum value
        """
        if landmarks is None:
            self._history.clear()
            self._current_gesture = Gesture.NONE
            self._prev_index_y = None
            return Gesture.NONE

        lm = landmarks  # Tasks API returns a direct list
        self._scroll_dy = 0.0

        # Get finger states
        fingers_up = self._get_fingers_up(lm)
        thumb_up, index_up, middle_up, ring_up, pinky_up = fingers_up

        # Calculate key distances
        thumb_index_dist = self._distance(lm[4], lm[8])
        thumb_middle_dist = self._distance(lm[4], lm[12])

        # ── Gesture classification (order matters — most specific first) ──

        raw_gesture = Gesture.IDLE  # Default fallback

        # PINCH: thumb and index tips close together
        if thumb_index_dist < config.PINCH_THRESHOLD:
            raw_gesture = Gesture.PINCH

        # RIGHT CLICK: thumb and middle tips close, index still up
        elif thumb_middle_dist < config.RIGHT_CLICK_THRESHOLD and index_up:
            raw_gesture = Gesture.RIGHT_CLICK

        # FIST: all fingers curled down
        elif not any(fingers_up):
            raw_gesture = Gesture.FIST

        # SCROLL: index + middle up, ring + pinky down
        elif index_up and middle_up and not ring_up and not pinky_up:
            raw_gesture = Gesture.SCROLL
            # Track vertical movement for scroll direction
            index_y = lm[8].y
            if self._prev_index_y is not None:
                self._scroll_dy = index_y - self._prev_index_y
            self._prev_index_y = index_y

        # POINT: only index finger up
        elif index_up and not middle_up and not ring_up and not pinky_up:
            raw_gesture = Gesture.POINT

        # IDLE: open palm (multiple fingers up, no pinch)
        else:
            raw_gesture = Gesture.IDLE

        # Reset scroll tracking when not in scroll mode
        if raw_gesture != Gesture.SCROLL:
            self._prev_index_y = None

        # ── Stabilization: require N consecutive same-gesture frames ──
        self._history.append(raw_gesture)

        if len(self._history) == self._history.maxlen:
            if all(g == self._history[0] for g in self._history):
                self._current_gesture = self._history[0]

        return self._current_gesture

    def _get_fingers_up(self, lm) -> tuple[bool, bool, bool, bool, bool]:
        """
        Determine which fingers are extended (up).

        For thumb: compare tip.x vs IP.x (thumb bends sideways).
        For other fingers: compare tip.y vs PIP.y (lower y = higher on screen).

        Returns:
            Tuple of (thumb, index, middle, ring, pinky) booleans
        """
        # Thumb: special case — compare X positions
        # (works for right hand; thumb tip should be further from palm center)
        thumb_up = lm[4].x < lm[3].x  # For right hand in mirrored view

        # Other fingers: tip.y < pip.y means finger is extended
        # (In normalized coords, y=0 is top of frame)
        index_up = lm[8].y < lm[6].y
        middle_up = lm[12].y < lm[10].y
        ring_up = lm[16].y < lm[14].y
        pinky_up = lm[20].y < lm[18].y

        return (thumb_up, index_up, middle_up, ring_up, pinky_up)

    @staticmethod
    def _distance(point_a, point_b) -> float:
        """Euclidean distance between two landmarks (2D, ignoring z)."""
        dx = point_a.x - point_b.x
        dy = point_a.y - point_b.y
        return math.sqrt(dx * dx + dy * dy)
