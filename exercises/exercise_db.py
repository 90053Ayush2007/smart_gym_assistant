"""
exercise_db.py
--------------
Exercise database with phase-aware angle targets.

IMPORTANT — HOW TARGETS WORK NOW:
  Each exercise has targets for TWO phases:
    joint_down = target angle when arm/leg is EXTENDED (bottom of movement)
    joint_up   = target angle when arm/leg is CONTRACTED (top of movement)

  Form score compares to the RIGHT target for the current phase.
  This means:
    - During a curl at the top: elbow compared to elbow_up target (40°)
    - During a curl at the bottom: elbow compared to elbow_down target (160°)

  TOLERANCES are generous (25-35°) so good-but-not-perfect form scores well.

HOW TO TUNE IF SCORE STILL WRONG:
  - Score always low → increase tolerance_deg values
  - Score never changes → targets are unreachable, adjust target_angles
  - Score jumps wildly → increase _score_buffer size in pose_correction.py
"""

EXERCISES = {

    # ─────────────────────────────────────────────────────────
    #  BICEP CURL
    # ─────────────────────────────────────────────────────────
    "bicep_curl": {
        "name": "Bicep Curl",
        "muscles": ["biceps brachii", "brachialis"],

        # Only check joints that are VISIBLE and RELEVANT
        "joints_to_check": [
            "left_elbow", "right_elbow",
            "left_shoulder", "trunk"
        ],

        # Phase-aware targets
        "target_angles": {
            # Bottom of curl — arm extended
            "left_elbow_down":    155,
            "right_elbow_down":   155,
            # Top of curl — arm contracted
            "left_elbow_up":       45,
            "right_elbow_up":      45,
            # Shoulder stays stable throughout
            "left_shoulder":       20,
            "right_shoulder":      20,
            # Trunk stays upright
            "trunk":                5,
        },

        # WIDE tolerances — good form should score 80+
        "tolerance_deg": {
            "left_elbow":     30,   # ±30° from target still "ok"
            "right_elbow":    30,
            "left_shoulder":  30,
            "right_shoulder": 30,
            "trunk":          15,
        },

        "rep_counter": {
            "joint":          "left_elbow",
            "up_threshold":    80,
            "down_threshold":  140,
        },

        "corrections": {
            "left_elbow": {
                "too_high": "Extend your left arm fully at the bottom",
                "too_low":  "Curl your left arm higher — full range!",
            },
            "right_elbow": {
                "too_high": "Extend your right arm fully at the bottom",
                "too_low":  "Curl your right arm higher — full range!",
            },
            "left_shoulder": {
                "too_high": "Keep left elbow pinned to your side",
                "too_low":  "Don't let left shoulder drop back",
            },
            "trunk": {
                "too_high": "Stop swinging — control the weight",
                "too_low":  "Stand upright — don't lean back",
            },
        },

        "tips": [
            "Keep elbows glued to your sides",
            "Squeeze bicep hard at the top",
            "Control the weight on the way down",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  SQUAT
    # ─────────────────────────────────────────────────────────
    "squat": {
        "name": "Squat",
        "muscles": ["quadriceps", "glutes", "hamstrings", "core"],

        "joints_to_check": [
            "left_knee", "right_knee",
            "left_hip", "trunk"
        ],

        "target_angles": {
            # Bottom of squat — deep position
            "left_knee_down":    90,
            "right_knee_down":   90,
            "left_hip_down":     80,
            "right_hip_down":    80,
            # Top — standing position
            "left_knee_up":     170,
            "right_knee_up":    170,
            "left_hip_up":      170,
            "right_hip_up":     170,
            # Trunk — slight forward lean is normal
            "trunk":             12,
        },

        "tolerance_deg": {
            "left_knee":  30,
            "right_knee": 30,
            "left_hip":   30,
            "right_hip":  30,
            "trunk":      18,
        },

        "rep_counter": {
            "joint":          "left_knee",
            "up_threshold":   150,
            "down_threshold": 120,
        },

        "corrections": {
            "left_knee": {
                "too_high": "Go deeper — aim for parallel (90°)",
                "too_low":  "Knees caving — push them out",
            },
            "right_knee": {
                "too_high": "Go deeper on right side",
                "too_low":  "Right knee caving — push out",
            },
            "trunk": {
                "too_high": "Keep chest up — don't lean too far forward",
                "too_low":  "Slight forward lean is normal",
            },
            "left_hip": {
                "too_high": "Sit hips back more — hinge at hip",
                "too_low":  "Don't collapse forward",
            },
        },

        "tips": [
            "Feet shoulder-width apart, toes slightly out",
            "Push knees out over toes",
            "Drive through heels to stand up",
            "Keep chest tall throughout",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  PUSH-UP
    # ─────────────────────────────────────────────────────────
    "push_up": {
        "name": "Push-Up",
        "muscles": ["pectorals", "triceps", "anterior deltoid", "core"],

        "joints_to_check": [
            "left_elbow", "right_elbow", "trunk"
        ],

        "target_angles": {
            # Bottom — chest near floor
            "left_elbow_down":    85,
            "right_elbow_down":   85,
            # Top — arms extended
            "left_elbow_up":     155,
            "right_elbow_up":    155,
            # Body stays straight
            "trunk":               5,
        },

        "tolerance_deg": {
            "left_elbow":  30,
            "right_elbow": 30,
            "trunk":       12,
        },

        "rep_counter": {
            "joint":          "left_elbow",
            "up_threshold":   140,
            "down_threshold": 110,
        },

        "corrections": {
            "left_elbow": {
                "too_high": "Lower chest closer to the floor",
                "too_low":  "Don't lock elbows at top",
            },
            "right_elbow": {
                "too_high": "Lower your chest to the floor",
                "too_low":  "Don't lock elbows",
            },
            "trunk": {
                "too_high": "Hips sagging — engage your core!",
                "too_low":  "Hips too high — lower into straight plank",
            },
        },

        "tips": [
            "Body straight from head to heels",
            "Elbows at 45° from torso — not flared wide",
            "Breathe in on way down, out on way up",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  SHOULDER PRESS
    # ─────────────────────────────────────────────────────────
    "shoulder_press": {
        "name": "Shoulder Press",
        "muscles": ["deltoids", "triceps", "trapezius"],

        "joints_to_check": [
            "left_elbow", "right_elbow", "trunk"
        ],

        "target_angles": {
            # Bottom — weights at ear level
            "left_elbow_down":    88,
            "right_elbow_down":   88,
            # Top — arms overhead
            "left_elbow_up":     165,
            "right_elbow_up":    165,
            "trunk":               5,
        },

        "tolerance_deg": {
            "left_elbow":  30,
            "right_elbow": 30,
            "trunk":       15,
        },

        "rep_counter": {
            "joint":          "left_elbow",
            "up_threshold":   150,
            "down_threshold": 105,
        },

        "corrections": {
            "left_elbow": {
                "too_high": "Bring weights down to ear level",
                "too_low":  "Fully extend arms overhead",
            },
            "right_elbow": {
                "too_high": "Bring weights down to ear level",
                "too_low":  "Fully extend arms overhead",
            },
            "trunk": {
                "too_high": "Don't arch lower back — brace your core",
                "too_low":  "Stand tall",
            },
        },

        "tips": [
            "Start with elbows at 90° at shoulder height",
            "Press directly overhead — not forward",
            "Don't arch your lower back",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  LATERAL RAISE
    # ─────────────────────────────────────────────────────────
    "lateral_raise": {
        "name": "Lateral Raise",
        "muscles": ["medial deltoid"],

        "joints_to_check": [
            "left_shoulder", "right_shoulder", "trunk"
        ],

        "target_angles": {
            # Top — arms at shoulder height
            "left_shoulder_up":    85,
            "right_shoulder_up":   85,
            # Bottom — arms at sides
            "left_shoulder_down":  15,
            "right_shoulder_down": 15,
            "trunk":                5,
        },

        "tolerance_deg": {
            "left_shoulder":  25,
            "right_shoulder": 25,
            "trunk":          15,
        },

        "rep_counter": {
            "joint":          "left_shoulder",
            "up_threshold":   65,
            "down_threshold": 35,
        },

        "corrections": {
            "left_shoulder": {
                "too_high": "Don't raise above shoulder height",
                "too_low":  "Raise arms to shoulder level (90°)",
            },
            "right_shoulder": {
                "too_high": "Don't raise above shoulder height",
                "too_low":  "Raise right arm to shoulder level",
            },
            "trunk": {
                "too_high": "Stop swinging — lighter weight or slower",
                "too_low":  "Stand straight",
            },
        },

        "tips": [
            "Lead with elbows not wrists",
            "Slight bend in elbow is fine",
            "Go light — this isolates a small muscle",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  DEADLIFT
    # ─────────────────────────────────────────────────────────
    "deadlift": {
        "name": "Deadlift",
        "muscles": ["hamstrings", "glutes", "lower back", "traps"],

        "joints_to_check": [
            "left_hip", "right_hip", "left_knee", "trunk"
        ],

        "target_angles": {
            # Bottom — hinged forward
            "left_hip_down":    50,
            "right_hip_down":   50,
            # Top — standing upright
            "left_hip_up":     168,
            "right_hip_up":    168,
            # Slight knee bend throughout
            "left_knee":       155,
            "right_knee":      155,
            # Neutral spine
            "trunk":            10,
        },

        "tolerance_deg": {
            "left_hip":   30,
            "right_hip":  30,
            "left_knee":  30,
            "right_knee": 30,
            "trunk":      15,
        },

        "rep_counter": {
            "joint":          "left_hip",
            "up_threshold":   150,
            "down_threshold":  90,
        },

        "corrections": {
            "left_hip": {
                "too_high": "Hinge deeper at hip — push hips back",
                "too_low":  "Don't round lower back",
            },
            "trunk": {
                "too_high": "CRITICAL: Straighten your back — injury risk!",
                "too_low":  "Keep neutral spine — don't hyperextend",
            },
            "left_knee": {
                "too_high": "Keep slight bend in knees",
                "too_low":  "Don't squat the deadlift — hinge at hip",
            },
        },

        "tips": [
            "Neutral spine throughout — no rounding!",
            "Bar close to your body",
            "Push the floor away — don't pull weight up",
            "Squeeze glutes at the top",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  LUNGE
    # ─────────────────────────────────────────────────────────
    "lunge": {
        "name": "Lunge",
        "muscles": ["quadriceps", "glutes", "hamstrings"],

        "joints_to_check": [
            "left_knee", "right_knee", "trunk"
        ],

        "target_angles": {
            # Bottom — both knees at 90°
            "left_knee_down":   92,
            "right_knee_down":  92,
            # Top — standing
            "left_knee_up":    168,
            "right_knee_up":   168,
            "trunk":             5,
        },

        "tolerance_deg": {
            "left_knee":  30,
            "right_knee": 30,
            "trunk":      15,
        },

        "rep_counter": {
            "joint":          "left_knee",
            "up_threshold":   150,
            "down_threshold": 115,
        },

        "corrections": {
            "left_knee": {
                "too_high": "Step further forward — front knee at 90°",
                "too_low":  "Front knee past toes — step further back",
            },
            "right_knee": {
                "too_high": "Lower back knee closer to floor",
                "too_low":  "Control back knee descent",
            },
            "trunk": {
                "too_high": "Keep torso upright",
                "too_low":  "Don't lean too far forward",
            },
        },

        "tips": [
            "Front knee directly over ankle",
            "Back knee hovers just above floor",
            "Step far enough for both knees at 90°",
        ],
    },

    # ─────────────────────────────────────────────────────────
    #  PLANK (static hold — no rep counting)
    # ─────────────────────────────────────────────────────────
    "plank": {
        "name": "Plank",
        "muscles": ["core", "shoulders", "glutes"],

        "joints_to_check": [
            "left_elbow", "right_elbow",
            "left_hip", "trunk"
        ],

        "target_angles": {
            "left_elbow":   88,
            "right_elbow":  88,
            "left_hip":    178,
            "right_hip":   178,
            "trunk":         3,
        },

        "tolerance_deg": {
            "left_elbow":  20,
            "right_elbow": 20,
            "left_hip":    15,
            "right_hip":   15,
            "trunk":       10,
        },

        "rep_counter": None,

        "corrections": {
            "trunk": {
                "too_high": "Hips sagging — lift hips and brace core",
                "too_low":  "Hips too high — lower into straight line",
            },
            "left_hip": {
                "too_high": "Keep hips level with body",
                "too_low":  "Don't pike hips up",
            },
            "left_elbow": {
                "too_high": "Elbows directly under shoulders",
                "too_low":  "Elbows directly under shoulders",
            },
        },

        "tips": [
            "Squeeze glutes, abs, and quads",
            "Breathe steadily — don't hold breath",
            "Gaze at floor slightly ahead of hands",
        ],
    },
}


def get_exercise(name: str):
    return EXERCISES.get(name)


def list_exercises():
    return {k: v["name"] for k, v in EXERCISES.items()}