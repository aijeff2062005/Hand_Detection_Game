# 🧟 Zombioo — Gesture-Controlled Zombie Shooter

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/Pygame-2.6-green?style=for-the-badge&logo=pygame" />
  <img src="https://img.shields.io/badge/MediaPipe-0.10-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/OpenCV-4.9-red?style=for-the-badge&logo=opencv" />
  <img src="https://img.shields.io/github/license/jankupczyk/Zombioo?color=important&style=for-the-badge" />
</p>

<p align="center">
  <img src="demo/demoNEW.gif" alt="Zombioo gameplay demo" width="720"/>
</p>

> **Zombioo** là game bắn zombie 2D viết bằng Python/Pygame, tích hợp hệ thống **điều khiển bằng cử chỉ tay** thời gian thực sử dụng OpenCV và MediaPipe.  
> Bạn không cần chạm vào bàn phím — chỉ cần để tay trước camera!

---

## ✨ Tính năng nổi bật

| Tính năng | Mô tả |
|-----------|-------|
| 🤚 **Điều khiển cử chỉ tay** | Nhận diện 8 tư thế tay khác nhau theo thời gian thực |
| 🎮 **Dual-input** | Bàn phím và tay cùng hoạt động song song, không xung đột |
| 🧠 **Majority-vote smoothing** | Buffer 5 frame để ổn định gesture, tránh trigger nhầm |
| 🖥️ **Debug HUD** | Cửa sổ camera realtime hiển thị gesture, FPS, trạng thái từng ngón |
| 💥 **6 màn chơi** | Cấp độ tăng dần, kẻ thù thông minh hơn |
| 🔫 **Vũ khí đa dạng** | Súng, lựu đạn, Molotov, hộp máu, hộp đạn |

---

## ✋ Bảng cử chỉ tay

| Cử chỉ | Tư thế | Điều khiển |
|--------|--------|------------|
| 👈 `move_left` | Ngón trỏ chỉ sang trái | Di chuyển trái |
| 👉 `move_right` | Ngón trỏ chỉ sang phải | Di chuyển phải |
| 👍 `jump` | Chỉ ngón cái | Nhảy |
| 🤟 `shoot` | Ngón trỏ + ngón giữa duỗi | Bắn |
| ✌️➕ `grenade` | Ngón trỏ + giữa + áp út | Ném lựu đạn |
| 🖐️ `molotov` | 4 ngón (không cái) | Ném Molotov |
| ✋ `reload` | 5 ngón mở hoàn toàn | Nạp đạn |
| ✊ `idle` | Nắm tay | Đứng yên |

> **Mẹo:** Giữ tay ổn định dưới ánh sáng tốt để nhận diện chính xác hơn.

---

## ⌨️ Điều khiển bàn phím (vẫn hoạt động song song)

| Phím | Hành động |
|------|-----------|
| `A` | Di chuyển trái |
| `D` | Di chuyển phải |
| `W` | Nhảy |
| `Space` | Bắn |
| `Q` | Ném lựu đạn |
| `E` | Ném Molotov |
| `M` | Tắt nhạc |
| `U` | Bật nhạc |
| `F` | Toàn màn hình |
| `F5` | Chụp ảnh màn hình |
| `ESC` | Thoát game |

---

## 🛠️ Cài đặt

### Yêu cầu
- Python **3.10+**
- [uv](https://github.com/astral-sh/uv) — trình quản lý package nhanh
- Webcam (hoặc camera tích hợp)

### Cài nhanh với `uv`

```bash
# Clone repo
git clone https://github.com/jankupczyk/Zombioo.git
cd Zombioo

# Cài toàn bộ dependencies
uv sync

# Chạy game
cd Zombioo
uv run python MAINGAME.py
```

### Cài thủ công với pip

```bash
pip install pygame opencv-python "mediapipe>=0.10.9,<0.10.14" numpy pyautogui
python Zombioo/MAINGAME.py
```

---

## 📦 Tech Stack

| Thư viện | Phiên bản | Vai trò |
|----------|-----------|---------|
| [Pygame](https://www.pygame.org) | ≥ 2.5 | Game engine, âm thanh, đồ hoạ |
| [OpenCV](https://opencv.org) | ≥ 4.9 | Đọc camera, xử lý ảnh, debug overlay |
| [MediaPipe](https://mediapipe.dev) | 0.10.9 – 0.10.13 | Nhận diện landmark bàn tay (21 điểm) |
| [NumPy](https://numpy.org) | ≥ 1.26 | Tính toán vector/ma trận |
| [PyAutoGUI](https://pyautogui.readthedocs.io) | ≥ 0.9 | Tự động hoá giao diện (phụ trợ) |

---

## 🗂️ Cấu trúc thư mục

```
game/
├── hand_control.py          # Module nhận diện cử chỉ tay (OpenCV + MediaPipe)
├── pyproject.toml           # Cấu hình dependencies (uv sync)
└── Zombioo/
    ├── MAINGAME.py          # Entry point chính của game
    ├── button.py            # Component nút bấm UI
    ├── audio/               # Nhạc nền & hiệu ứng âm thanh
    ├── img/                 # Sprite, tile, icon, background
    ├── font/                # Font chữ Futurot
    ├── level/               # Dữ liệu bản đồ (CSV)
    ├── screenshots/         # Ảnh chụp màn hình (F5)
    └── demo/                # GIF demo
```

---

## 🎮 Yêu cầu hệ thống

| | Yêu cầu tối thiểu |
|--|--|
| **OS** | Windows 10 / 11 (hoặc Linux/macOS) |
| **CPU** | Bất kỳ CPU x64 hiện đại |
| **RAM** | 512 MB+ |
| **GPU** | Không bắt buộc (MediaPipe dùng CPU) |
| **Camera** | Webcam 720p trở lên (khuyến nghị) |
| **Python** | 3.10 – 3.12 |

---

## 📸 Chụp ảnh màn hình

Nhấn `F5` trong lúc chơi để lưu ảnh vào thư mục `screenshots/`.

---

## 📄 Giấy phép

MIT — xem file [`LICENSE`](LICENSE).

---

## 👨‍💻 Tác giả

**Jan Kupczyk** — [GitHub](https://github.com/jankupczyk) · [Zombioo Website](https://jankupczyk.github.io/Zombioo/)

Hand gesture integration by **ThanhVu** using OpenCV + MediaPipe.

---

*Zombioo™ là dự án học tập. Không đảm bảo hỗ trợ lâu dài.*
