> STATUS: DRAFT - UNVERIFIED - requires human review at the Phase 0 gate. Research notes compiled on 2026-10-26 from the sources listed at the end; items not checked against a primary source are marked UNCONFIRMED.

# Wisp: onboard person detection and tracking for a sub-250 g follow-me drone

Research date: 2026-10-26. This is web research only; nothing here was measured on Wisp hardware.

## Labels used in this report

- **MEASURED**: the number appears in the cited source, for the board named.
- **OTHER BOARD**: the number was measured on a different board than the row heading. The board is named.
- **ESTIMATE**: my own arithmetic from cited numbers. The method is stated next to it. It is not a measurement.
- **UNCONFIRMED**: I could not verify the number from a primary source in this session.

**Research limits.** The web-search budget ran out partway through. The research container could also not reach the vendor sites: wiki.luckfox.com, docs.radxa.com, wiki.sipeed.com, milkv.io, ardupilot.org, discuss.ardupilot.org, raspberrypi.com and arxiv.org were all blocked. Where possible I used each vendor's own docs hosted on GitHub instead. Because of this, **board masses and prices are UNCONFIRMED**, along with a few FPS figures. The tables flag each one.

**Two caveats apply to almost every benchmark below:**
1. Benchmark FPS usually counts **inference only**. It leaves out camera capture, resize or letterbox, decoding, Non-Maximum Suppression (NMS) and drawing. Expect the real pipeline to run 20-50 % slower. The +20-50 % is my rule of thumb, not a sourced figure.
2. ncnn `benchncnn` runs each model at a fixed input size with **random weights**. It measures the speed of the network shape, not accuracy.

---

## 1. Person detectors on Raspberry Pi Zero 2 W (and Pi 3/4 where Zero numbers are missing)

### 1a. The best Zero 2 W source: ncnn's official benchmark

Source: Tencent ncnn `benchmark/README.md`, section "Raspberry Pi Zero 2 W Broadcom BCM2710A1, Cortex-A53 (ARMv8) (1.0GHz x 4)". Input sizes come from `benchncnn.cpp`. Settings: loop_count=8, cooling_down=1. FPS = 1000 / average ms.

| Model (ncnn) | Input | Zero 2 W, 4 threads, avg ms | **Zero 2 W FPS** | Zero 2 W, 1 thread, ms | Pi 4 (1.8 GHz), 4 threads, ms / FPS | Radxa Zero 3W CPU (4×A55 1.416 GHz), 4 threads, ms / FPS | COCO mAP (published) |
|---|---|---|---|---|---|---|---|
| yolo-fastestv2 | 352×352 | 81.29 | **12.3** | 127.05 | 37.47 / 26.7 | 26.54 / 37.7 | 24.1 mAP@0.5 (not 0.5:0.95) [dog-qiuqiu] |
| yolo-fastest-1.1 | 320×320 | 99.17 | **10.1** | 155.53 | 48.06 / 20.8 | 47.36 / 21.1 (min 32.87; noisy) | 24.4 mAP@0.5 [dog-qiuqiu] |
| nanodet_m | 320×320 | 166.27 | **6.0** | 301.70 | 68.38 / 14.6 | 66.25 / 15.1 | 20.6 mAP@0.5:0.95 [NanoDet] |
| mobilenet_ssd (MobileNet v1 SSD) | 300×300 | 339.50 | **2.9** | 803.56 | 121.46 / 8.2 | 98.61 / 10.1 | not given in source |
| mobilenet_ssd_int8 | 300×300 | 190.48 | **5.2** | 568.42 | 71.14 / 14.1 | 79.10 / 12.6 | (int8 version of the row above) |
| squeezenet_ssd | 300×300 | 379.13 | 2.6 | 564.44 | 127.61 / 7.8 | 100.86 / 9.9 | – |
| mobilenetv2_yolov3 | 352×352 | 489.37 | 2.0 | 951.72 | 184.88 / 5.4 | 139.54 / 7.2 | – |
| yolov4-tiny | 416×416 | 646.64 | 1.5 | 1258.66 | 207.22 / 4.8 | 171.25 / 5.8 | 21.7 mAP@0.5:0.95 [NanoDet table] |
| blazeface (face only, not a person detector) | 128×128 | 23.10 | 43.3 | 43.96 | 8.69 / 115 | 8.27 / 121 | – |
| FastestDet | 352×352 | not run on Zero 2 W | – | – | 38.69 / 25.8 | 33.65 / 29.7 | – |

**Takeaways from this table**
- On the Zero 2 W, only Yolo-FastestV2 and Yolo-Fastest 1.1 reach about 10 FPS or more (inference only). NanoDet-m reaches about 6 FPS. The rest are too slow for 10 Hz.
- In these ncnn numbers, a Pi 4 at 1.8 GHz is **2.1-3.1× faster** than a Zero 2 W. The ratio is computed per model from the table and ranges from 2.06 (yolo-fastest-1.1) to 3.12 (yolov4-tiny). I use this ratio below to turn Pi 4 numbers into rough Zero 2 W estimates.

### 1b. YOLOv5n / YOLOv8n / YOLO11n, NanoDet-Plus, PicoDet, EfficientDet-Lite0, MobileNet-SSD (TFLite)

| Detector | Input | Board | FPS / latency | Label | COCO mAP@0.5:0.95 | Source |
|---|---|---|---|---|---|---|
| YOLOv8n (NCNN, Ultralytics) | 640 | Zero 2 W ("Raspi-Zero") | about 1 s, "or 1 FPS on the Raspi-Zero" (custom model); stock NCNN "<1 second" | MEASURED (approximate, from text) | 37.3 (640) | MLSysBook [mlsys] |
| YOLOv8n (NCNN, custom bee model) | 640 | Zero 2 W | "inference latency is around 730ms" (~1.4 FPS) | MEASURED | – | Hackster BuzzTech [buzz] |
| YOLOv8n (NCNN) | 640 | Pi 4 ("1950", likely 1950 MHz overclock) | 3.1 FPS | OTHER BOARD | 37.3 | Qengineering YoloV8 [qe-v8] |
| YOLOv8n (NCNN) | 640 | Zero 2 W | ~1.0-1.5 FPS | ESTIMATE (Pi 4 3.1 FPS ÷ 2.1-3.1); agrees with the measured ~1 FPS | 37.3 | – |
| YOLOv8n (NCNN) | **320** | Zero 2 W | ~4-6 FPS | ESTIMATE (¼ of the pixels → about 4× less compute than at 640; not measured anywhere I found) | lower than 37.3 at 320; **no official 320 mAP published** | – |
| YOLOv8n NCNN int8 | 640 | Pi 4 | 2.0 FPS | OTHER BOARD | – | Habr [habr] |
| YOLO11n (ONNX) | 640 | Pi 5 | 6.79 FPS | OTHER BOARD | 39.5 | Ultralytics Raspberry Pi guide [ultra-rpi] |
| YOLO26n (NCNN, FP32) | 640 | Pi 5 | 67.03 ms (~14.9 FPS) | OTHER BOARD | 40.1 (ONNX row) / 47.84 (NCNN row as printed; likely a different metric or typo, UNCONFIRMED) | [ultra-rpi] |
| YOLOv5n (NCNN) | 640 | Pi 4 "1950" | 1.6 FPS | OTHER BOARD | 28.4 (v6.0, per NanoDet table; Qengineering's table lists 22.5, which looks like a copy error) | [qe-v8], [nanodet] |
| YOLO11n / YOLOv5n at 160 or 320 on Zero 2 W | – | – | **no measured source found** | UNCONFIRMED | – | – |
| NanoDet (m) | 320 | Pi 4 "1950" | 13.0 FPS | OTHER BOARD | 20.6 | [qe-v8] |
| NanoDet-Plus-m | 416 | Pi 4 "1950" | 5.0 FPS | OTHER BOARD | 30.4 | [qe-v8] |
| NanoDet-Plus-m | 320 | Kirin 980 (4×A76), ncnn | 11.97 ms | OTHER BOARD (phone SoC) | **27.0** | [nanodet] |
| NanoDet-Plus-m | 320 | Zero 2 W | roughly 3-5 FPS | ESTIMATE (between nanodet_m at 6.0 FPS on Zero 2 W and NanoDet-Plus-416 at 5.0 FPS on Pi 4 ÷ ~2.4; FLOPs 0.9 G vs nanodet_m 0.72 G) | 27.0 | – |
| PP-PicoDet (S, v1) | 320 | Pi 4 "1950" | 7.5 FPS | OTHER BOARD | 27.0 | [qe-v8] |
| PicoDet-XS | 320 | Snapdragon 865, Paddle Lite | 7.81 ms | OTHER BOARD | **23.5** (0.70 M params, 0.67 GFLOPs) | PaddleDetection picodet README [picodet] |
| PicoDet-S (v2) | 320 | Snapdragon 865, Paddle Lite | 9.56 ms | OTHER BOARD | **29.1** (1.18 M params, 0.97 GFLOPs) | [picodet] |
| EfficientDet-Lite0 | 320 | Pixel 4 CPU, 4 threads | 37 ms | OTHER BOARD (phone) | 25.69 % AP | Google LiteRT Model Maker [effdet] |
| EfficientDet-Lite0 | 320 | Pi | not reported | UNCONFIRMED | – | MLSysBook says no latency is given |
| MobileNet-V1 SSD (TFLite) | 300 | Pi 4, 64-bit OS, 1950 MHz | 26.8 FPS (Invoke() only) | OTHER BOARD | not given | Qengineering TFLite [qe-tfl] |
| SSD-MobileNet V2 FPN-Lite int8 (TFLite) | 320 | "Raspi-Zero" | about 600 ms (range 0.5-1.3 s) | MEASURED (the book's "Raspi-Zero" is the Zero 2W kit; label from the source) | – | [mlsys] |
| MediaPipe person detector (OpenCV DNN) | 224 | Pi 4B @1.5 GHz | 105.60 ms | OTHER BOARD | – | OpenCV Zoo benchmark [zoo] |
| NanoDet-Plus (OpenCV DNN, zoo build) | 416 | Pi 4B @1.5 GHz | 214.59 ms | OTHER BOARD | – | [zoo] |
| Qengineering YoloCam (model not named in README) | – | **Zero 2 W** | 2.25 FPS (email version) / 0.91 FPS (GPIO version) | MEASURED (end-to-end app) | – | [yolocam] |

### 1c. Pose and FOMO

| Model | Input | Board | Latency / FPS | Label | Accuracy | Source |
|---|---|---|---|---|---|---|
| MoveNet Lightning INT8 (TFLite) | 192 | Pi 4, 4 threads | 95 ms (~10.5 FPS) | OTHER BOARD | 57.4 mAP (single-person COCO subset) | TF pose page [movenet] |
| MoveNet Lightning FP16 | 192 | Pi 4 | 186 ms | OTHER BOARD | 63.0 | [movenet] |
| MoveNet Lightning INT8 | 192 | Zero 2 W | ~200-300 ms | ESTIMATE (×2.1-3.1) | – | – |
| PoseNet MobileNetV1 (TFLite) | 257 | Pi 4, 64-bit, 1950 MHz | 10.3 FPS | OTHER BOARD | 45.6 | [qe-tfl], [movenet] |
| BlazePose / MediaPipe Pose | – | Zero 2 W | not found | UNCONFIRMED | – | – |
| Edge Impulse FOMO (MobileNetV2 0.1) | 160×160 grayscale | Pi 4 | "60 fps" | OTHER BOARD (vendor claim) | centroids only, no boxes | Edge Impulse docs [fomo] |
| FOMO MobileNetV2 0.35 | 160×160 | Pi 4 | 8 ms | OTHER BOARD | – | [mlsys] |

FOMO gives centroids, not bounding boxes. Wisp needs box size to estimate range, so FOMO is a poor fit unless range comes from another source.

---

## 2. Trackers that run cheaply between detections

### 2a. Single-object trackers in OpenCV

| Tracker | Board | Resolution | FPS | Label | Source |
|---|---|---|---|---|---|
| MOSSE | Pi 3B | 358×288 / 640×480 | 21 / 8 | OTHER BOARD (Pi 3B is A53 @1.2 GHz; Zero 2 W is A53 @1.0 GHz) | Darvishi 2020 [darvishi] |
| KCF | Pi 3B | 358×288 / 640×480 | 16 / 3-4 | OTHER BOARD | [darvishi] |
| MedianFlow | Pi 3B | 358×288 / 640×480 | 15 / 5-6 | OTHER BOARD | [darvishi] |
| CSRT | Pi 3B | 358×288 / 640×480 | 4 / 2-5 | OTHER BOARD | [darvishi] |
| MIL | Pi 3B | 358×288 / 640×480 | 2 / 2 | OTHER BOARD | [darvishi] |
| Boosting / TLD | Pi 3B | 358×288 | 6 / 3 | OTHER BOARD | [darvishi] |
| Nano tracker (`cv::TrackerNano`, NanoTrack v2) | – | – | "much faster and extremely lightweight"; model about 1.9 MB (backbone + neckhead) | No Pi FPS found, UNCONFIRMED | OpenCV docs [nano] |
| ViT tracker (`cv::TrackerVit`, needs OpenCV > 4.8.0) | Pi 4B @1.5 GHz | 1280×720 frame | 48.55 ms (~20.6 FPS) | OTHER BOARD | OpenCV Zoo benchmark [zoo] |
| ViT tracker | Toybrick RV1126 (quad A7) | 1280×720 | 411.41 ms | OTHER BOARD (A7, closest proxy for RV1106's single A7) | [zoo] |
| ViT vs NanoTrack | Apple M2, 1 thread (ONNX Runtime) | – | 4.18 ms vs 5.25 ms; LaSOT AUC 48.6 vs 46.8 | OTHER BOARD | opencv_zoo vittrack README [vit] |
| ViT tracker | Zero 2 W | 1280×720 | ~100-150 ms | ESTIMATE (Pi 4 48.55 ms × 2.1-3.1) | – |

**Interpretation.** On a Zero 2 W, KCF and MOSSE only stay above 10 FPS on small frames (about 360×288 or less, from the Pi 3B data). CSRT and MIL are too slow. The ViT tracker is the most accurate cheap learned tracker. On a Zero 2 W it would likely run slower than the detector loop rate (ESTIMATE). On Pi-class CPUs, **tracking by detection (detector plus a Kalman/IoU association) is the more reliable design**. A KCF/MOSSE tracker on a downscaled region of interest (ROI) can fill gaps between detections.

### 2b. Multi-object association (SORT / ByteTrack / OC-SORT)

- These trackers run on boxes, not pixels, so their cost is negligible compared with the detector. Roboflow's comparison says SORT "runs at hundreds of frames per second" and that ByteTrack's two-stage association "adds almost no extra compute". These are qualitative statements; no Pi figure is given. [roboflow]
- Accuracy on MOT17 with YOLOX detections, default parameters (HOTA / IDF1 / MOTA):
  - SORT: 58.4 / 69.9 / 67.2
  - ByteTrack: 60.1 / 73.2 / 74.1
  - OC-SORT: 61.9 / 76.4 / 76.0 [roboflow]
- On DanceTrack, a benchmark with look-alike people that is closer to "pick me out of a group": ByteTrack HOTA 53.3, OC-SORT 54.1, SORT 47.2. [roboflow]
- End-to-end figures on Pi 4 (OTHER BOARD):
  - NanoDet + ByteTrack (ncnn): **11.8 FPS**
  - YoloX + ByteTrack: 7.2 FPS
  - TFLite + ByteTrack: 24.6 FPS [qe-nanotrack]
- MaixCAM ships a native `maix.tracker.ByteTracker` in MaixPy. [maix-track]

### 2c. Re-identification ("lock onto me")

| Method | Cost | Accuracy | Label | Source |
|---|---|---|---|---|
| OSNet x0.25 | 0.2 M params, 82.3 M mult-adds (input 256×128) | Market1501 rank-1 92.2 %, mAP 77.8 % | MEASURED (paper) | Zhou et al. 2019 [osnet] |
| OSNet x0.25 on Zero 2 W | ~40-60 ms per crop | – | ESTIMATE (82 M MACs vs MobileNetV2 at ~300 M MACs, which takes 147 ms on Zero 2 W ncnn; not measured) | – |
| YoutuReID (OpenCV Zoo) | Pi 4B 478.89 ms | – | OTHER BOARD (too heavy) | [zoo] |
| Hue-Saturation (HS) colour histogram of torso and legs, compared with Bhattacharyya distance | Histogram on MaixCAM: 10.9 ms (OpenMV-style) / 1 ms (OpenCV) at 320×240 full frame | no benchmark accuracy | OTHER BOARD; a crop costs less | MaixPy README [maixpy] |

**Suggested "lock onto me" logic.** At lock time, store an HS histogram of the clothing and, optionally, an OSNet-x0.25 embedding. Keep following the ByteTrack/OC-SORT track ID while it exists. Run re-ID only when the track is lost or two person tracks overlap.

---

## 3. NPU boards

| Board | NPU (vendor figure) | Measured detector FPS | Label | Camera interface | Linux | MAVLink (pymavlink / MAVSDK) | Mass / price |
|---|---|---|---|---|---|---|---|
| **Radxa Zero 3W** (RK3566, 4×A55 up to 1.6 GHz, 1/2/4/8 GB LPDDR4, Wi-Fi 6, 65×30 mm) [radxa] | RK3566 NPU (0.8 TOPS figure not in the doc I could read, UNCONFIRMED) | **RKNN Model Zoo, RK3566/RK3568 column, INT8, 640×640, inference only:** YOLOv5n 41.7, YOLOv8n 35.1, YOLO11n 22.6, YOLOv5s 20.1 FPS [rknn-zoo]. Qengineering: YOLOv8n 18.2, YOLOv5n 14.8 FPS on the "RK3566/682 NPU" column [qe-v8]. CPU ncnn: yolo-fastestv2 37.7 FPS [ncnn] | MEASURED on RK3566 (same SoC; the zoo measured on a Rockchip reference board at maximum NPU frequency) | 1× 4-lane MIPI CSI, 22-pin 0.5 mm [radxa]. Pi Camera Module 3 compatibility UNCONFIRMED | Radxa OS (Debian) [radxa] | Full Debian on arm64, so pymavlink works; MAVSDK has Linux builds (not verified for this board). Note: MAVSDK Offboard is written for PX4's Offboard mode [mavsdk] | UNCONFIRMED |
| **Luckfox Pico Max / Pico Ultra** (RV1106) [luckfox] | 0.5 / 1 TOPS (user-supplied; README only says the NPU clock was raised on RV1106G3) | **No published YOLO FPS found.** RKNN zoo supports yolov5/yolov8/yolo11/yolov10 on RV1103/RV1106, but its FPS table has no RV1106 column [rknn-zoo] | UNCONFIRMED | Official demos use the SC3336 camera over MIPI [luckfox-mpi] | Buildroot (uclibc) by default; Ubuntu images also exist (UNCONFIRMED) | uclibc Buildroot complicates Python packages; a C MAVLink library over UART is the safe path (inferred) | UNCONFIRMED |
| **Sipeed MaixCAM** (SG2002: 1 GHz C906 Linux core plus an optional 1 GHz A53, 700 MHz C906 RTOS core, 256 MB DDR3) [maixcam] | 1 TOPS INT8 | **YOLO11n: 320×320 at 95 FPS, 320×224 at 120 FPS, 640×640 at 23 FPS. YOLOv5s: 320×256 at 70 FPS. YOLOv8n: 640×640 at 23 FPS** (forward pass only) [maixpy] | MEASURED (vendor) | Bundled 4 MP GC4653 or OS04A10, 4-lane MIPI CSI 22-pin [maixcam] | Buildroot plus MaixPy (Python 3) [maixpy] | UART available. pymavlink is pure Python and should install with pip, but this is UNCONFIRMED on MaixCAM | UNCONFIRMED (includes screen and case; a screenless version exists) [maixpy-docs] |
| **Milk-V Duo S** (SG2000 = cv1813h) [milkv] | Same SG200x TPU family as MaixCAM; per-board TOPS UNCONFIRMED | TPU YOLO FPS not found. CPU-only ncnn on SG2000 (C906, 1 thread): yolo-fastestv2 190.96 ms (5.2 FPS), nanodet_m 549.81 ms [ncnn] | CPU MEASURED; TPU UNCONFIRMED. MaixCAM's SG2002 numbers are the closest proxy (OTHER BOARD) | MIPI CSI (details UNCONFIRMED) | Buildroot SDK [milkv] | UART / pymavlink plausible, UNCONFIRMED | UNCONFIRMED |
| Rockchip RV1103B | – | none found | UNCONFIRMED | – | – | – | – |
| OpenMV | – | not researched (budget ran out) | – | – | – | – | – |
| Raspberry Pi **AI Camera** (Sony IMX500, runs the network on the sensor) | on-sensor | Docs show MobileNet-SSD and PoseNet running "directly on the AI Camera" at `--framerate 30`. They say it works "with minor changes" on Zero 2 W [rpi-aicam]. Measured Zero 2 W FPS not found | UNCONFIRMED FPS | CSI | Raspberry Pi OS | yes (Pi) | **6 g**, 25×24×11.9 mm, 66° HFOV [rpi-camhw] |

**RKNN note.** The RKNN Model Zoo FPS is at 640×640 and leaves out pre- and post-processing [rknn-zoo]. At 320×320, compute is about ¼, so expect well over the 640 figures. That is an ESTIMATE; NPU efficiency at small inputs is not linear.

---

## 4. Recommended pipeline for Wisp

### 4a. Recommendation

**Primary: Radxa Zero 3W + RKNN YOLOv8n (or YOLOv5n) at 320×320 or 416×416, INT8 + ByteTrack (or OC-SORT) + HS-histogram re-ID.**
- Why: RK3566 NPU inference is measured at 35 FPS for YOLOv8n and 41.7 FPS for YOLOv5n at 640 [rknn-zoo]. That leaves plenty of headroom to run the detector on every frame at 15-30 Hz, so no visual tracker is needed. The four A55 cores handle ByteTrack, the Kalman filter and MAVLink with ease. It runs full Debian. Its 65×30 mm footprint matches the Pi Zero.
- Expected detection rate: **≥20-30 Hz** end-to-end at 320-416. This is an ESTIMATE: measured 35 FPS inference at 640, with input reduced and pre/post-processing added.
- Risks: board mass UNCONFIRMED; camera driver support for the chosen sensor UNCONFIRMED.

**Alternative (integrated, very fast NPU): Sipeed MaixCAM + YOLO11n 320×224 (120 FPS forward, vendor figure) + built-in `maix.tracker.ByteTracker`.**
- Weaknesses: only 256 MB RAM, a weak single C906 Linux core for Python glue, and pymavlink support UNCONFIRMED.

**Fallback (CPU only): Pi Zero 2 W + Yolo-FastestV2 (ncnn, 352) at 12.3 FPS inference, measured [ncnn].**
- Expect about 6-10 Hz end-to-end (ESTIMATE).
- Add a Kalman/ByteTrack association and, optionally, MOSSE/KCF on a downscaled ROI between detections.
- Weakness: Yolo-FastestV2's COCO accuracy is low (24.1 mAP@0.5), so fine-tune it on person-only data shot from drone height. NanoDet-m (6 FPS, measured) is the more accurate CPU option.

### 4b. Rates and latency budget (design targets, not measurements)

| Stage | Pi Zero 2 W fallback | Radxa Zero 3W (NPU) |
|---|---|---|
| Camera | 30 fps, 640×480 or lower, from a 102° wide camera | 30 fps |
| Detector | 8-12 Hz (Yolo-FastestV2 352: 81 ms inference) | 30 Hz (YOLOv8n 320-416) |
| Tracker | MOSSE/KCF on ROI at 30 Hz, or Kalman prediction only | ByteTrack on every detection |
| Re-ID | HS histogram per detection; OSNet only on loss | same |
| Command output to ArduPilot | 10-20 Hz | 20 Hz |
| Glass-to-command latency target | < 200 ms | < 80 ms |

Latency adds up as frame period plus capture, inference, post-processing and serial transfer. Keep the camera buffer depth at 1 so the detector never runs on stale frames.

### 4c. From pixels to a follow command

1. **Bearing.** First compute the focal length in pixels: f_x = (W/2) / tan(HFOV/2). The horizontal bearing is then ψ_err = atan((c_x − W/2) / f_x). Use the same method vertically with VFOV. With the Camera Module 3 Wide (HFOV 102°, VFOV 67° [rpi-camhw]), f_x ≈ 0.40·W. This is arithmetic from the published FOV.
2. **Range** (combine two estimates):
   - *Box height:* d ≈ H_person · f_y / h_px, where H_person is your measured standing height. Box height breaks down when you crouch, are partly occluded, or the camera pitch is steep.
   - *Ground-plane:* use the bottom edge of the box (your feet), the camera pitch and altitude: d = h_agl / tan(pitch_down + angle_of_feet_below_center). This is more robust at follow-me heights of 3-10 m, provided altitude above ground level (AGL) is reliable from a rangefinder, or from barometer altitude above home on flat ground.
3. **Filter.** Run a constant-velocity Kalman filter on the target position in North-East-Down (NED) coordinates. Each measurement comes from drone pose + bearing + range. The filter gives a smoothed target velocity for feed-forward and covers missed detections; coast for at most about 1 s, then hold position.
4. **Send to ArduPilot.** Two options:
   - **Option A (simple, robust): Guided mode velocity.** Stream `SET_POSITION_TARGET_LOCAL_NED` with velocity and yaw rate.
     - Use the velocity type mask 0x0DC7 / 3527. `MAV_FRAME_BODY_OFFSET_NED` (9) is body-relative, so forward = closing speed and yaw_rate = k·ψ_err.
     - ArduPilot docs: velocity commands "should be re-sent every second (the vehicle will stop after 3 seconds if no command is received)". [ap-guided]
     - Command forward velocity = k_d·(d − d_set) + v_target_feedforward.
   - **Option B (reuse ArduPilot's estimator): Follow mode.** The companion converts the filtered target into latitude/longitude/altitude/velocity. It then publishes `FOLLOW_TARGET` (preferred) or `GLOBAL_POSITION_INT` under its own MAVLink system id. ArduPilot sets `FOLL_SYSID` to that id.
     - Tune with `FOLL_OFS_*`, `FOLL_OFS_TYPE=1` (offset relative to heading), `FOLL_YAW_BEHAVE`, `FOLL_POS_P`, the `FOLL_ACCEL_*`/`FOLL_JERK_*` limits and `FOLL_TIMEOUT`. [ap-follow]
     - Current master ignores `GLOBAL_POSITION_INT` once `FOLLOW_TARGET` is being used, and `FOLL_SYSID=0` now means "follow nothing" [ap-follow-src].
     - Option B gets ArduPilot's acceleration and jerk limiting for free, but its accuracy depends on the vision range estimate.
5. **Tap to lock from a ground control station (optional).** ArduPilot accepts `MAV_CMD_CAMERA_TRACK_POINT`, `MAV_CMD_CAMERA_TRACK_RECTANGLE` and `MAV_CMD_CAMERA_STOP_TRACKING` [ap-camera-src].
   - Mount backends that implement tracking in current master: **ViewPro and Topotek only; SiYi has no `set_tracking`** [ap-mount-src].
   - Copter 4.5.0 release notes: "Image tracking support (ViewPro only)" [ap-rn].
   - With the MAVLink Camera v2 backend, ArduPilot forwards `CAMERA_TRACKING_IMAGE_STATUS` from a MAVLink camera to the ground station [ap-camv2-src]. So the companion can present itself as a MAVLink camera that accepts tap-to-lock and reports the tracked box.
   - Example script: `fake_camera_tracking.lua` [ap-faketrack].
6. **MAVSDK.** Its Offboard plugin is built around PX4's Offboard mode, supports velocity setpoints only, and resends at 20 Hz [mavsdk]. For ArduPilot, **pymavlink (or MAVSDK's raw MAVLink passthrough)** sending Guided-mode setpoints is the better-trodden path.
7. **Prior art.** ArduPilot GSoC projects include "Visual Follow-Me" (2024) and "Camera and Gimbal enhancements" (2023) [ap-gsoc]. I could not retrieve the project write-ups on discuss.ardupilot.org, so their architecture is UNCONFIRMED.
8. **Gimbal-camera route.** SiYi/ViewPro tracking cameras put the tracking on the gimbal. They are likely too heavy for a sub-250 g airframe (mass UNCONFIRMED), and SiYi tracking is not wired into ArduPilot (see item 5).

---

## 5. Camera modules

| Camera | Mass | Size | HFOV / VFOV | Notes | Source |
|---|---|---|---|---|---|
| Raspberry Pi Camera Module 3 | **4 g** | ~25×24×11.5 mm | 66° / 41° | IMX708, autofocus | [rpi-camhw] |
| **Raspberry Pi Camera Module 3 Wide** | **4 g** | ~25×24×12.4 mm | **102° / 67°** | 2.75 mm, F2.2. **Best fit for follow-me**: keeps you in frame during aggressive yaw | [rpi-camhw] |
| Raspberry Pi Camera Module 2 | 3 g | ~25×24×9 mm | 62.2° / 48.8° | – | [rpi-camhw] |
| Raspberry Pi AI Camera (IMX500) | 6 g | 25×24×11.9 mm | 66° / 52.3° | on-sensor MobileNet-SSD; Zero 2 W supported "with minor changes" | [rpi-camhw], [rpi-aicam] |
| Arducam lightweight modules | UNCONFIRMED | – | – | not verified (site blocked) | – |
| Luckfox SC3336 | UNCONFIRMED | – | UNCONFIRMED | the camera used by Luckfox's RTSP/YOLO demos | [luckfox-mpi] |
| MaixCAM GC4653 / OS04A10 | UNCONFIRMED | – | UNCONFIRMED | 4 MP, 4-lane MIPI, 22-pin | [maixcam] |

---

## Sources (all seen 2026-10-26)

| Key | URL | What it supports |
|---|---|---|
| ncnn | https://github.com/Tencent/ncnn/blob/master/benchmark/README.md (raw copy fetched) and https://github.com/Tencent/ncnn/blob/master/benchmark/benchncnn.cpp | Zero 2 W, Pi 4, Radxa Zero 3W, SG2000 latency tables; model input sizes |
| qe-v8 | https://github.com/Qengineering/YoloV8-ncnn-Raspberry-Pi-4 and https://github.com/Qengineering/YoloFastestV2-ncnn-Raspberry-Pi-4 | Pi 4 / Pi 5 / RK3566-NPU FPS table for NanoDet, PicoDet, YOLO family, plus mAP column |
| qe-tfl | https://qengineering.eu/install-tensorflow-2-lite-on-raspberry-64-os.html | Pi 4 TFLite MobileNet-SSD 26.8 FPS, PoseNet 10.3 FPS |
| qe-zero | https://qengineering.eu/install-64-os-on-raspberry-pi-zero-2.html | Zero 2 W 32/64-bit notes (numbers only in charts) |
| qe-nanotrack | https://github.com/Qengineering/NanoDet-Tracking-ncnn-RPi_64-bit | NanoDet + ByteTrack 11.8 FPS on Pi 4 |
| qe-examples | https://qengineering.eu/deep-learning-examples-on-raspberry-32-64-os.html | ByteTrack with YoloX at 7.15-24.6 FPS; YoloCam runs on Zero 2W |
| yolocam | https://awesome.ecosyste.ms/projects/github.com%2Fqengineering%2Fyolocam | YoloCam FPS on Zero 2W / 3B+ / Pi 4 |
| dog-qiuqiu | https://github.com/dog-qiuqiu/Yolo-FastestV2 | Yolo-FastestV2 / V1.1 mAP@0.5, FLOPs, params (Kirin 990 timings) |
| nanodet | https://github.com/DefTruth/nanodet (mirror of RangiLyu/nanodet README) | NanoDet-m / Plus-m mAP, Kirin 980 latency, YOLOv5n 28.4 |
| picodet | https://openharmony.gitee.com/kingzuos/PaddleDetection/blob/release/2.6/configs/picodet/README.md and https://ar5iv.labs.arxiv.org/html/2111.00902 | PicoDet XS/S/M/L mAP, latency on Snapdragon 865 |
| effdet | https://developers.google.com/edge/litert/libraries/modify/object_detection | EfficientDet-Lite0 25.69 AP, 37 ms on Pixel 4 |
| mlsys | https://mlsysbook.ai/kits/contents/raspi/object_detection/object_detection.html | "Raspi-Zero" SSD-MobileNetV2 ~600 ms, YOLOv8n ~1 FPS; FOMO 8 ms on Pi 4 |
| buzz | https://www.hackster.io/518000/buzztech-machine-learning-at-the-edge-07c951 | YOLOv8n NCNN ~730 ms on Zero 2 W |
| habr | https://habr.com/en/articles/822917 | YOLOv8n NCNN/ONNX FPS on Pi 4 |
| ultra-rpi | https://docs.ultralytics.com/guides/raspberry-pi | YOLO11n 6.79 FPS (Pi 5, ONNX), YOLO26n NCNN 67 ms on Pi 5; mAP 39.5 |
| movenet | https://www.tensorflow.org/lite/examples/pose_estimation/overview and https://blog.tensorflow.org/2021/08/pose-estimation-and-classification-on-edge-devices-with-MoveNet-and-TensorFlow-Lite.html | MoveNet / PoseNet latency on Pi 4 and mAP |
| fomo | https://docs.edgeimpulse.com/nordic/edge-impulse-studio/learning-blocks/object-detection/fomo-object-detection-for-constrained-devices and https://www.cnx-software.com/2022/04/18/fomo-faster-objects-more-objects-real-time-object-detection-embedded-systems/ | FOMO 60 fps on Pi 4 claim; centroid-only output |
| zoo | https://github.com/opencv/opencv_zoo/blob/main/benchmark/README.md (raw copy fetched) | Pi 4B / RV1126 latency for VitTrack, MPPersonDet, NanoDet, YoutuReID (OpenCV 4.10) |
| vit | https://huggingface.co/opencv/opencv_zoo/blob/8a1a70cce93b53bd55cebced420389736ccb27e7/models/object_tracking_vittrack/README.md | ViT tracker vs NanoTrack speed and LaSOT accuracy; needs OpenCV > 4.8.0 |
| nano | https://docs.opencv.org/4.x/d8/d69/classcv_1_1TrackerNano.html | TrackerNano model size about 1.9 MB, two models |
| darvishi | https://sciarena.com/storage/models/article/qsUEQ6r5ctgGUtrfc2jcseg7W7qxqG748SOgFni8Mp9x6JfxwZKu5u5gPvl7/comparison-of-api-trackers-in-opencv-using-raspberry-pi-hardware.pdf | OpenCV tracker FPS on Pi 3B (Darvishi, Spec. J. Electron. Comput. Sci. 2020) |
| roboflow | https://trackers.roboflow.com/latest/trackers/comparison/ | SORT / ByteTrack / OC-SORT HOTA, IDF1, MOTA; qualitative speed |
| osnet | https://arxiv.org/pdf/1905.00953 | OSNet x0.25 params, mult-adds, Market1501 accuracy |
| rknn-zoo | https://github.com/airockchip/rknn_model_zoo (README, raw copy fetched; also tags v1.6.0-v2.3.0) | RK3566 NPU FPS for YOLOv5n/v8n/11n; RV1106 support, no RV1106 FPS |
| radxa | https://github.com/radxa-docs/docs/blob/main/docs/zero/zero3/README.md | Radxa Zero 3W specs (RK3566, A55 1.6 GHz, MIPI CSI 4-lane 22-pin, 65×30 mm) |
| luckfox | https://github.com/LuckfoxTECH/luckfox-pico (README) | RV1106 board list (Pico Max/Ultra); NPU frequency change |
| luckfox-mpi | https://github.com/LuckfoxTECH/luckfox_pico_rkmpi_example and https://github.com/LuckfoxTECH/luckfox_pico_rknn_example | YOLOv5 demo on RV1106 with SC3336 camera; no FPS |
| maixpy | https://github.com/sipeed/MaixPy (README performance table) | MaixCAM YOLO11n / YOLOv5s / YOLOv8n FPS; histogram timings; SG2002 specs |
| maixpy-docs | https://github.com/sipeed/MaixPy/blob/main/docs/doc/en/vision/yolov5.md and https://github.com/sipeed/MaixPy/blob/main/docs/doc/en/README.md | MaixCAM default 320×224 input; YOLO11/26 support; screenless version |
| maix-track | https://github.com/sipeed/MaixPy/blob/main/docs/doc/en/vision/object_track.md | Native ByteTracker on MaixCAM |
| maixcam | https://github.com/sipeed/sipeed_wiki/blob/main/docs/hardware/en/maixcam/maixcam.md | MaixCAM hardware table (NPU 1 TOPS, 256 MB, camera sensors) |
| milkv | https://github.com/milkv-duo/duo-buildroot-sdk (README) | Duo S = cv1813h (SG2000); Buildroot SDK |
| rpi-camhw | https://github.com/raspberrypi/documentation/blob/develop/documentation/asciidoc/accessories/camera/hardware_specification.adoc | Camera mass, size, FOV (CM2, CM3, CM3 Wide, AI Camera) |
| rpi-aicam | https://github.com/raspberrypi/documentation/tree/develop/documentation/asciidoc/accessories/ai-camera | AI Camera on-sensor MobileNet-SSD; Zero 2 W support |
| ap-follow | https://github.com/ArduPilot/ardupilot_wiki/blob/master/copter/source/docs/follow-mode.rst | Follow mode, FOLLOW_TARGET / GLOBAL_POSITION_INT, FOLL_* parameters |
| ap-follow-src | https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Follow/AP_Follow.cpp | Message handling (FOLLOW_TARGET takes priority) |
| ap-guided | https://github.com/ArduPilot/ardupilot_wiki/blob/master/dev/source/docs/copter-commands-in-guided-mode.rst | SET_POSITION_TARGET_LOCAL_NED frames, type masks, 3 s timeout |
| ap-camera-src | https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Camera/AP_Camera.cpp | CAMERA_TRACK_POINT / RECTANGLE / STOP_TRACKING handling |
| ap-camv2-src | https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Camera/AP_Camera_MAVLinkCamV2.cpp | Forwards CAMERA_TRACKING_IMAGE_STATUS |
| ap-mount-src | https://github.com/ArduPilot/ardupilot/tree/master/libraries/AP_Mount | set_tracking implemented only in Viewpro and Topotek backends |
| ap-rn | https://github.com/ArduPilot/ardupilot/blob/master/ArduCopter/ReleaseNotes.txt | 4.5.0: "Image tracking support (ViewPro only)" |
| ap-faketrack | https://github.com/ArduPilot/ardupilot/blob/master/libraries/AP_Scripting/examples/fake_camera_tracking.lua | Example camera-tracking backend in Lua |
| ap-gsoc | https://github.com/ArduPilot/ardupilot_wiki/blob/master/dev/source/docs/gsoc-ideas-list.rst | GSoC 2024 "Visual Follow-Me" and 2023 "Camera and Gimbal enhancements" exist |
| mavsdk | https://github.com/mavlink/MAVSDK/blob/main/docs/en/cpp/guide/offboard.md | Offboard plugin: PX4 Offboard mode, velocity setpoints only, 20 Hz resend |
