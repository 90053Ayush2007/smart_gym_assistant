# 🏋️ Smart Gym Assistant
**Applied AI Course · Applied Roots**

A real-time AI gym coach using **BlazePose (MediaPipe)** that:
- Detects your body pose via webcam or phone camera
- Computes joint angles and compares them to ideal exercise form
- Counts reps automatically using a finite-state-machine
- Streams live annotated video to your laptop/TV browser
- Gives real-time visual + text corrections

---

## 📁 Project Structure

```
smart_gym_assistant/
├── app.py                        ← Flask + SocketIO server (laptop/TV UI)
├── run_webcam.py                 ← Standalone OpenCV window (no browser)
├── requirements.txt
├── models/
│   └── blazepose_processor.py   ← BlazePose inference + CV2 HUD overlay
├── utils/
│   ├── pose_angles.py           ← Joint angle computation from 33 landmarks
│   ├── rep_counter.py           ← FSM-based rep counter
│   └── pose_correction.py      ← Form score + feedback engine
└── exercises/
    └── exercise_db.py           ← Exercise database (8 exercises)
```

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2a. Webcam-only mode (simplest)
```bash
python run_webcam.py --exercise bicep_curl
```
Keys: `1-8` switch exercise · `r` reset reps · `SPACE` pause · `q` quit

### 2b. Browser/TV mode (Flask server)
```bash
python app.py --exercise squat
```
Then open:
- **Laptop/TV:** `http://localhost:5000`
- **Phone camera:** `http://<your-laptop-ip>:5000/mobile`

---

## 📱 Phone as Camera (from PDF Slide 5–6)

1. Connect phone and laptop to the **same WiFi**
2. Run `python app.py`
3. On your phone, open `http://<laptop-ip>:5000/mobile`
4. Your phone camera streams frames to the laptop for processing
5. Watch the annotated feed on your laptop/TV at `http://localhost:5000`

This replicates the exact architecture from the PDF:
> *Smartphone (Camera + WiFi) → TV/Laptop (Screen + AI Processing)*

---

## 🧠 Model: BlazePose (MediaPipe)

**Why BlazePose over OpenPose?** (PDF Slide 34)

| Model | FPS | Yoga PCK@0.2 | Target Hardware |
|-------|-----|--------------|-----------------|
| OpenPose (body) | 0.4 | 83.4 | Desktop 20-core CPU |
| BlazePose Full | 10 | **84.5** | Single-core Android |
| BlazePose Lite | 31 | 77.6 | Single-core Android |

BlazePose is **more accurate on fitness movements AND 25× faster** on mobile hardware. Perfect for our use case.

### BlazePose Architecture (PDF Slide 35–36)

```
Input RGB Image (256×256)
        ↓
  Face Detector        ← detects person on frame #1
  with pose alignment  ← subsequent frames skip detection
        ↓
  Encoder (Hourglass)  ← MobileNetV2-like backbone
  128×128×16 → 8×8×192
        ↓
  Decoder              ← skip connections (U-Net style)
        ↓
  Branch A: Heat maps + Offset maps (64×64×99)
  Branch B: 33×3 keypoints + visibility
        ↓
  33 3D Landmarks (x, y, z, visibility)
```

The model outputs **33 keypoints** (vs OpenPose's 18), including finger joints and feet, giving finer-grained angle computation.

### Our Pipeline (PDF Slide 8)

```
Camera Frame
    → BlazePose Pose Estimation  (33 landmarks)
    → Joint Angle Computation    (pose_angles.py)
    → Pose Match                 (compare θ_obs vs θ_target)
    → Pose Correction            (form_score, corrections)
    → Rep Counter FSM            (DOWN → UP → DOWN = 1 rep)
    → A/V Feedback               (HUD overlay + browser UI)
```

---

## 📐 Joint Angles (PDF Slide 40–41)

Pose matching works by comparing **observed joint angles** to **stored ideal angles** for each exercise. This is exactly how Google ML Kit classifies poses (slide 41 — "Breaking a pose into angles").

For each joint angle θ at keypoint B between points A-B-C:

```python
θ = arccos( (BA · BC) / (|BA| × |BC|) )
```

### Joints Tracked per Exercise

| Exercise | Key Joints |
|----------|-----------|
| Bicep Curl | L/R Elbow, L/R Shoulder, Trunk |
| Squat | L/R Knee, L/R Hip, Trunk |
| Push-Up | L/R Elbow, L/R Shoulder, Trunk |
| Shoulder Press | L/R Elbow, L/R Shoulder, Trunk |
| Lateral Raise | L/R Shoulder, Trunk |
| Deadlift | L/R Hip, L/R Knee, Trunk |
| Lunge | L/R Knee, L/R Hip, Trunk |
| Plank | L/R Elbow, L/R Hip, Trunk |

---

## 🔢 Rep Counter FSM (PDF Slide 42)

```
WAITING ──(angle ≥ down_threshold)──► DOWN
  DOWN  ──(angle ≤ up_threshold)───► UP
  UP    ──(angle ≥ down_threshold)──► DOWN  ← REP COUNTED!
```

Example for Bicep Curl (tracking left elbow):
- `down_threshold = 150°` (arm extended)
- `up_threshold   = 55°`  (arm curled)

---

## 📊 Datasets Used to Train BlazePose

BlazePose was trained and evaluated on these datasets (PDF Slide 29):

### 1. COCO Keypoints 2018
- **URL:** https://cocodataset.org/#keypoints-2018
- **Size:** ~200K person instances, 17 keypoints each
- **Metric:** OKS (Object Keypoint Similarity), AP/AR
- Used for upper-body and multi-person keypoint detection

### 2. MPII Human Pose (Max Planck Institute)
- **URL:** http://human-pose.mpi-inf.mpg.de
- **Size:** ~25K images, ~40K annotated people, 16 keypoints
- **Metric:** PCKh@0.5 (% correct keypoints within 50% of head bone length)
- Single and multi-person; diverse activities

### 3. LSP / VGG Pose Evaluation
- **URL:** https://www.robots.ox.ac.uk/~vgg/data/pose_evaluation/
- **Size:** ~10K images, 14 joint annotations
- Sport activities; used for PCK@0.2 evaluation

### 4. BlazePose's Own Fitness Dataset (Google, 2020)
- **Paper:** arxiv.org/pdf/2006.10204.pdf
- Yoga + Aerobics videos, 33 keypoint annotations
- Specifically collected for fitness/sports poses
- Evaluated with PCK@0.2 on AR (Aerobics) and Yoga splits
- **This is why BlazePose excels at gym exercises**

### 5. Additional (for fine-tuning your own classifier)
| Dataset | URL | Notes |
|---------|-----|-------|
| Yoga-82 | https://sites.google.com/view/yoga-82 | 82 yoga poses |
| GymAction | Search "GymAction dataset" | Gym exercise videos |
| FitVid | Search "FitVid dataset" | Fitness instructional |

---

## ⚙️ Configuration

### BlazePose Model Complexity
Set in `GymPoseProcessor(model_complexity=N)`:
- `0` = Lite  (fastest, ~31 FPS on phone)
- `1` = Full  (balanced, ~10 FPS)  ← **default**
- `2` = Heavy (most accurate, slower)

### Adding Custom Exercises
Edit `exercises/exercise_db.py`:

```python
EXERCISES["my_exercise"] = {
    "name": "My Exercise",
    "muscles": ["target muscle"],
    "joints_to_check": ["left_knee", "right_knee"],
    "target_angles": {
        "left_knee_down": 90,   # angle at bottom of movement
        "left_knee_up":  170,   # angle at top of movement
    },
    "tolerance_deg": {"left_knee": 15},
    "rep_counter": {
        "joint": "left_knee",
        "up_threshold":   160,  # standing
        "down_threshold": 110,  # parallel
    },
    "corrections": {
        "left_knee": {
            "too_high": "Go deeper",
            "too_low":  "Don't go past toes",
        }
    },
    "tips": ["Tip 1", "Tip 2"],
}
```

---

## 🔑 Key Challenges & Solutions (PDF Slide 9)

| Challenge | Solution |
|-----------|----------|
| Latency | BlazePose Lite at 30+ FPS; local processing |
| Compute (>30fps) | model_complexity=1 balances speed/accuracy |
| Smooth TV-connect | MJPEG stream via Flask; SocketIO for JSON feedback |
| Phone → TV | `/mobile` page streams JPEG frames via HTTP POST |

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `mediapipe` | BlazePose inference (Google) |
| `opencv-python` | Camera capture, frame processing, drawing |
| `flask` | Web server for browser UI |
| `flask-socketio` | Real-time feedback push to browser |
| `numpy` | Vector math for angle computation |
| `scipy` | Signal processing (optional smoothing) |

---

## 🎯 Performance Tips

1. **Ensure full body is visible** – BlazePose needs to detect your face first
2. **Good lighting** – BlazePose is a vision model; dark gyms reduce accuracy
3. **Camera at ~2–3m distance** – Full body should fit in frame
4. **Use `model_complexity=0`** (Lite) on older laptops for better FPS
5. **Phone placement** – Mount phone at waist height, perpendicular to body

---

## 📚 References

- BlazePose paper: https://arxiv.org/pdf/2006.10204.pdf
- MediaPipe Pose: https://google.github.io/mediapipe/solutions/pose
- Google ML Kit Pose: https://developers.google.com/ml-kit/vision/pose-detection
- OpenPose CMU: https://github.com/CMU-Perceptual-Computing-Lab/openpose
- Papers with Code (Pose): https://paperswithcode.com/task/pose-estimation
- Pose classification guide: https://developers.google.com/ml-kit/vision/pose-detection/classifying-poses
