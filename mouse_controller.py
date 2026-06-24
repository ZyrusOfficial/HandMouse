"""
AirMouse — Mouse Controller
Translates recognized gestures into actual Windows mouse events.
"""

import time
import pyautogui
from gesture_recognizer import Gesture
from smoother import CursorSmoother
import config


# Disable PyAutoGUI's pause between actions for responsiveness
pyautogui.PAUSE = 0
# Keep failsafe: moving mouse to (0, 0) will raise exception and stop
pyautogui.FAILSAFE = True


class MouseController:
    """
    Maps gesture classifications and hand landmark positions to mouse actions.

    Handles:
    - Cursor movement with adaptive smoothing
    - Left click, right click with debounce
    - Click-and-drag mode
    - Scroll with Y-delta tracking
    """

    def __init__(self):
        self._screen_w, self._screen_h = pyautogui.size()
        self._smoother = CursorSmoother()

        # Debounce state
        self._last_click_time = 0.0
        self._last_right_click_time = 0.0

        # Drag state
        self._is_dragging = False
        self._fist_frame_count = 0

        # Previous gesture for edge transitions
        self._prev_gesture = Gesture.NONE

    @property
    def is_dragging(self) -> bool:
        return self._is_dragging

    def execute(self, gesture: Gesture, landmarks, scroll_delta: float = 0.0):
        """
        Execute the mouse action corresponding to the current gesture.

        Args:
            gesture: Current classified gesture
            landmarks: MediaPipe hand landmarks (for position tracking)
            scroll_delta: Y-delta from gesture recognizer (for scroll)
        """
        # ── Handle gesture transitions ──
        if gesture != self._prev_gesture:
            self._on_gesture_change(self._prev_gesture, gesture)
        self._prev_gesture = gesture

        # ── No hand detected ──
        if gesture == Gesture.NONE:
            self._smoother.reset()
            self._fist_frame_count = 0
            return

        # ── Get cursor target position (from index fingertip) ──
        if landmarks is not None:
            screen_x, screen_y = self._landmark_to_screen(landmarks)
        else:
            return

        # ── Execute action based on gesture ──
        if gesture == Gesture.POINT:
            # Move cursor — smooth and go
            sx, sy = self._smoother.smooth(screen_x, screen_y)
            pyautogui.moveTo(int(sx), int(sy), _pause=False)
            self._fist_frame_count = 0

        elif gesture == Gesture.PINCH:
            # Left click (debounced)
            sx, sy = self._smoother.smooth(screen_x, screen_y)
            pyautogui.moveTo(int(sx), int(sy), _pause=False)
            now = time.time()
            if now - self._last_click_time > config.CLICK_DEBOUNCE:
                pyautogui.click(_pause=False)
                self._last_click_time = now

        elif gesture == Gesture.RIGHT_CLICK:
            # Right click (debounced)
            sx, sy = self._smoother.smooth(screen_x, screen_y)
            pyautogui.moveTo(int(sx), int(sy), _pause=False)
            now = time.time()
            if now - self._last_right_click_time > config.CLICK_DEBOUNCE:
                pyautogui.rightClick(_pause=False)
                self._last_right_click_time = now

        elif gesture == Gesture.FIST:
            # Drag: hold left button and move
            self._fist_frame_count += 1
            if self._fist_frame_count >= config.DRAG_ENTER_FRAMES:
                sx, sy = self._smoother.smooth(screen_x, screen_y)
                if not self._is_dragging:
                    pyautogui.mouseDown(_pause=False)
                    self._is_dragging = True
                pyautogui.moveTo(int(sx), int(sy), _pause=False)

        elif gesture == Gesture.SCROLL:
            # Scroll based on vertical hand movement
            if abs(scroll_delta) > config.SCROLL_Y_THRESHOLD:
                # Negative delta = hand moved up = scroll up (positive scroll value)
                scroll_amount = int(-scroll_delta * config.SCROLL_SENSITIVITY * 100)
                scroll_amount = max(-15, min(15, scroll_amount))  # Clamp
                if scroll_amount != 0:
                    pyautogui.scroll(scroll_amount, _pause=False)

        elif gesture == Gesture.IDLE:
            # Open palm — do nothing, cursor stays put
            self._fist_frame_count = 0

    def _on_gesture_change(self, old_gesture: Gesture, new_gesture: Gesture):
        """Handle transition between gestures."""
        # Release drag if leaving fist
        if old_gesture == Gesture.FIST and self._is_dragging:
            pyautogui.mouseUp(_pause=False)
            self._is_dragging = False
            self._fist_frame_count = 0

        # Reset smoother on certain transitions for snappier response
        if old_gesture == Gesture.NONE and new_gesture != Gesture.NONE:
            self._smoother.reset()

    def _landmark_to_screen(self, landmarks) -> tuple[float, float]:
        """
        Convert normalized landmark position to screen coordinates.
        Uses index fingertip (landmark 8) as the cursor reference.

        Applies margin mapping: the central zone of the camera frame
        maps to the full screen, so you don't need to reach extreme edges.
        """
        lm = landmarks  # Tasks API returns a direct list
        index_tip = lm[8]

        # Apply margins: remap the [margin, 1-margin] range to [0, 1]
        mx = config.SCREEN_MARGIN_X
        my = config.SCREEN_MARGIN_Y

        # Clamp and remap
        norm_x = (index_tip.x - mx) / (1.0 - 2 * mx)
        norm_y = (index_tip.y - my) / (1.0 - 2 * my)

        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # Map to screen pixels
        screen_x = norm_x * self._screen_w
        screen_y = norm_y * self._screen_h

        return screen_x, screen_y
