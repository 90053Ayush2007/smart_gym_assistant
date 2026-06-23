"""
app.py
------
Flask + SocketIO server for the Smart Gym Assistant.

Architecture (from PDF slide 6):
  Smartphone (camera) ──HDMI/WiFi──► TV / Laptop
                                        └─ This server runs here

The server:
  1. Opens your webcam (or receives MJPEG from phone via /mobile_feed)
  2. Runs BlazePose on each frame
  3. Streams annotated frames as MJPEG  →  browser on the laptop/TV
  4. Sends JSON feedback via SocketIO   →  browser UI

Run:
  python app.py

Then open:  http://localhost:5000
From phone: http://<your-laptop-ip>:5000/mobile
"""

import os
import cv2
import base64
import threading
import time
from flask import Flask, Response, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit

# Local imports
import sys
sys.path.insert(0, os.path.dirname(__file__))
from models.blazepose_processor import GymPoseProcessor
from exercises.exercise_db      import list_exercises

# ── App setup ────────────────────────────────────────────────
app    = Flask(__name__)
app.config["SECRET_KEY"] = "gym_assistant_2024"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Global state ─────────────────────────────────────────────
processor   = GymPoseProcessor(exercise_key="bicep_curl", model_complexity=1)
camera      = None
camera_lock = threading.Lock()
frame_lock  = threading.Lock()
current_frame_jpg = None   # latest JPEG bytes for MJPEG stream
streaming   = False
USE_MOBILE_CAMERA = False  # True when phone sends frames


# ─────────────────────────────────────────────────────────────
#  Camera helpers
# ─────────────────────────────────────────────────────────────

def open_camera(index: int = 0):
    global camera
    with camera_lock:
        if camera is not None:
            camera.release()
        cam = cv2.VideoCapture(index)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cam.set(cv2.CAP_PROP_FPS,          30)
        camera = cam
    return camera.isOpened()


def capture_loop():
    """Background thread: grab frames, run BlazePose, store latest JPEG."""
    global current_frame_jpg, streaming
    streaming = True

    while streaming:
        if USE_MOBILE_CAMERA:
            time.sleep(0.01)
            continue

        with camera_lock:
            if camera is None or not camera.isOpened():
                time.sleep(0.1)
                continue
            ret, frame = camera.read()

        if not ret:
            time.sleep(0.05)
            continue

        # Flip for mirror view (natural for user facing camera)
        frame = cv2.flip(frame, 1)

        annotated, feedback = processor.process_frame(frame)

        # Encode to JPEG
        _, jpg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        with frame_lock:
            current_frame_jpg = jpg.tobytes()

        # Push feedback JSON to all connected browsers
        socketio.emit("feedback", feedback)
        time.sleep(0.001)


def generate_mjpeg():
    """Generator for the MJPEG stream endpoint."""
    boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
    while True:
        with frame_lock:
            jpg = current_frame_jpg
        if jpg:
            yield boundary + jpg + b"\r\n"
        time.sleep(0.033)   # ~30 fps cap


# ─────────────────────────────────────────────────────────────
#  Routes
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    exercises = list_exercises()
    return render_template_string(MAIN_PAGE_HTML, exercises=exercises)


@app.route("/video_feed")
def video_feed():
    return Response(
        generate_mjpeg(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/mobile")
def mobile():
    """Page shown on the phone – just a camera feed that POSTs frames."""
    return render_template_string(MOBILE_PAGE_HTML)


@app.route("/mobile_feed", methods=["POST"])
def mobile_feed():
    """
    Phone posts raw JPEG bytes here.
    Server runs BlazePose and returns annotated JPEG.
    """
    global current_frame_jpg, USE_MOBILE_CAMERA
    USE_MOBILE_CAMERA = True

    data  = request.data
    nparr = __import__("numpy").frombuffer(data, __import__("numpy").uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        return Response(status=400)

    frame = cv2.flip(frame, 1)
    annotated, feedback = processor.process_frame(frame)
    socketio.emit("feedback", feedback)

    _, jpg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
    with frame_lock:
        current_frame_jpg = jpg.tobytes()

    return Response(jpg.tobytes(), mimetype="image/jpeg")


@app.route("/api/exercises")
def api_exercises():
    return jsonify(list_exercises())


@app.route("/api/set_exercise", methods=["POST"])
def api_set_exercise():
    key = request.json.get("exercise")
    processor.change_exercise(key)
    processor.reset_reps()
    return jsonify({"ok": True, "exercise": key})


@app.route("/api/reset_reps", methods=["POST"])
def api_reset_reps():
    processor.reset_reps()
    return jsonify({"ok": True})


@app.route("/api/stats")
def api_stats():
    return jsonify(processor.session_stats())


# ─────────────────────────────────────────────────────────────
#  SocketIO events
# ─────────────────────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    emit("status", {"msg": "Connected to Smart Gym Assistant"})


@socketio.on("set_exercise")
def on_set_exercise(data):
    key = data.get("exercise", "bicep_curl")
    processor.change_exercise(key)
    processor.reset_reps()
    emit("exercise_changed", {"exercise": key})


@socketio.on("reset_reps")
def on_reset_reps():
    processor.reset_reps()
    emit("reps_reset", {})


# ─────────────────────────────────────────────────────────────
#  HTML Templates (self-contained – no extra files needed)
# ─────────────────────────────────────────────────────────────

MAIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Gym Assistant</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js"></script>
<style>
  :root {
    --bg:       #0a0a0a;
    --surface:  #141414;
    --accent:   #ff9f0a;
    --green:    #30d158;
    --yellow:   #ffd60a;
    --red:      #ff453a;
    --text:     #f5f5f7;
    --muted:    #6e6e73;
    --radius:   12px;
    --font:     'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--font);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ── Header ── */
  header {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px 28px;
    border-bottom: 1px solid #222;
  }
  .logo-ring {
    width: 38px; height: 38px;
    border-radius: 50%;
    background: conic-gradient(var(--accent) 0%, var(--green) 60%, var(--accent) 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }
  header h1 { font-size: 1.25rem; font-weight: 700; letter-spacing: -.3px; }
  header span { font-size: .75rem; color: var(--muted); margin-left: auto; }

  /* ── Main layout ── */
  .main {
    display: grid;
    grid-template-columns: 1fr 320px;
    gap: 18px;
    padding: 18px 28px;
    flex: 1;
  }

  /* ── Video ── */
  .video-wrap {
    position: relative;
    background: #000;
    border-radius: var(--radius);
    overflow: hidden;
    aspect-ratio: 16/9;
  }
  .video-wrap img {
    width: 100%; height: 100%;
    object-fit: cover;
    display: block;
  }
  .live-badge {
    position: absolute; top: 12px; right: 12px;
    background: var(--red);
    padding: 3px 10px; border-radius: 20px;
    font-size: .7rem; font-weight: 700; letter-spacing: .5px;
    display: flex; align-items: center; gap: 5px;
  }
  .live-dot { width: 7px; height: 7px; border-radius: 50%; background: #fff;
              animation: pulse 1.4s infinite; }
  @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.3; } }

  /* ── Side panel ── */
  .panel { display: flex; flex-direction: column; gap: 14px; }

  .card {
    background: var(--surface);
    border-radius: var(--radius);
    padding: 18px;
    border: 1px solid #222;
  }
  .card-title {
    font-size: .65rem; font-weight: 600;
    color: var(--muted); letter-spacing: 1px;
    text-transform: uppercase; margin-bottom: 10px;
  }

  /* ── Form score ── */
  .score-num {
    font-size: 3.5rem; font-weight: 800;
    line-height: 1; letter-spacing: -2px;
    transition: color .3s;
  }
  .score-bar-bg {
    height: 8px; background: #2a2a2a; border-radius: 4px;
    margin-top: 10px; overflow: hidden;
  }
  .score-bar { height: 100%; border-radius: 4px;
               transition: width .4s ease, background .3s; }

  /* ── Reps ── */
  .rep-display {
    display: flex; align-items: baseline; gap: 10px;
  }
  .rep-num {
    font-size: 4rem; font-weight: 800;
    color: var(--accent); line-height: 1;
  }
  .rep-state-pill {
    padding: 3px 10px; border-radius: 20px;
    font-size: .7rem; font-weight: 700;
    background: #222; color: var(--muted);
  }
  .rep-state-pill.up   { background: #0f3320; color: var(--green); }
  .rep-state-pill.down { background: #3a2f00; color: var(--yellow); }

  /* ── Corrections ── */
  .correction-item {
    display: flex; gap: 8px;
    font-size: .82rem; line-height: 1.4;
    padding: 8px 0;
    border-bottom: 1px solid #1e1e1e;
    color: var(--yellow);
  }
  .correction-item:last-child { border-bottom: none; }
  .correction-ok { color: var(--green); font-size: .82rem; }
  .corr-icon { flex-shrink: 0; margin-top: 1px; }

  /* ── Exercise selector ── */
  select {
    width: 100%; padding: 10px 12px;
    background: #1e1e1e; color: var(--text);
    border: 1px solid #333; border-radius: 8px;
    font-size: .9rem; appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='7'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23888' stroke-width='1.5' fill='none'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    cursor: pointer;
  }
  select:focus { outline: none; border-color: var(--accent); }

  /* ── Buttons ── */
  .btn {
    padding: 10px 18px; border-radius: 8px;
    font-size: .85rem; font-weight: 600;
    cursor: pointer; border: none;
    transition: opacity .15s;
  }
  .btn:hover { opacity: .85; }
  .btn-primary   { background: var(--accent); color: #000; }
  .btn-secondary { background: #222; color: var(--text); border: 1px solid #333; }
  .btn-row       { display: flex; gap: 8px; }

  /* ── Angles table ── */
  .angles-grid {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 6px; font-size: .78rem;
  }
  .angle-item {
    display: flex; justify-content: space-between;
    padding: 5px 8px; background: #1a1a1a;
    border-radius: 6px;
  }
  .angle-item.ok     { border-left: 3px solid var(--green); }
  .angle-item.too_high { border-left: 3px solid var(--red); }
  .angle-item.too_low  { border-left: 3px solid var(--yellow); }
  .angle-val { font-weight: 700; color: var(--accent); }

  /* ── Tips ── */
  .tip-item {
    font-size: .8rem; color: var(--muted);
    padding: 5px 0; border-bottom: 1px solid #1a1a1a;
    display: flex; gap: 6px;
  }
  .tip-item:last-child { border-bottom: none; }

  /* ── Footer ── */
  footer {
    text-align: center; padding: 12px;
    font-size: .7rem; color: var(--muted);
    border-top: 1px solid #1a1a1a;
  }
</style>
</head>
<body>

<header>
  <div class="logo-ring">💪</div>
  <h1>Smart Gym Assistant</h1>
  <span id="connection-status">Connecting…</span>
</header>

<div class="main">

  <!-- Video stream -->
  <div>
    <div class="video-wrap">
      <img id="video-feed" src="/video_feed" alt="Pose feed">
      <div class="live-badge"><div class="live-dot"></div> LIVE</div>
    </div>

    <!-- Tips row -->
    <div class="card" style="margin-top:14px;">
      <div class="card-title">💡 Exercise Tips</div>
      <div id="tips-list"></div>
    </div>
  </div>

  <!-- Side panel -->
  <div class="panel">

    <!-- Exercise picker -->
    <div class="card">
      <div class="card-title">Exercise</div>
      <select id="exercise-select">
        {% for key, name in exercises.items() %}
        <option value="{{ key }}">{{ name }}</option>
        {% endfor %}
      </select>
      <div class="btn-row" style="margin-top:10px;">
        <button class="btn btn-primary" onclick="setExercise()">Set Exercise</button>
        <button class="btn btn-secondary" onclick="resetReps()">Reset Reps</button>
      </div>
    </div>

    <!-- Form score -->
    <div class="card">
      <div class="card-title">Form Score</div>
      <div class="score-num" id="score-num">—</div>
      <div class="score-bar-bg">
        <div class="score-bar" id="score-bar" style="width:0%;"></div>
      </div>
    </div>

    <!-- Rep counter -->
    <div class="card">
      <div class="card-title">Reps</div>
      <div class="rep-display">
        <div class="rep-num" id="rep-num">0</div>
        <div class="rep-state-pill" id="rep-state">WAITING</div>
      </div>
    </div>

    <!-- Corrections -->
    <div class="card" style="flex:1;">
      <div class="card-title">Feedback</div>
      <div id="corrections-list"><span class="correction-ok">Waiting for pose…</span></div>
    </div>

    <!-- Joint angles -->
    <div class="card">
      <div class="card-title">Joint Angles</div>
      <div class="angles-grid" id="angles-grid"></div>
    </div>

  </div>
</div>

<footer>
  Smart Gym Assistant · BlazePose (MediaPipe) · Applied AI Course · Applied Roots
</footer>

<script>
const socket = io();

socket.on("connect",    () => setStatus("● Connected",  "#30d158"));
socket.on("disconnect", () => setStatus("○ Disconnected","#ff453a"));

function setStatus(msg, col) {
  const el = document.getElementById("connection-status");
  el.textContent = msg;
  el.style.color = col;
}

// ── Feedback handler ──────────────────────────────────────────
socket.on("feedback", (d) => {
  updateScore(d.form_score, d.color);
  updateReps(d.reps, d.rep_state);
  updateCorrections(d.corrections, d.landmarks_detected);
  updateAngles(d.angles, d.joint_status);
  updateTips(d);
});

const COLOR_MAP = {
  green:  { text: "#30d158", bar: "#30d158" },
  yellow: { text: "#ffd60a", bar: "#ffd60a" },
  red:    { text: "#ff453a", bar: "#ff453a" },
};

function updateScore(score, color) {
  const el  = document.getElementById("score-num");
  const bar = document.getElementById("score-bar");
  const c   = COLOR_MAP[color] || COLOR_MAP.red;
  el.textContent  = score + "%";
  el.style.color  = c.text;
  bar.style.width = score + "%";
  bar.style.background = c.bar;
}

function updateReps(reps, state) {
  document.getElementById("rep-num").textContent = reps;
  const pill = document.getElementById("rep-state");
  pill.textContent  = state.toUpperCase();
  pill.className    = "rep-state-pill " + state;
}

function updateCorrections(corrections, detected) {
  const el = document.getElementById("corrections-list");
  if (!detected) {
    el.innerHTML = '<span style="color:#6e6e73">Step back – no pose detected</span>';
    return;
  }
  if (!corrections || corrections.length === 0) {
    el.innerHTML = '<span class="correction-ok">✓ Great form! Keep it up.</span>';
    return;
  }
  el.innerHTML = corrections.map(c =>
    `<div class="correction-item"><span class="corr-icon">⚠</span>${c}</div>`
  ).join("");
}

function updateAngles(angles, statuses) {
  const grid = document.getElementById("angles-grid");
  if (!angles || Object.keys(angles).length === 0) {
    grid.innerHTML = "";
    return;
  }
  const LABEL = {
    left_elbow: "L Elbow", right_elbow: "R Elbow",
    left_shoulder: "L Shoulder", right_shoulder: "R Shoulder",
    left_hip: "L Hip", right_hip: "R Hip",
    left_knee: "L Knee", right_knee: "R Knee",
    left_ankle: "L Ankle", right_ankle: "R Ankle",
    trunk: "Trunk",
  };
  grid.innerHTML = Object.entries(angles).map(([k, v]) => {
    const st  = (statuses || {})[k] || "";
    const lbl = LABEL[k] || k;
    return `<div class="angle-item ${st}">
      <span>${lbl}</span>
      <span class="angle-val">${v}°</span>
    </div>`;
  }).join("");
}

const EXERCISE_TIPS = {
  bicep_curl:     ["Elbows pinned to sides","Exhale curling up","Squeeze at the top"],
  squat:          ["Feet shoulder-width","Knees over toes","Drive through heels"],
  push_up:        ["Body straight as a plank","Elbows at 45°","Breathe steadily"],
  shoulder_press: ["Core braced","Press straight overhead","Elbows at 90° at start"],
  lateral_raise:  ["Lead with elbows","Stop at shoulder height","Use light weight"],
  deadlift:       ["Neutral spine always","Bar close to body","Push floor away"],
  lunge:          ["Front knee over ankle","Chest tall","Step far enough"],
  plank:          ["Squeeze everything","Breathe steadily","Hips level"],
};

function updateTips(d) {
  const key  = document.getElementById("exercise-select").value;
  const tips = EXERCISE_TIPS[key] || [];
  document.getElementById("tips-list").innerHTML = tips.map(t =>
    `<div class="tip-item"><span>→</span>${t}</div>`
  ).join("");
}

// ── Controls ──────────────────────────────────────────────────
function setExercise() {
  const key = document.getElementById("exercise-select").value;
  socket.emit("set_exercise", { exercise: key });
}
function resetReps() {
  socket.emit("reset_reps", {});
}
</script>

</body>
</html>
"""


MOBILE_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Gym Cam</title>
<style>
  body { margin:0; background:#000; display:flex;
         flex-direction:column; height:100vh; align-items:center; justify-content:center; }
  video { width:100%; max-width:480px; }
  canvas { display:none; }
  p { color:#888; font-family:sans-serif; font-size:14px; margin-top:10px; text-align:center; }
  .status { color:#ff9f0a; font-size:13px; margin-top:6px; }
</style>
</head>
<body>
<video id="v" autoplay playsinline muted></video>
<canvas id="c"></canvas>
<p>📸 Phone Camera → Laptop</p>
<div class="status" id="status">Connecting camera…</div>

<script>
const video  = document.getElementById("v");
const canvas = document.getElementById("c");
const ctx    = canvas.getContext("2d");
const status = document.getElementById("status");

async function startCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: 640, height: 480 }
    });
    video.srcObject = stream;
    video.onloadedmetadata = () => {
      canvas.width  = video.videoWidth;
      canvas.height = video.videoHeight;
      status.textContent = "✓ Camera active – sending frames";
      sendFrames();
    };
  } catch (e) {
    status.textContent = "Camera error: " + e.message;
  }
}

function sendFrames() {
  setInterval(async () => {
    ctx.drawImage(video, 0, 0);
    canvas.toBlob(async (blob) => {
      try {
        await fetch("/mobile_feed", {
          method: "POST",
          headers: { "Content-Type": "image/jpeg" },
          body: blob,
        });
      } catch (e) {}
    }, "image/jpeg", 0.7);
  }, 66);   // ~15 fps from phone (server processes at 30fps+ from cache)
}

startCamera();
</script>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Smart Gym Assistant")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default 0)")
    parser.add_argument("--port",   type=int, default=5000)
    parser.add_argument("--exercise", default="bicep_curl",
                        choices=list(list_exercises().keys()))
    args = parser.parse_args()

    processor.change_exercise(args.exercise)

    if not open_camera(args.camera):
        print(f"[WARN] Could not open camera {args.camera} – waiting for mobile feed at /mobile")

    # Start background capture thread (for local webcam)
    t = threading.Thread(target=capture_loop, daemon=True)
    t.start()

    local_ip = "localhost"
    try:
        import socket as _s
        local_ip = _s.gethostbyname(_s.gethostname())
    except Exception:
        pass

    print("\n" + "=" * 55)
    print("  Smart Gym Assistant")
    print("=" * 55)
    print(f"  Laptop / TV  →  http://localhost:{args.port}")
    print(f"  Phone camera →  http://{local_ip}:{args.port}/mobile")
    print(f"  Exercise     :  {args.exercise}")
    print("=" * 55 + "\n")

    socketio.run(app, host="0.0.0.0", port=args.port, debug=False)
