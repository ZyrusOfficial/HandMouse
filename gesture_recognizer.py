"""
AirMouse — Gesture Recognizer
Classifies hand gestures from MediaPipe landmarks using pure geometry.
No ML — just distances and finger-up/down checks.

Uses rotation-invariant finger detection so gestures work at any hand angle.
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
    - Rotation-invariant finger extension detection (wrist→MCP axis projection)
    - Euclidean distances between thumb/index/middle tips for pinch detection
    - Gesture stabilization with hysteresis to prevent flickering
    """

    # Finger definitions: (tip_index, pip_index, mcp_index)
    THUMB = (4, 3, 2)
    INDEX = (8, 6, 5)
    MIDDLE = (12, 10, 9)
    RING = (16, 14, 13)
    PINKY = (20, 18, 17)

    def __init__(self, stability_frames: int = None):
        """
        Args:
            stability_frames: Number of consecutive frames a gesture must
                              be detected before it's confirmed (prevents flicker).
                              Defaults to config.GESTURE_STABILITY_FRAMES.
        """
        if stability_frames is None:
            stability_frames = config.GESTURE_STABILITY_FRAMES

        self._stability_frames = stability_frames
        self._exit_frames = config.GESTURE_EXIT_FRAMES
        self._history = deque(maxlen=stability_frames)
        self._current_gesture = Gesture.NONE
        self._prev_index_y = None  # For scroll delta tracking
        self._exit_counter = 0     # Hysteresis: counts frames of different gesture

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
            self._exit_counter = 0
            return Gesture.NONE

        lm = landmarks  # Tasks API returns a direct list
        self._scroll_dy = 0.0

        # Get finger states (rotation-invariant)
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

        # SCROLL: index + middle up, ring down (relaxed — pinky doesn't matter)
        elif index_up and middle_up and not ring_up:
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

        # ── Stabilization with hysteresis ──
        # Once a gesture is active, it's "sticky" — requires EXIT_FRAMES of
        # a different gesture before we allow switching. This prevents the
        # rapid flickering that causes cursor jumps.
        self._history.append(raw_gesture)

        if self._current_gesture == Gesture.NONE:
            # No active gesture — use standard confirmation
            if len(self._history) == self._history.maxlen:
                if all(g == self._history[0] for g in self._history):
                    self._current_gesture = self._history[0]
                    self._exit_counter = 0
        else:
            # Active gesture — apply hysteresis
            if raw_gesture != self._current_gesture:
                self._exit_counter += 1
                if self._exit_counter >= self._exit_frames:
                    # Enough frames of different gesture — check if new one is stable
                    if len(self._history) >= self._exit_frames:
                        recent = list(self._history)[-self._exit_frames:]
                        if all(g == recent[0] for g in recent):
                            self._current_gesture = recent[0]
                            self._exit_counter = 0
            else:
                # Same gesture as current — reset exit counter
                self._exit_counter = 0

        return self._current_gesture

    def _get_fingers_up(self, lm) -> tuple[bool, bool, bool, bool, bool]:
        """
        Determine which fingers are extended (up) using rotation-invariant
        projection along the hand's own axis.

        Instead of comparing raw Y-coordinates (which breaks when the hand
        rotates), we project finger positions onto the hand's natural
        "up" direction: from wrist (lm[0]) toward middle-finger MCP (lm[9]).

        Returns:
            Tuple of (thumb, index, middle, ring, pinky) booleans
        """
        # ── Compute hand axis: wrist → middle MCP ──
        # This is the "up" direction of the hand regardless of orientation
        wrist = lm[0]
        mid_mcp = lm[9]

        axis_x = mid_mcp.x - wrist.x
        axis_y = mid_mcp.y - wrist.y
        axis_len = math.sqrt(axis_x * axis_x + axis_y * axis_y)

        if axis_len < 1e-6:
            # Degenerate case — hand is basically a dot, fall back to Y-axis
            return self._get_fingers_up_fallback(lm)

        # Normalize the axis
        axis_x /= axis_len
        axis_y /= axis_len

        # Perpendicular axis (for thumb which bends sideways)
        perp_x = -axis_y
        perp_y = axis_x

        # ── Thumb: uses perpendicular axis ──
        # Project thumb tip and thumb IP onto the perpendicular direction
        # relative to wrist. Thumb is "up" if tip is further along perp than IP.
        thumb_tip_proj = self._project_onto(lm[4], wrist, perp_x, perp_y)
        thumb_ip_proj = self._project_onto(lm[3], wrist, perp_x, perp_y)
        # Use absolute difference — thumb can stick out either side
        thumb_up = abs(thumb_tip_proj) > abs(thumb_ip_proj) + 0.01

        # ── Other fingers: project tip and PIP onto the hand axis ──
        # A finger is "up" (extended) if its tip is further along the hand
        # axis than its PIP joint
        index_up = self._project_onto(lm[8], wrist, axis_x, axis_y) > \
                   self._project_onto(lm[6], wrist, axis_x, axis_y)
        middle_up = self._project_onto(lm[12], wrist, axis_x, axis_y) > \
                    self._project_onto(lm[10], wrist, axis_x, axis_y)
        ring_up = self._project_onto(lm[16], wrist, axis_x, axis_y) > \
                  self._project_onto(lm[14], wrist, axis_x, axis_y)
        pinky_up = self._project_onto(lm[20], wrist, axis_x, axis_y) > \
                   self._project_onto(lm[18], wrist, axis_x, axis_y)

        return (thumb_up, index_up, middle_up, ring_up, pinky_up)

    def _get_fingers_up_fallback(self, lm) -> tuple[bool, bool, bool, bool, bool]:
        """Fallback finger detection using raw Y-axis (for degenerate cases)."""
        thumb_up = lm[4].x < lm[3].x
        index_up = lm[8].y < lm[6].y
        middle_up = lm[12].y < lm[10].y
        ring_up = lm[16].y < lm[14].y
        pinky_up = lm[20].y < lm[18].y
        return (thumb_up, index_up, middle_up, ring_up, pinky_up)

    @staticmethod
    def _project_onto(point, origin, axis_x: float, axis_y: float) -> float:
        """
        Project a landmark onto a direction axis relative to an origin point.

        Returns the scalar projection (signed distance along the axis).
        """
        dx = point.x - origin.x
        dy = point.y - origin.y
        return dx * axis_x + dy * axis_y

    @staticmethod
    def _distance(point_a, point_b) -> float:
        """Euclidean distance between two landmarks (2D, ignoring z)."""
        dx = point_a.x - point_b.x
        dy = point_a.y - point_b.y
        return math.sqrt(dx * dx + dy * dy)
