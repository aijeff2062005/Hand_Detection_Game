"""
hand_control.py  –  Điều khiển thiết bị thông minh bằng cử chỉ tay
====================================================================
Sử dụng OpenCV + MediaPipe để nhận diện các tư thế tay và ánh xạ
thành lệnh điều khiển cho game Zombioo.

Cử chỉ được nhận diện
─────────────────────
  Tên gesture   │ Mô tả ngón tay                       │ Điều khiển
  ──────────────┼──────────────────────────────────────┼──────────────────
  idle          │ Nắm tay                               │ Đứng yên
  move_left     │ Chỉ ngón trỏ sang trái                │ Di chuyển trái
  move_right    │ Chỉ ngón trỏ sang phải                │ Di chuyển phải
  jump          │ 👍 (chỉ ngón cái lên)                 │ Nhảy
  shoot         │ 🤟 (ngón trỏ + giữa duỗi)            │ Bắn
  grenade       │ ✌️ (chỉ 3 ngón: trỏ+giữa+áp út)       │ Ném lựu đạn
  molotov       │ 🖐 (4 ngón, không có ngón cái)        │ Ném Molotov
  reload        │ ✋ (5 ngón mở)                        │ Nạp đạn
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional

import cv2
import mediapipe as mp

_mp_hands_sol = mp.solutions.hands
_mp_draw_sol  = mp.solutions.drawing_utils
_mp_style_sol = mp.solutions.drawing_styles
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Cấu hình giao diện camera
# ─────────────────────────────────────────────────────────────────────────────
_OVERLAY_FONT      = cv2.FONT_HERSHEY_SIMPLEX
_COLOR_GREEN       = (0, 230, 80)
_COLOR_RED         = (50, 50, 255)
_COLOR_BLUE        = (255, 128, 0)
_COLOR_WHITE       = (255, 255, 255)
_COLOR_GRAY        = (80, 80, 80)
_COLOR_GOLD        = (0, 205, 255)
_COLOR_BG          = (18, 18, 30, 180)      # BGRA

# MediaPipe landmark indices
_TIP   = [4, 8, 12, 16, 20]   # ngón cái, trỏ, giữa, áp út, út
_MCP   = [2, 5, 9,  13, 17]   # khớp gốc


# ─────────────────────────────────────────────────────────────────────────────
# Kiểu dữ liệu trả về
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class HandData:
    """Dữ liệu trả về từ mỗi lần đọc camera."""

    # Toạ độ pixel của đầu ngón trỏ (đã smooth) – None nếu không thấy tay
    x: Optional[int] = None
    y: Optional[int] = None

    # Tên gesture hiện tại
    gesture: str = "idle"

    # Góc nghiêng bàn tay theo trục ngang (radian, dương = nghiêng phải)
    tilt: float = 0.0

    # Trạng thái từng ngón (1=duỗi, 0=co)
    fingers: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0])

    # Vận tốc di chuyển của đầu ngón trỏ (pixel/frame)
    vx: float = 0.0
    vy: float = 0.0

    # Có tay trong khung hình không
    hand_present: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Bộ nhận diện chính
# ─────────────────────────────────────────────────────────────────────────────
class HandController:
    """
    Nhận diện cử chỉ tay thời gian thực bằng OpenCV + MediaPipe.

    Parameters
    ----------
    camera_index : int
        Chỉ số camera (mặc định 0).
    smoothing : int
        Hệ số làm mịn vị trí (1 = không làm mịn, giá trị cao hơn = mịn hơn).
    history : int
        Số frame dùng để ổn định gesture (majority-vote).
    min_confidence : float
        Ngưỡng tin cậy tối thiểu của MediaPipe.
    show_debug : bool
        Hiển thị cửa sổ camera với overlay debug.
    """

    def __init__(
        self,
        camera_index: int = 0,
        smoothing: int = 6,
        history: int = 5,
        min_confidence: float = 0.75,
        show_debug: bool = True,
    ) -> None:
        self.smoothing      = smoothing
        self.history        = history
        self.show_debug     = show_debug

        # Camera
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Không mở được camera {camera_index}")

        self.cam_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.cam_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # MediaPipe Hands (dùng import trực tiếp – tương thích 0.10.x)
        self._mp_hands = _mp_hands_sol
        self._mp_draw  = _mp_draw_sol
        self._mp_style = _mp_style_sol
        self.hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=1,
            min_detection_confidence=min_confidence,
            min_tracking_confidence=min_confidence - 0.1,
        )

        # State
        self._prev_x: float = self.cam_w / 2
        self._prev_y: float = self.cam_h / 2
        self._prev_x2: float = self.cam_w / 2
        self._prev_y2: float = self.cam_h / 2
        self._gesture_buf: deque[str] = deque(maxlen=history)
        self._last_data  = HandData()
        self._fps_buf: deque[float] = deque(maxlen=30)
        self._last_time  = time.perf_counter()

        # Background thread
        self._lock   = threading.Lock()
        self._stop   = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="HandCtrl")
        self._thread.start()
        logger.info("HandController khởi động (camera=%d)", camera_index)

    # ──────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────

    def get_data(self) -> HandData:
        """Trả dữ liệu tay mới nhất (thread-safe)."""
        with self._lock:
            return self._last_data

    def stop(self) -> None:
        """Dừng thread camera và giải phóng tài nguyên."""
        self._stop.set()
        self._thread.join(timeout=2)
        self.cap.release()
        cv2.destroyAllWindows()
        logger.info("HandController đã dừng.")

    # ──────────────────────────────────────────────
    # Vòng lặp nội bộ (chạy trong thread riêng)
    # ──────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop.is_set():
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            # Tính FPS
            now = time.perf_counter()
            self._fps_buf.append(1.0 / max(now - self._last_time, 1e-6))
            self._last_time = now

            frame = cv2.flip(frame, 1)
            data  = self._process(frame)

            with self._lock:
                self._last_data = data

            if self.show_debug:
                self._draw_debug(frame, data)
                cv2.imshow("✋ Hand Control – Zombioo", frame)
                if cv2.waitKey(1) & 0xFF == 27:   # ESC để tắt cửa sổ debug
                    self.show_debug = False
                    cv2.destroyWindow("✋ Hand Control – Zombioo")

    # ──────────────────────────────────────────────
    # Xử lý frame
    # ──────────────────────────────────────────────

    def _process(self, frame: np.ndarray) -> HandData:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True

        data = HandData()

        if not results.multi_hand_landmarks:
            self._gesture_buf.clear()
            return data

        # Vẽ skeleton
        if self.show_debug:
            self._mp_draw.draw_landmarks(
                frame,
                results.multi_hand_landmarks[0],
                self._mp_hands.HAND_CONNECTIONS,
                self._mp_style.get_default_hand_landmarks_style(),
                self._mp_style.get_default_hand_connections_style(),
            )

        lm = results.multi_hand_landmarks[0].landmark

        # ── Vị trí đầu ngón trỏ (đã smooth) ──
        raw_x = lm[8].x * self.cam_w
        raw_y = lm[8].y * self.cam_h

        sx = self._prev_x + (raw_x - self._prev_x) / self.smoothing
        sy = self._prev_y + (raw_y - self._prev_y) / self.smoothing

        vx = sx - self._prev_x
        vy = sy - self._prev_y

        self._prev_x, self._prev_y = sx, sy

        # ── Phân tích ngón tay ──
        fingers = self._fingers_up(lm)

        # ── Nghiêng bàn tay ──
        tilt = self._hand_tilt(lm)

        # ── Nhận diện gesture ──
        raw_gesture = self._classify(fingers, lm, tilt)
        self._gesture_buf.append(raw_gesture)
        gesture = self._majority_vote()

        data.x           = int(sx)
        data.y           = int(sy)
        data.gesture     = gesture
        data.tilt        = tilt
        data.fingers     = fingers
        data.vx          = vx
        data.vy          = vy
        data.hand_present = True
        return data

    # ──────────────────────────────────────────────
    # Phân tích ngón tay
    # ──────────────────────────────────────────────

    def _fingers_up(self, lm) -> List[int]:
        """Trả danh sách 5 bit: 1=duỗi, 0=co (cái, trỏ, giữa, áp út, út)."""
        fingers = []

        # Ngón cái: so sánh theo trục x (do bàn tay bị lật)
        thumb_tip  = lm[4]
        thumb_mcp  = lm[2]
        index_mcp  = lm[5]
        # Nếu tip nằm bên phải (xa) so với khớp cái → duỗi
        if abs(thumb_tip.x - index_mcp.x) > 0.04:
            fingers.append(1 if thumb_tip.x > thumb_mcp.x else 0)
        else:
            fingers.append(0)

        # 4 ngón còn lại: tip.y < pip.y → duỗi (y tăng xuống dưới)
        for tip_id, pip_id in zip([8, 12, 16, 20], [6, 10, 14, 18]):
            fingers.append(1 if lm[tip_id].y < lm[pip_id].y else 0)

        return fingers

    def _hand_tilt(self, lm) -> float:
        """Góc nghiêng bàn tay (radian, âm=trái, dương=phải)."""
        dx = lm[5].x - lm[17].x
        dy = lm[5].y - lm[17].y
        return math.atan2(dy, dx)

    # ──────────────────────────────────────────────
    # Phân loại gesture
    # ──────────────────────────────────────────────

    def _classify(self, fingers: List[int], lm, tilt: float) -> str:
        f = fingers   # [cái, trỏ, giữa, áp út, út]

        # ── Các chỉ số hay dùng ──
        _tip_dx      = lm[8].x - lm[5].x   # ngang: tip ngón trỏ so gốc
        _hand_lean   = lm[9].x - lm[0].x   # nghiêng bàn tay: MCP giữa vs cổ tay
        _index_curled = lm[8].y > lm[6].y  # True = ngón trỏ gập (tip thấp hơn PIP)

        # ─────────────────────────────────────────────────────
        # 5 ngón mở = reload
        # ─────────────────────────────────────────────────────
        if f == [1, 1, 1, 1, 1]:
            return "reload"

        # ─────────────────────────────────────────────────────
        # Chỉ ngón cái = jump tại chỗ
        # ─────────────────────────────────────────────────────
        if f == [1, 0, 0, 0, 0]:
            return "jump"

        # ─────────────────────────────────────────────────────
        # Trỏ + giữa = shoot
        # ─────────────────────────────────────────────────────
        if f == [0, 1, 1, 0, 0]:
            return "shoot"

        # ─────────────────────────────────────────────────────
        # Trỏ + giữa + áp út = grenade
        # ─────────────────────────────────────────────────────
        if f == [0, 1, 1, 1, 0]:
            return "grenade"

        # ─────────────────────────────────────────────────────
        # 4 ngón (không cái) = molotov
        # ─────────────────────────────────────────────────────
        if f == [0, 1, 1, 1, 1]:
            return "molotov"

        # ─────────────────────────────────────────────────────
        # Ngón trỏ DUỖI THẲNG → Di chuyển / aim
        #   Nghiêng ngang TRÁI  (tip_dx < -0.05) → move_left
        #   Nghiêng ngang PHẢI  (tip_dx > +0.05) → move_right
        #   Thẳng lên                              → aim
        # ─────────────────────────────────────────────────────
        if f == [0, 1, 0, 0, 0]:
            if _tip_dx < -0.05:
                return "move_left"
            elif _tip_dx > 0.05:
                return "move_right"
            return "aim"

        # ─────────────────────────────────────────────────────
        # Ngón trỏ GẬP (tip thấp hơn PIP) + nghiêng bàn tay
        #   → jump_left  hoặc  jump_right
        #
        #   Cách thực hiện:
        #     1. Duỗi ngón trỏ sang trái/phải (move_left/right)
        #     2. Gập ngón trỏ xuống (cuộn đầu ngón vào trong)
        #        → bàn tay vẫn nghiêng theo hướng cũ
        #     3. Hướng nghiêng (_hand_lean) quyết định trái/phải
        #
        #   Điều kiện: ngón giữa + áp út KHÔNG duỗi (tránh nhầm
        #   với shoot / grenade / molotov)
        # ─────────────────────────────────────────────────────
        if _index_curled and f[0] == 0 and f[2] == 0 and f[3] == 0:
            if _hand_lean < -0.06:
                return "jump_left"
            elif _hand_lean > 0.06:
                return "jump_right"

        return "idle"


    def _majority_vote(self) -> str:
        if not self._gesture_buf:
            return "idle"
        from collections import Counter
        return Counter(self._gesture_buf).most_common(1)[0][0]

    # ──────────────────────────────────────────────
    # Debug overlay
    # ──────────────────────────────────────────────

    def _draw_debug(self, frame: np.ndarray, data: HandData) -> None:
        h, w = frame.shape[:2]
        fps  = sum(self._fps_buf) / len(self._fps_buf) if self._fps_buf else 0

        # ── HUD panel (bán trong suốt) ──
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (320, 200), (20, 20, 40), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # Title
        cv2.putText(frame, "HAND CONTROL", (10, 25),
                    _OVERLAY_FONT, 0.65, _COLOR_GOLD, 2, cv2.LINE_AA)

        # FPS
        cv2.putText(frame, f"FPS: {fps:.0f}", (10, 50),
                    _OVERLAY_FONT, 0.55, _COLOR_WHITE, 1, cv2.LINE_AA)

        if data.hand_present:
            # Gesture badge
            color = _gesture_color(data.gesture)
            cv2.rectangle(frame, (8, 58), (315, 90), color, -1)
            cv2.putText(frame, f"Gesture: {data.gesture.upper()}", (12, 82),
                        _OVERLAY_FONT, 0.65, (0, 0, 0), 2, cv2.LINE_AA)

            # Tọa độ
            cv2.putText(frame, f"X:{data.x}  Y:{data.y}", (10, 110),
                        _OVERLAY_FONT, 0.5, _COLOR_WHITE, 1, cv2.LINE_AA)

            # Tốc độ
            cv2.putText(frame,
                        f"vX:{data.vx:+.1f}  vY:{data.vy:+.1f}",
                        (10, 130),
                        _OVERLAY_FONT, 0.5, _COLOR_WHITE, 1, cv2.LINE_AA)

            # Ngón tay
            labels = ["T", "I", "M", "R", "P"]  # Cái, Trỏ, Giữa, Áp út, Út
            for i, (lbl, up) in enumerate(zip(labels, data.fingers)):
                cx = 14 + i * 55
                clr = _COLOR_GREEN if up else _COLOR_GRAY
                cv2.circle(frame, (cx + 18, 160), 16, clr, -1)
                cv2.putText(frame, lbl, (cx + 12, 166),
                            _OVERLAY_FONT, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

            # Đầu ngón trỏ
            if data.x is not None:
                cv2.circle(frame, (data.x, data.y), 10, _COLOR_GOLD, 3)
                cv2.circle(frame, (data.x, data.y), 3,  _COLOR_GOLD, -1)

        else:
            cv2.putText(frame, "No hand detected", (10, 80),
                        _OVERLAY_FONT, 0.6, _COLOR_RED, 1, cv2.LINE_AA)

        # Viền khung
        cv2.rectangle(frame, (0, 0), (w - 1, h - 1), _COLOR_BLUE, 2)
        cv2.putText(frame, "ESC = close debug", (w - 180, h - 8),
                    _OVERLAY_FONT, 0.4, _COLOR_GRAY, 1, cv2.LINE_AA)


def _gesture_color(gesture: str):
    _MAP = {
        "shoot":      (50,  50, 230),
        "grenade":    (30, 160, 255),
        "molotov":    (0,  110, 255),
        "jump":       (0,  200, 100),
        "jump_left":  (0,  170, 140),
        "jump_right": (0,  210,  80),
        "move_left":  (200, 80,  80),
        "move_right": (80, 200,  80),
        "reload":     (180, 180,  0),
        "aim":        (200, 200, 200),
        "idle":       (60,  60,  60),
    }
    return _MAP.get(gesture, (80, 80, 80))


# ─────────────────────────────────────────────────────────────────────────────
# Test độc lập  (python hand_control.py)
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Nhấn ESC trong cửa sổ camera để thoát.")
    ctrl = HandController(show_debug=True)
    try:
        while True:
            d = ctrl.get_data()
            if d.hand_present:
                print(f"[{d.gesture:<12}]  x={d.x:4d}  y={d.y:4d}  "
                      f"fingers={d.fingers}  tilt={math.degrees(d.tilt):+.1f}°")
            time.sleep(0.05)
    except KeyboardInterrupt:
        ctrl.stop()