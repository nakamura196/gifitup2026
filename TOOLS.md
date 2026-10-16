# 作業環境 / Tools used for the checked build

| tool | version |
|---|---|
| macOS | 27.0.1 (arm64) |
| python3 | 3.9.6 |
| numpy / opencv-python / pillow | 2.0.2 / 4.13.0.90 / 10.4.0 (`requirements.txt`) |
| ffmpeg | 8.1.2 (mushi: palette and GIF encoding) |
| gifsicle | LCDF Gifsicle 1.98 (globe: final optimisation) |
| shell | zsh (`md5 -q` is the macOS command) |

The md5 values in `checksums.md5` were obtained with exactly these versions.
Other versions of Pillow / OpenCV / ffmpeg / gifsicle may give a GIF that looks the same but differs in bytes.
