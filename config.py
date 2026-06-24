"""
AirMouse Configuration
All tunable parameters in one place.
"""

# ─── Camera ──────────────────────────────────────────────
CAMERA_INDEX = 0            # Which webcam to use (0 = default)
CAMERA_WIDTH = 640          # Capture resolution width
CAMERA_HEIGHT = 480         # Capture resolution height

# ─── MediaPipe Hands ─────────────────────────────────────
MP_MAX_HANDS = 1            # Track only 1 hand for performance
MP_DETECTION_CONFIDENCE = 0.7
MP_TRACKING_CONFIDENCE = 0.6

# ─── Gesture Thresholds ─────────────────────────────────
# Pinch: Euclidean distance between thumb tip and index tip
# (normalized coordinates, so values are 0.0 – 1.0 range)
PINCH_THRESHOLD = 0.045          # Thumb↔Index distance to trigger click
RIGHT_CLICK_THRESHOLD = 0.045    # Thumb↔Middle distance to trigger right-click

# Finger "up" detection: tip must be this many units above MCP
FINGER_UP_MARGIN = 0.02

# Scroll: minimum Y-delta per frame to register a scroll tick
SCROLL_SENSITIVITY = 25     # Pixels of scroll per detected unit
SCROLL_Y_THRESHOLD = 0.01   # Min Y-change to trigger scroll

# ─── Cursor Smoothing (Adaptive EMA) ────────────────────
EMA_ALPHA_MIN = 0.15        # Heavy smoothing (hand nearly still)
EMA_ALPHA_MAX = 0.70        # Light smoothing (hand moving fast)
EMA_SPEED_THRESHOLD = 80    # Pixel delta that triggers max alpha
DEADBAND_PIXELS = 3         # Ignore movements smaller than this

# ─── Mouse Control ──────────────────────────────────────
# Screen mapping margins: shrink the effective tracking zone
# so you don't have to reach the very edges of the camera frame
SCREEN_MARGIN_X = 0.1       # 10% margin on each side horizontally
SCREEN_MARGIN_Y = 0.12      # 12% margin on top/bottom

# Debounce: minimum time (seconds) between repeated click actions
CLICK_DEBOUNCE = 0.25       # 250ms between clicks
DRAG_ENTER_FRAMES = 3       # Consecutive fist frames before drag starts

# ─── Overlay / HUD ──────────────────────────────────────
SHOW_OVERLAY = True         # Show the camera feed with overlay
OVERLAY_WINDOW_NAME = "AirMouse 🖐️"

# Colors (BGR for OpenCV)
COLOR_CYAN = (255, 255, 0)       # Landmark connections
COLOR_ORANGE = (0, 140, 255)     # Fingertips
COLOR_GREEN = (0, 255, 100)      # Active/up indicators
COLOR_RED = (0, 0, 255)          # Down/inactive indicators
COLOR_HUD_BG = (20, 20, 20)     # HUD panel background
COLOR_HUD_TEXT = (220, 220, 220) # HUD text
COLOR_GESTURE = (0, 220, 255)    # Current gesture label
COLOR_FPS = (100, 255, 100)      # FPS counter

# ─── Key Bindings ────────────────────────────────────────
KEY_QUIT = ord('q')
KEY_PAUSE = ord('p')
