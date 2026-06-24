# 🖐️ AirMouse — Iron Man-Style Gesture Mouse Control

Turn your webcam into an air mouse! Point, click, drag, and scroll using hand gestures — no special hardware needed.

All processing runs **100% locally** on your CPU using Google's MediaPipe hand tracking.

---

## 🚀 Quick Start

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run AirMouse

```bash
python main.py
```

### 3. Show your hand and start controlling!

---

## ✋ Gesture Guide

| Gesture | How To | What It Does |
|:--------|:-------|:-------------|
| ☝️ **Point** | Raise only your index finger | Moves the cursor |
| 🤏 **Pinch** | Touch thumb tip to index fingertip | Left click |
| ✌️ **Peace Pinch** | Index up + touch thumb to middle finger | Right click |
| ✊ **Fist** | Close all fingers into a fist | Click-and-drag |
| 🤟 **Scroll** | Raise index + middle fingers, move hand up/down | Scroll |
| ✋ **Open Palm** | Spread all 5 fingers | Pause cursor (idle) |

---

## ⌨️ Keyboard Controls

| Key | Action |
|:----|:-------|
| `q` | Quit AirMouse |
| `p` | Pause / Resume hand tracking |

**Emergency Stop:** Move your physical mouse to the top-left corner of the screen (0, 0).

---

## ⚙️ Configuration

Edit `config.py` to tune:

| Setting | Default | Description |
|:--------|:--------|:------------|
| `CAMERA_INDEX` | `0` | Which webcam to use |
| `PINCH_THRESHOLD` | `0.045` | How close thumb/index must be to register a click |
| `EMA_ALPHA_MIN` | `0.15` | Smoothing when hand is still (lower = smoother) |
| `EMA_ALPHA_MAX` | `0.70` | Smoothing when hand is moving (higher = more responsive) |
| `DEADBAND_PIXELS` | `3` | Ignore movements smaller than this (prevents drift) |
| `CLICK_DEBOUNCE` | `0.25` | Minimum seconds between clicks |
| `SCROLL_SENSITIVITY` | `25` | How fast scrolling responds |
| `SCREEN_MARGIN_X/Y` | `0.1/0.12` | Shrink tracking zone (so you don't need to reach edges) |

---

## 📁 Project Structure

```
AIRMOUSE/
├── main.py                  # Entry point — runs the main loop
├── hand_tracker.py          # MediaPipe hand landmark detection
├── gesture_recognizer.py    # Classifies gestures from landmarks
├── mouse_controller.py      # Maps gestures to mouse actions
├── smoother.py              # Adaptive EMA cursor smoothing
├── overlay.py               # Iron Man-style HUD overlay
├── config.py                # All tunable settings
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

---

## 🔧 Troubleshooting

**Camera not found:**
- Make sure no other app is using your webcam
- Try changing `CAMERA_INDEX` in `config.py` (try `1` or `2`)

**Cursor is too jittery:**
- Lower `EMA_ALPHA_MIN` (e.g., `0.1`)
- Increase `DEADBAND_PIXELS` (e.g., `5`)

**Clicks firing too often:**
- Increase `CLICK_DEBOUNCE` (e.g., `0.4`)
- Increase `PINCH_THRESHOLD` (e.g., `0.06`)

**Tracking feels laggy:**
- Increase `EMA_ALPHA_MAX` (e.g., `0.85`)
- Make sure you have good lighting on your hand

**Hand not detected:**
- Ensure your hand is well-lit and visible to the camera
- Try lowering `MP_DETECTION_CONFIDENCE` (e.g., `0.5`)

---

## 📋 Requirements

- Python 3.9+
- Webcam
- Windows (PyAutoGUI mouse control)

---

## License

MIT — Use it however you want! 🦾
# HandMouse
