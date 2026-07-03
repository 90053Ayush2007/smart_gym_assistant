"""
exercise_db.py
--------------
Exercise database with carefully calibrated angle thresholds.

IMPORTANT THRESHOLD GUIDE:
  For bicep curl (tracking elbow angle):
    - Standing with arm fully extended = ~160°
    - Arm fully curled = ~40°
    - down_threshold = 140  (arm must reach THIS angle to be "down")
    - up_threshold   = 70   (arm must reach THIS angle to be "up")
    - Wider gap = easier to count, narrower = stricter

  If reps NOT counting:
    - Increase up_threshold (e.g. 70 → 90) so "up" is easier to reach
    - Decrease down_threshold (e.g. 140 → 120) so "down" is easier to reach

  If reps double counting:
    - Decrease up_threshold
    - Increase down_threshold
    - Increase hysteresis in RepCounter
"""

EXERCISES = {

    # ─────────────────────────────────────────────────────────
    #  BICEP CURL
    # ─────────────────────────────────────────────────────────
    "bicep_curl": {
        "name": "Bicep Curl",
        "muscles": ["biceps brachii", "brachialis"],
        "joints_to_check": ["left_elbow", "right_elbow", "left_shoulder", "trunk"],
        "target_angles": {
            "left_elbow_down":   160,
            "left_elbow_up":      40,
            "right_elbow_down":  160,
            "right_elbow_up":     40,
            "left_shoulder":      15,
            "trunk":               5,
        },
        "tolerance_deg": {
            "left_elbow":    20,
            "right_elbow":   20,
            "left_shoulder": 25,
            "trunk":         12,
        },
        "rep_counter": {
            "joint":          "left_elbow",
            "up_threshold":    80,    # elbow angle = "curled up" — increased from 55
            "down_threshold":  140,   # elbow angle = "extended down" — decreased from 150
        },
        "corrections": {
            "left_elbow": {
                "too_high": "Extend your arm more at the bottom",
                "too_low":  "Curl higher for full range of motion",
            },
            "left_shoulder": {
                "too_high": "Keep elbow pinned to your side",
                "too_low":  "Don't let shoulder drop back",
            },
            "trunk": {
                "too_high": "Stop swinging your back",
                "too_low":  "Stand upright",
            },
        },
        "tips": [
            "Keep elbows glued to your sides",
            "Squeeze bicep at the top",
            "Control the weight on the way down",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  SQUAT
    # ─────────────────────────────────────────────────────────
    "squat": {
        "name": "Squat",
        "muscles": ["quadriceps", "glutes", "hamstrings", "core"],
        "joints_to_check": ["left_knee", "right_knee", "left_hip", "trunk"],
        "target_angles": {
            "left_knee_down":   95,
            "right_knee_down":  95,
            "left_knee_up":    165,
            "right_knee_up":   165,
            "left_hip":         90,
            "trunk":            15,
        },
        "tolerance_deg": {
            "left_knee":  20,
            "right_knee": 20,
            "left_hip":   25,
            "trunk":      18,
        },
        "rep_counter": {
            "joint":          "left_knee",
            "up_threshold":   150,   # standing = knee angle large
            "down_threshold": 120,   # squatting = knee angle small
        },
        "corrections": {
            "left_knee": {
                "too_high": "Go deeper — aim for parallel",
                "too_low":  "Knees caving — push them out",
            },
            "trunk": {
                "too_high": "Keep chest up — don't lean forward",
                "too_low":  "Slight lean is normal",
            },
        },
        "tips": [
            "Feet shoulder-width apart",
            "Push knees out over toes",
            "Drive through heels to stand",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  PUSH-UP
    # ─────────────────────────────────────────────────────────
    "push_up": {
        "name": "Push-Up",
        "muscles": ["pectorals", "triceps", "anterior deltoid", "core"],
        "joints_to_check": ["left_elbow", "right_elbow", "trunk"],
        "target_angles": {
            "left_elbow_down":   90,
            "right_elbow_down":  90,
            "left_elbow_up":    155,
            "right_elbow_up":   155,
            "trunk":               5,
        },
        "tolerance_deg": {
            "left_elbow":    20,
            "right_elbow":   20,
            "trunk":         10,
        },
        "rep_counter": {
            "joint":          "left_elbow",
            "up_threshold":   140,   # arms extended = up
            "down_threshold": 110,   # chest to floor = down
        },
        "corrections": {
            "left_elbow": {
                "too_high": "Lower chest closer to floor",
                "too_low":  "Don't lock elbows at top",
            },
            "trunk": {
                "too_high": "Hips sagging — engage your core",
                "too_low":  "Hips too high — lower into plank",
            },
        },
        "tips": [
            "Body straight from head to heels",
            "Elbows at 45° from torso",
            "Breathe in down, out up",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  SHOULDER PRESS
    # ─────────────────────────────────────────────────────────
    "shoulder_press": {
        "name": "Shoulder Press",
        "muscles": ["deltoids", "triceps", "trapezius"],
        "joints_to_check": ["left_elbow", "right_elbow", "trunk"],
        "target_angles": {
            "left_elbow_down":   90,
            "right_elbow_down":  90,
            "left_elbow_up":    165,
            "right_elbow_up":   165,
            "trunk":               5,
        },
        "tolerance_deg": {
            "left_elbow":    20,
            "right_elbow":   20,
            "trunk":         12,
        },
        "rep_counter": {
            "joint":          "left_elbow",
            "up_threshold":   150,   # arms up overhead
            "down_threshold": 105,   # weights at ear level
        },
        "corrections": {
            "left_elbow": {
                "too_high": "Bring weights down to ear level",
                "too_low":  "Fully extend arms overhead",
            },
            "trunk": {
                "too_high": "Don't arch lower back — brace core",
                "too_low":  "Stand tall",
            },
        },
        "tips": [
            "Start with elbows at 90° at shoulder height",
            "Press directly overhead",
            "Don't arch your back",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  LATERAL RAISE
    # ─────────────────────────────────────────────────────────
    "lateral_raise": {
        "name": "Lateral Raise",
        "muscles": ["medial deltoid"],
        "joints_to_check": ["left_shoulder", "right_shoulder", "trunk"],
        "target_angles": {
            "left_shoulder_up":    85,
            "right_shoulder_up":   85,
            "left_shoulder_down":  15,
            "right_shoulder_down": 15,
            "trunk":                5,
        },
        "tolerance_deg": {
            "left_shoulder":  20,
            "right_shoulder": 20,
            "trunk":          12,
        },
        "rep_counter": {
            "joint":          "left_shoulder",
            "up_threshold":   65,    # arms raised
            "down_threshold": 35,    # arms lowered
        },
        "corrections": {
            "left_shoulder": {
                "too_high": "Don't raise above shoulder height",
                "too_low":  "Raise arms to shoulder level",
            },
            "trunk": {
                "too_high": "Stop swinging — use lighter weight",
                "too_low":  "Stand straight",
            },
        },
        "tips": [
            "Lead with elbows not wrists",
            "Slight bend in elbow is fine",
            "Go light — small muscle",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  DEADLIFT
    # ─────────────────────────────────────────────────────────
    "deadlift": {
        "name": "Deadlift",
        "muscles": ["hamstrings", "glutes", "lower back", "traps"],
        "joints_to_check": ["left_hip", "right_hip", "left_knee", "trunk"],
        "target_angles": {
            "left_hip_down":   50,
            "right_hip_down":  50,
            "left_hip_up":    165,
            "right_hip_up":   165,
            "left_knee":      155,
            "trunk":           10,
        },
        "tolerance_deg": {
            "left_hip":   20,
            "right_hip":  20,
            "left_knee":  25,
            "trunk":      15,
        },
        "rep_counter": {
            "joint":          "left_hip",
            "up_threshold":   150,   # standing upright
            "down_threshold":  90,   # hinging forward
        },
        "corrections": {
            "left_hip": {
                "too_high": "Hinge deeper at hip — push hips back",
                "too_low":  "Don't round lower back",
            },
            "trunk": {
                "too_high": "CRITICAL: Straighten your back!",
                "too_low":  "Keep neutral spine",
            },
        },
        "tips": [
            "Neutral spine throughout",
            "Bar close to your body",
            "Push floor away — don't pull weight up",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  LUNGE
    # ─────────────────────────────────────────────────────────
    "lunge": {
        "name": "Lunge",
        "muscles": ["quadriceps", "glutes", "hamstrings"],
        "joints_to_check": ["left_knee", "right_knee", "trunk"],
        "target_angles": {
            "left_knee_down":   95,
            "right_knee_down":  95,
            "left_knee_up":    165,
            "right_knee_up":   165,
            "trunk":             5,
        },
        "tolerance_deg": {
            "left_knee":  20,
            "right_knee": 20,
            "trunk":      12,
        },
        "rep_counter": {
            "joint":          "left_knee",
            "up_threshold":   150,
            "down_threshold": 115,
        },
        "corrections": {
            "left_knee": {
                "too_high": "Step further — front knee at 90°",
                "too_low":  "Front knee past toes — step further",
            },
            "trunk": {
                "too_high": "Keep torso upright",
                "too_low":  "Don't lean too far forward",
            },
        },
        "tips": [
            "Front knee directly over ankle",
            "Back knee hovers above floor",
            "Both knees reach 90°",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  PLANK (timed — no rep counting)
    # ─────────────────────────────────────────────────────────
    "plank": {
        "name": "Plank",
        "muscles": ["core", "shoulders", "glutes"],
        "joints_to_check": ["left_elbow", "right_elbow", "trunk", "left_hip"],
        "target_angles": {
            "left_elbow":   90,
            "right_elbow":  90,
            "trunk":          5,
            "left_hip":     175,
        },
        "tolerance_deg": {
            "left_elbow":  15,
            "right_elbow": 15,
            "trunk":        8,
            "left_hip":    12,
        },
        "rep_counter": None,
        "corrections": {
            "trunk": {
                "too_high": "Hips sagging — lift hips and brace core",
                "too_low":  "Hips too high — lower into straight line",
            },
            "left_hip": {
                "too_high": "Keep hips in line with body",
                "too_low":  "Don't pike hips up",
            },
        },
        "tips": [
            "Squeeze glutes abs and quads",
            "Breathe steadily",
            "Gaze at floor slightly ahead",
        ],
    },
}


def get_exercise(name: str):
    return EXERCISES.get(name)


def list_exercises():
    return {k: v["name"] for k, v in EXERCISES.items()}