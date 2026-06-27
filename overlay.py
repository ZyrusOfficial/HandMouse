"""
AirMouse — Overlay HUD
Draws an Iron Man-inspired heads-up display on the camera feed.
"""

import cv2
import time
from gesture_recognizer import Gesture
import config


class OverlayHUD:
    """
    Renders a styled overlay on top of the camera feed showing:
    - Current gesture label
    - FPS counter
    - Finger state indicators
    - Status badges (drag mode, tracking active, etc.)
    """

    # Gesture display names and icons
    GESTURE_LABELS = {
        Gesture.NONE:        ("NO HAND",     (100, 100, 100)),
        Gesture.IDLE:        ("IDLE",         (200, 200, 200)),
        Gesture.POINT:       ("MOVE",         config.COLOR_GREEN),
        Gesture.PINCH:       ("CLICK",        config.COLOR_ORANGE),
        Gesture.RIGHT_CLICK: ("RIGHT CLICK",  (255, 100, 255)),
        Gesture.FIST:        ("DRAG",         config.COLOR_RED),
        Gesture.SCROLL:      ("SCROLL",       config.COLOR_CYAN),
    }

    def __init__(self):
        self._fps_history = []
        self._prev_time = time.time()

    def draw(self, frame, gesture: Gesture, landmarks=None,
             is_dragging: bool = False, is_paused: bool = False):
        """
        Draw the full HUD overlay on the frame.

        Args:
            frame: BGR image to draw on (modified in-place)
            gesture: Current detected gesture
            landmarks: Hand landmarks (for finger state display)
            is_dragging: Whether drag mode is active
            is_paused: Whether tracking is paused
        """
        h, w = frame.shape[:2]

        # ── FPS Counter ──
        self._draw_fps(frame)

        # ── Top-left: Gesture label panel ──
        self._draw_gesture_panel(frame, gesture, w)

        # ── Status badges ──
        badge_y = 90
        if is_dragging:
            self._draw_badge(frame, "DRAGGING", config.COLOR_RED, 15, badge_y)
            badge_y += 35
        if is_paused:
            self._draw_badge(frame, "PAUSED", (0, 140, 255), 15, badge_y)
            badge_y += 35

        # ── Bottom: Finger state indicators ──
        if landmarks is not None:
            self._draw_finger_states(frame, landmarks, w, h)

        # ── Corner accents (Iron Man HUD style) ──
        self._draw_hud_accents(frame, w, h)

        # ── Crosshair on index fingertip ──
        if landmarks is not None and gesture in (Gesture.POINT, Gesture.PINCH):
            self._draw_crosshair(frame, landmarks, w, h)

    def _draw_fps(self, frame):
        """Draw FPS counter in the top-right corner."""
        now = time.time()
        dt = now - self._prev_time
        self._prev_time = now
        if dt > 0:
            fps = 1.0 / dt
            self._fps_history.append(fps)
            if len(self._fps_history) > 30:
                self._fps_history.pop(0)

        avg_fps = sum(self._fps_history) / max(len(self._fps_history), 1)
        h, w = frame.shape[:2]

        fps_text = f"FPS: {int(avg_fps)}"
        (tw, th), _ = cv2.getTextSize(fps_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        x = w - tw - 15
        y = 30

        # Background
        cv2.rectangle(frame, (x - 8, y - th - 8), (x + tw + 8, y + 8),
                      config.COLOR_HUD_BG, -1)
        cv2.rectangle(frame, (x - 8, y - th - 8), (x + tw + 8, y + 8),
                      config.COLOR_FPS, 1)
        cv2.putText(frame, fps_text, (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, config.COLOR_FPS, 2)

    def _draw_gesture_panel(self, frame, gesture: Gesture, frame_w: int):
        """Draw the current gesture label in a styled panel."""
        label, color = self.GESTURE_LABELS.get(gesture, ("UNKNOWN", (255, 255, 255)))

        # Panel background
        panel_w = 250
        panel_h = 55
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (10 + panel_w, 10 + panel_h),
                      config.COLOR_HUD_BG, -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Border
        cv2.rectangle(frame, (10, 10), (10 + panel_w, 10 + panel_h), color, 2)

        # Gesture text
        cv2.putText(frame, label, (22, 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2, cv2.LINE_AA)

        # Small label
        cv2.putText(frame, "GESTURE", (22, 26),
                    cv2.FONT_HERSHEY_PLAIN, 0.9, config.COLOR_HUD_TEXT, 1)

    def _draw_badge(self, frame, text: str, color: tuple, x: int, y: int):
        """Draw a small status badge."""
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x, y - th - 6), (x + tw + 16, y + 6), color, -1)
        cv2.putText(frame, text, (x + 8, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

    def _draw_finger_states(self, frame, landmarks, w: int, h: int):
        """Draw finger up/down indicators at the bottom of the frame."""
        import math
        lm = landmarks  # Tasks API returns a direct list

        # Use rotation-invariant detection (same logic as gesture_recognizer)
        wrist = lm[0]
        mid_mcp = lm[9]
        axis_x = mid_mcp.x - wrist.x
        axis_y = mid_mcp.y - wrist.y
        axis_len = math.sqrt(axis_x * axis_x + axis_y * axis_y)

        if axis_len < 1e-6:
            # Fallback to Y-axis
            fingers = [
                ("THM", lm[4].x < lm[3].x),
                ("IDX", lm[8].y < lm[6].y),
                ("MID", lm[12].y < lm[10].y),
                ("RNG", lm[16].y < lm[14].y),
                ("PNK", lm[20].y < lm[18].y),
            ]
        else:
            ax = axis_x / axis_len
            ay = axis_y / axis_len
            px, py = -ay, ax  # perpendicular for thumb

            def proj(pt):
                return (pt.x - wrist.x) * ax + (pt.y - wrist.y) * ay
            def proj_perp(pt):
                return (pt.x - wrist.x) * px + (pt.y - wrist.y) * py

            fingers = [
                ("THM", abs(proj_perp(lm[4])) > abs(proj_perp(lm[3])) + 0.01),
                ("IDX", proj(lm[8]) > proj(lm[6])),
                ("MID", proj(lm[12]) > proj(lm[10])),
                ("RNG", proj(lm[16]) > proj(lm[14])),
                ("PNK", proj(lm[20]) > proj(lm[18])),
            ]

        bar_y = h - 40
        start_x = w // 2 - 120

        for i, (name, is_up) in enumerate(fingers):
            x = start_x + i * 55
            color = config.COLOR_GREEN if is_up else config.COLOR_RED
            # Circle indicator
            cv2.circle(frame, (x + 12, bar_y), 8, color, -1)
            cv2.circle(frame, (x + 12, bar_y), 8, (255, 255, 255), 1)
            # Label
            cv2.putText(frame, name, (x, bar_y + 25),
                        cv2.FONT_HERSHEY_PLAIN, 0.9, config.COLOR_HUD_TEXT, 1)

    def _draw_hud_accents(self, frame, w: int, h: int):
        """Draw corner brackets for that Iron Man HUD feel."""
        accent_len = 30
        color = config.COLOR_CYAN
        thickness = 1

        # Top-left
        cv2.line(frame, (5, 5), (5 + accent_len, 5), color, thickness)
        cv2.line(frame, (5, 5), (5, 5 + accent_len), color, thickness)

        # Top-right
        cv2.line(frame, (w - 5, 5), (w - 5 - accent_len, 5), color, thickness)
        cv2.line(frame, (w - 5, 5), (w - 5, 5 + accent_len), color, thickness)

        # Bottom-left
        cv2.line(frame, (5, h - 5), (5 + accent_len, h - 5), color, thickness)
        cv2.line(frame, (5, h - 5), (5, h - 5 - accent_len), color, thickness)

        # Bottom-right
        cv2.line(frame, (w - 5, h - 5), (w - 5 - accent_len, h - 5), color, thickness)
        cv2.line(frame, (w - 5, h - 5), (w - 5, h - 5 - accent_len), color, thickness)

    def _draw_crosshair(self, frame, landmarks, w: int, h: int):
        """Draw a crosshair on the index fingertip."""
        lm = landmarks  # Tasks API returns a direct list
        ix = int(lm[8].x * w)
        iy = int(lm[8].y * h)
        size = 15
        color = config.COLOR_ORANGE

        cv2.line(frame, (ix - size, iy), (ix + size, iy), color, 1, cv2.LINE_AA)
        cv2.line(frame, (ix, iy - size), (ix, iy + size), color, 1, cv2.LINE_AA)
        cv2.circle(frame, (ix, iy), size // 2, color, 1, cv2.LINE_AA)
