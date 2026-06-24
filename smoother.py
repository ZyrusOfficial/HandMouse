"""
AirMouse — Adaptive EMA Cursor Smoother
Eliminates jitter while keeping cursor responsive to intentional movement.
"""

import math
import config


class CursorSmoother:
    """
    Smooths raw (x, y) screen coordinates using an Adaptive Exponential
    Moving Average with deadband filtering.

    - When the hand moves fast → alpha is high → cursor is responsive
    - When the hand is nearly still → alpha is low → jitter is killed
    - Sub-threshold movements are ignored entirely (deadband)
    """

    def __init__(self):
        self._prev_x = None
        self._prev_y = None
        self._alpha_min = config.EMA_ALPHA_MIN
        self._alpha_max = config.EMA_ALPHA_MAX
        self._speed_threshold = config.EMA_SPEED_THRESHOLD
        self._deadband = config.DEADBAND_PIXELS

    def reset(self):
        """Reset state — call when hand re-enters the frame."""
        self._prev_x = None
        self._prev_y = None

    def smooth(self, raw_x: float, raw_y: float) -> tuple[float, float]:
        """
        Apply adaptive EMA smoothing to raw screen coordinates.

        Args:
            raw_x: Raw screen X coordinate
            raw_y: Raw screen Y coordinate

        Returns:
            (smoothed_x, smoothed_y) tuple
        """
        if self._prev_x is None or self._prev_y is None:
            # First frame — initialize without smoothing
            self._prev_x = raw_x
            self._prev_y = raw_y
            return raw_x, raw_y

        # Calculate movement speed (pixel distance from last frame)
        dx = raw_x - self._prev_x
        dy = raw_y - self._prev_y
        speed = math.sqrt(dx * dx + dy * dy)

        # Deadband: ignore tiny movements to prevent drift
        if speed < self._deadband:
            return self._prev_x, self._prev_y

        # Adaptive alpha: scale linearly with speed
        t = min(speed / self._speed_threshold, 1.0)
        alpha = self._alpha_min + t * (self._alpha_max - self._alpha_min)

        # EMA filter
        smoothed_x = alpha * raw_x + (1.0 - alpha) * self._prev_x
        smoothed_y = alpha * raw_y + (1.0 - alpha) * self._prev_y

        self._prev_x = smoothed_x
        self._prev_y = smoothed_y

        return smoothed_x, smoothed_y
