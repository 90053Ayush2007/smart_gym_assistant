"""
blazepose_processor.py
----------------------
BlazePose wrapper with:
  - 3-layer landmark smoothing (stable skeleton lines)
  - Pure OpenCV skeleton drawing (no MediaPipe drawing utils)
  - Rep counting FSM
  - Form score + corrections
"""

import cv2
import mediapipe as mp
import numpy as np
import time

from utils.pose_angles     import get_all_angles
from utils.rep_counter     import RepCounter
from utils.pose_correction import evaluate_pose
from exercises.exercise_db import get_exercise

mp_pose = mp.solutions.pose

# ── Colours ────────────────────────────────────────────────────
COLOR = {
    "green":    (0,  210, 100),
    "yellow":   (0,  200, 255),
    "red":      (0,  60,  220),
    "white":    (255,255, 255),
    "dark":     (20, 20,  20),
    "accent":   (255,165, 0),
    "landmark": (0,  220, 255),   # cyan dots
    "bone":     (255,255, 255),   # white sticks default
}

NUM_LANDMARKS = 33

# ── BlazePose connections (index pairs) ────────────────────────
# These are the 35 connections that form the full body skeleton
CONNECTIONS = [
    # Face
    (0,1),(1,2),(2,3),(3,7),
    (0,4),(4,5),(5,6),(6,8),
    (9,10),
    # Torso
    (11,12),(11,23),(12,24),(23,24),
    # Left arm
    (11,13),(13,15),(15,17),(15,19),(15,21),(17,19),
    # Right arm
    (12,14),(14,16),(16,18),(16,20),(16,22),(18,20),
    # Left leg
    (23,25),(25,27),(27,29),(27,31),(29,31),
    # Right leg
    (24,26),(26,28),(28,30),(28,32),(30,32),
]

# Body part groups for colour coding
LEFT_LANDMARKS  = {11,13,15,17,19,21,23,25,27,29,31}
RIGHT_LANDMARKS = {12,14,16,18,20,22,24,26,28,30,32}


# ══════════════════════════════════════════════════════════════
#  ONE-EURO FILTER  — removes jitter when still, stays fast
#  when moving.  Best filter for human motion tracking.
# ══════════════════════════════════════════════════════════════

class OneEuroFilter:
    def __init__(self, freq=30.0, mincutoff=1.5, beta=0.05, dcutoff=1.0):
        self.freq      = freq
        self.mincutoff = mincutoff
        self.beta      = beta
        self.dcutoff   = dcutoff
        self.x_prev    = None
        self.dx_prev   = 0.0
        self.t_prev    = None

    def _alpha(self, cutoff):
        tau = 1.0 / (2 * np.pi * cutoff)
        te  = 1.0 / max(self.freq, 1e-6)
        return 1.0 / (1.0 + tau / te)

    def filter(self, x, t=None):
        if t is None:
            t = time.time()
        if self.x_prev is None:
            self.x_prev = x
            self.t_prev = t
            return x
        dt = t - self.t_prev
        if dt > 0:
            self.freq = 1.0 / dt
        self.t_prev = t
        dx  = (x - self.x_prev) * self.freq
        a_d = self._alpha(self.dcutoff)
        dx  = a_d * dx + (1 - a_d) * self.dx_prev
        cutoff = self.mincutoff + self.beta * abs(dx)
        a      = self._alpha(cutoff)
        x_hat  = a * x + (1 - a) * self.x_prev
        self.x_prev  = x_hat
        self.dx_prev = dx
        return x_hat


class LandmarkSmoother:
    """One-Euro filter for every landmark coordinate (33 × 3 = 99 filters)."""
    def __init__(self, mincutoff=1.5, beta=0.05):
        self.filters = [
            [OneEuroFilter(mincutoff=mincutoff, beta=beta) for _ in range(3)]
            for _ in range(NUM_LANDMARKS)
        ]

    def smooth(self, landmarks):
        t = time.time()
        out = np.zeros((NUM_LANDMARKS, 3))
        for i, lm in enumerate(landmarks):
            out[i, 0] = self.filters[i][0].filter(lm.x, t)
            out[i, 1] = self.filters[i][1].filter(lm.y, t)
            out[i, 2] = self.filters[i][2].filter(lm.z, t)
        return out


class EMALandmarkSmoother:
    """Exponential Moving Average — final light polish pass."""
    def __init__(self, alpha=0.4):
        self.alpha = alpha
        self.prev  = None

    def smooth(self, coords: np.ndarray) -> np.ndarray:
        if self.prev is None:
            self.prev = coords.copy()
            return coords
        self.prev = self.alpha * coords + (1 - self.alpha) * self.prev
        return self.prev.copy()


# ══════════════════════════════════════════════════════════════
#  SIMPLE LANDMARK WRAPPER
#  Plain Python object — no Protobuf, no HasField needed
# ══════════════════════════════════════════════════════════════

class SimpleLandmark:
    """Minimal landmark object used for angle computation only."""
    __slots__ = ("x", "y", "z", "visibility")
    def __init__(self, x, y, z, visibility=1.0):
        self.x          = float(x)
        self.y          = float(y)
        self.z          = float(z)
        self.visibility = float(visibility)


# ══════════════════════════════════════════════════════════════
#  MAIN PROCESSOR
# ══════════════════════════════════════════════════════════════

class GymPoseProcessor:
    def __init__(
        self,
        exercise_key: str           = "bicep_curl",
        model_complexity: int       = 1,
        min_detection_confidence: float = 0.6,
        min_tracking_confidence:  float = 0.6,
        one_euro_mincutoff: float   = 1.5,
        one_euro_beta:      float   = 0.05,
        ema_alpha:          float   = 0.4,
    ):
        self.exercise_key = exercise_key
        self.exercise     = get_exercise(exercise_key)

        # BlazePose — smooth_landmarks=True is Layer 1
        self.pose = mp_pose.Pose(
            model_complexity         = model_complexity,
            smooth_landmarks         = True,
            enable_segmentation      = False,
            min_detection_confidence = min_detection_confidence,
            min_tracking_confidence  = min_tracking_confidence,
        )

        # Layer 2: One-Euro
        self.one_euro = LandmarkSmoother(
            mincutoff = one_euro_mincutoff,
            beta      = one_euro_beta,
        )
        # Layer 3: EMA
        self.ema = EMALandmarkSmoother(alpha=ema_alpha)

        # Rep counter
        self._setup_rep_counter()

        # Timing
        self._start_time  = time.time()
        self._frame_count = 0
        self._fps         = 0.0
        self.last_feedback = {}
        self.last_angles   = {}

    def _setup_rep_counter(self):
        rc = self.exercise.get("rep_counter") if self.exercise else None
        if rc:
            self.rep_counter = RepCounter(
                up_threshold   = rc["up_threshold"],
                down_threshold = rc["down_threshold"],
            )
            self._rep_joint = rc["joint"]
        else:
            self.rep_counter = None
            self._rep_joint  = None

    # ── Public API ────────────────────────────────────────────

    def change_exercise(self, exercise_key: str):
        self.exercise_key = exercise_key
        self.exercise     = get_exercise(exercise_key)
        self._setup_rep_counter()

    def reset_reps(self):
        if self.rep_counter:
            self.rep_counter.reset()

    def process_frame(self, bgr_frame: np.ndarray):
        self._frame_count += 1
        h, w = bgr_frame.shape[:2]

        # MediaPipe needs RGB
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.pose.process(rgb)       # Layer 1 smoothing inside
        rgb.flags.writeable = True
        frame = bgr_frame.copy()

        feedback = {
            "exercise":           self.exercise["name"] if self.exercise else "—",
            "form_score":         0,
            "corrections":        [],
            "joint_status":       {},
            "color":              "red",
            "reps":               0,
            "rep_state":          "waiting",
            "angles":             {},
            "fps":                self._fps,
            "landmarks_detected": False,
        }

        if not results.pose_landmarks:
            self._draw_no_pose(frame, w, h)
            self._draw_hud(frame, feedback, w, h)
            self._update_fps()
            return frame, feedback

        feedback["landmarks_detected"] = True
        raw_lm = results.pose_landmarks.landmark

        # ── Layer 2: One-Euro filter ──────────────────────────
        smoothed = self.one_euro.smooth(raw_lm)

        # ── Layer 3: EMA ──────────────────────────────────────
        smoothed = self.ema.smooth(smoothed)

        # Visibility from original landmarks
        vis = [lm.visibility for lm in raw_lm]

        # Build simple landmark list for angle computation
        lm_list = [
            SimpleLandmark(smoothed[i,0], smoothed[i,1], smoothed[i,2], vis[i])
            for i in range(NUM_LANDMARKS)
        ]

        # ── Compute joint angles ───────────────────────────────
        angles = get_all_angles(lm_list)
        self.last_angles = angles
        feedback["angles"] = {k: round(v, 1) for k, v in angles.items()}

        # ── Rep counter ────────────────────────────────────────
        rep_state = "waiting"
        if self.rep_counter and self._rep_joint in angles:
            rep_result = self.rep_counter.update(angles[self._rep_joint])
            rep_state  = rep_result["state"]
            feedback["reps"]      = rep_result["reps"]
            feedback["rep_state"] = rep_state

        # ── Pose correction ────────────────────────────────────
        eval_result = evaluate_pose(self.exercise_key, angles, rep_state)
        feedback.update(eval_result)
        self.last_feedback = feedback

        # ── Draw skeleton with pure OpenCV ─────────────────────
        self._draw_skeleton_cv2(frame, smoothed, vis, feedback["color"], w, h)

        # ── Angle labels ───────────────────────────────────────
        self._draw_angle_labels(frame, lm_list, angles,
                                feedback["joint_status"], w, h)

        # ── HUD overlay ───────────────────────────────────────
        self._draw_hud(frame, feedback, w, h)

        self._update_fps()
        return frame, feedback

    def session_stats(self) -> dict:
        return self.rep_counter.session_stats() if self.rep_counter else {}

    def close(self):
        self.pose.close()

    def _update_fps(self):
        elapsed = time.time() - self._start_time
        if elapsed > 0:
            self._fps = round(self._frame_count / elapsed, 1)

    # ── Drawing ───────────────────────────────────────────────

    def _draw_skeleton_cv2(self, frame, smoothed, vis, form_color, w, h):
        """
        Draw skeleton using pure OpenCV — no MediaPipe drawing utils needed.
        smoothed: numpy array (33, 3) with normalised x,y,z coords
        """
        # Convert normalised coords to pixel coords
        pts = np.zeros((NUM_LANDMARKS, 2), dtype=int)
        for i in range(NUM_LANDMARKS):
            pts[i, 0] = int(smoothed[i, 0] * w)
            pts[i, 1] = int(smoothed[i, 1] * h)

        # Connection colour based on form score
        form_col = COLOR.get(form_color, COLOR["bone"])

        # Draw connections (sticks between keypoints)
        for a, b in CONNECTIONS:
            # Skip if either landmark is not visible
            if vis[a] < 0.3 or vis[b] < 0.3:
                continue
            pt1 = tuple(pts[a])
            pt2 = tuple(pts[b])

            # Colour left side blue, right side green, centre white
            if a in LEFT_LANDMARKS or b in LEFT_LANDMARKS:
                col = (255, 100, 0)     # blue-ish for left
            elif a in RIGHT_LANDMARKS or b in RIGHT_LANDMARKS:
                col = (0, 200, 50)      # green for right
            else:
                col = (200, 200, 200)   # white for centre/torso

            # Draw thick white border first then coloured line on top
            cv2.line(frame, pt1, pt2, (30, 30, 30), 5, cv2.LINE_AA)
            cv2.line(frame, pt1, pt2, col,           3, cv2.LINE_AA)

        # Draw keypoint circles
        for i in range(NUM_LANDMARKS):
            if vis[i] < 0.3:
                continue
            pt = tuple(pts[i])
            # Outer dark ring
            cv2.circle(frame, pt, 7,  (20, 20, 20),  -1, cv2.LINE_AA)
            # Inner coloured dot
            if i in LEFT_LANDMARKS:
                dot_col = (255, 150, 50)
            elif i in RIGHT_LANDMARKS:
                dot_col = (50, 230, 80)
            else:
                dot_col = (0, 220, 255)  # cyan for face/centre
            cv2.circle(frame, pt, 5, dot_col, -1, cv2.LINE_AA)

    def _draw_angle_labels(self, frame, lm_list, angles, joint_status, w, h):
        PL = mp_pose.PoseLandmark
        joint_landmark_map = {
            "left_elbow":     PL.LEFT_ELBOW,
            "right_elbow":    PL.RIGHT_ELBOW,
            "left_shoulder":  PL.LEFT_SHOULDER,
            "right_shoulder": PL.RIGHT_SHOULDER,
            "left_hip":       PL.LEFT_HIP,
            "right_hip":      PL.RIGHT_HIP,
            "left_knee":      PL.LEFT_KNEE,
            "right_knee":     PL.RIGHT_KNEE,
            "left_ankle":     PL.LEFT_ANKLE,
            "right_ankle":    PL.RIGHT_ANKLE,
        }

        visible_joints = set(
            self.exercise.get("joints_to_check", [])
        ) if self.exercise else set(joint_landmark_map.keys())

        for joint, lm_idx in joint_landmark_map.items():
            if joint not in visible_joints:
                continue
            angle = angles.get(joint)
            if angle is None:
                continue
            lm  = lm_list[lm_idx]
            px  = int(lm.x * w)
            py  = int(lm.y * h)

            status = joint_status.get(joint, "ok")
            col = (
                COLOR["green"]  if status == "ok"      else
                COLOR["yellow"] if status == "too_low" else
                COLOR["red"]
            )
            label = f"{int(angle)}"
            # Dark shadow for readability
            cv2.putText(frame, label, (px - 15, py - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                        (0, 0, 0), 4, cv2.LINE_AA)
            # Coloured text
            cv2.putText(frame, label, (px - 15, py - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                        col, 2, cv2.LINE_AA)

    def _draw_no_pose(self, frame, w, h):
        cv2.putText(frame,
                    "NO POSE DETECTED",
                    (w//2 - 180, h//2),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0,
                    COLOR["red"], 2, cv2.LINE_AA)
        cv2.putText(frame,
                    "Step back so full body is visible",
                    (w//2 - 220, h//2 + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    COLOR["white"], 1, cv2.LINE_AA)

    def _draw_hud(self, frame, feedback: dict, w: int, h: int):
        # Semi-transparent left panel
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (340, h), (10, 10, 10), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        # Exercise name
        cv2.putText(frame, feedback.get("exercise", "—"), (12, 38),
                    cv2.FONT_HERSHEY_DUPLEX, 0.85,
                    COLOR["accent"], 2, cv2.LINE_AA)

        # Form score bar
        score     = feedback.get("form_score", 0)
        bar_color = COLOR.get(feedback.get("color", "red"), COLOR["red"])
        cv2.putText(frame, "FORM SCORE", (12, 72),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    COLOR["white"], 1, cv2.LINE_AA)
        bar_w = int(300 * score / 100)
        cv2.rectangle(frame, (12, 80),  (312, 98), (60, 60, 60), -1)
        cv2.rectangle(frame, (12, 80),  (12 + bar_w, 98), bar_color, -1)
        cv2.putText(frame, f"{score}%", (318, 96),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    bar_color, 2, cv2.LINE_AA)

        # Rep count
        cv2.putText(frame, "REPS", (12, 128),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    COLOR["white"], 1, cv2.LINE_AA)
        cv2.putText(frame, str(feedback.get("reps", 0)), (12, 180),
                    cv2.FONT_HERSHEY_DUPLEX, 2.2,
                    COLOR["accent"], 3, cv2.LINE_AA)

        # Rep state pill
        state = feedback.get("rep_state", "waiting")
        state_col = {
            "up":      COLOR["green"],
            "down":    COLOR["yellow"],
            "waiting": (120, 120, 120),
        }.get(state, COLOR["white"])
        cv2.putText(frame, state.upper(), (110, 175),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    state_col, 2, cv2.LINE_AA)

        # Corrections
        y = 212
        cv2.putText(frame, "FEEDBACK", (12, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    COLOR["white"], 1, cv2.LINE_AA)
        y += 22
        corrections = feedback.get("corrections", [])
        if not corrections:
            if feedback.get("landmarks_detected"):
                cv2.putText(frame, "Good form! Keep it up", (12, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                            COLOR["green"], 1, cv2.LINE_AA)
        else:
            for msg in corrections[:4]:
                words = msg.split()
                line, lines = "", []
                for word in words:
                    if len(line) + len(word) + 1 <= 34:
                        line += (" " if line else "") + word
                    else:
                        lines.append(line)
                        line = word
                if line:
                    lines.append(line)
                for ln in lines:
                    cv2.putText(frame, "• " + ln, (12, y),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                                COLOR["yellow"], 1, cv2.LINE_AA)
                    y += 18
                y += 4

        # FPS
        cv2.putText(frame, f"FPS: {self._fps}", (12, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (100, 100, 100), 1, cv2.LINE_AA)

        # Key hints
        cv2.putText(frame,
                    "Q=quit  R=reset reps  1-8=exercise  SPACE=pause",
                    (350, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    (80, 80, 80), 1, cv2.LINE_AA)