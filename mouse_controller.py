"""
AirMouse — Mouse Controller
Translates recognized gestures into actual Windows mouse events.
"""

import time
import math
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
    - Cursor movement with adaptive smoothing and blended tracking point
    - Left click, right click with debounce
    - Click-and-drag mode
    - Velocity-scaled scroll with Y-delta tracking
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
        
        # Scroll state
        self._scroll_accumulator = 0.0

        # Previous gesture for edge transitions
        self._prev_gesture = Gesture.NONE

        # Track the last known cursor position (for smoother re-entry)
        self._last_cursor_x = None
        self._last_cursor_y = None

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
            self._last_cursor_x = None
            self._last_cursor_y = None
            return

        # ── Get cursor target position (blended tracking point) ──
        if landmarks is not None:
            screen_x, screen_y = self._landmark_to_screen(landmarks)
        else:
            return

        # ── Execute action based on gesture ──
        if gesture == Gesture.POINT:
            # Move cursor — smooth and go
            sx, sy = self._smoother.smooth(screen_x, screen_y)
            pyautogui.moveTo(int(sx), int(sy), _pause=False)
            # Remember position for smoother re-entry
            self._last_cursor_x = sx
            self._last_cursor_y = sy
            self._fist_frame_count = 0

        elif gesture == Gesture.PINCH:
            # Left click (debounced)
            # We purposely DO NOT update the cursor position here.
            # Freezing the cursor during a pinch stops it from jumping 
            # as your index finger moves to touch your thumb!
            now = time.time()
            if now - self._last_click_time > config.CLICK_DEBOUNCE:
                pyautogui.click(_pause=False)
                self._last_click_time = now

        elif gesture == Gesture.RIGHT_CLICK:
            # Right click (debounced)
            # Freeze cursor position here too
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
                self._last_cursor_x = sx
                self._last_cursor_y = sy

        elif gesture == Gesture.SCROLL:
            # Freeze cursor position while scrolling
            # Accumulate the vertical hand movement
            self._scroll_accumulator += scroll_delta
            
            if abs(self._scroll_accumulator) > config.SCROLL_Y_THRESHOLD:
                # Velocity-scaled scrolling: faster hand movement = bigger scroll
                velocity = abs(scroll_delta)
                scroll_amount = config.SCROLL_BASE_AMOUNT + \
                    velocity * config.SCROLL_VELOCITY_SCALE
                scroll_amount = min(scroll_amount, config.SCROLL_MAX_AMOUNT)
                scroll_amount = int(scroll_amount)
                
                # Negative delta = hand moved up = scroll up
                direction = 1 if self._scroll_accumulator < 0 else -1
                
                pyautogui.scroll(direction * scroll_amount, _pause=False)
                
                # Subtract threshold instead of full reset — preserves momentum
                # so continuous movement triggers continuous scrolling
                if self._scroll_accumulator > 0:
                    self._scroll_accumulator -= config.SCROLL_Y_THRESHOLD
                else:
                    self._scroll_accumulator += config.SCROLL_Y_THRESHOLD

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

        # Seed smoother with last known cursor position when returning to POINT
        # This prevents the jump that happens when the smoother resets and
        # snaps to the raw (noisy) landmark position
        if new_gesture == Gesture.POINT and old_gesture != Gesture.POINT:
            if self._last_cursor_x is not None:
                self._smoother.seed(self._last_cursor_x, self._last_cursor_y)
            else:
                self._smoother.reset()

        if new_gesture == Gesture.NONE and old_gesture != Gesture.NONE:
            self._smoother.reset()
            
        if old_gesture == Gesture.SCROLL:
            self._scroll_accumulator = 0.0

    def _landmark_to_screen(self, landmarks) -> tuple[float, float]:
        """
        Convert normalized landmark position to screen coordinates.
        
        Uses a BLENDED tracking point: weighted average of index fingertip (lm[8])
        and index MCP knuckle (lm[5]). The fingertip provides responsiveness while
        the knuckle anchors against jitter — the MCP is much more stable because
        it's closer to the wrist in the kinematic chain.

        Applies margin mapping: the central zone of the camera frame
        maps to the full screen, so you don't need to reach extreme edges.
        """
        lm = landmarks  # Tasks API returns a direct list
        index_tip = lm[8]
        index_mcp = lm[5]

        # Blend fingertip and knuckle for stability
        tip_w = config.CURSOR_TIP_WEIGHT
        mcp_w = config.CURSOR_MCP_WEIGHT
        raw_x = tip_w * index_tip.x + mcp_w * index_mcp.x
        raw_y = tip_w * index_tip.y + mcp_w * index_mcp.y

        # Apply margins: remap the [margin, 1-margin] range to [0, 1]
        mx = config.SCREEN_MARGIN_X
        my = config.SCREEN_MARGIN_Y

        # Clamp and remap
        norm_x = (raw_x - mx) / (1.0 - 2 * mx)
        norm_y = (raw_y - my) / (1.0 - 2 * my)

        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        # Map to screen pixels
        screen_x = norm_x * self._screen_w
        screen_y = norm_y * self._screen_h

        return screen_x, screen_y
