"""
exercises.py
------------
Database of exercises with:
  - ideal joint angles  (target_angles)
  - tolerance per joint (tolerance_deg)
  - which joints to monitor
  - rep-counting configuration (which angle oscillates and its thresholds)
  - correction messages

Each exercise entry follows this schema:
{
    "name": str,
    "muscles": [str],
    "joints_to_check": [str],          # subset of angle keys
    "target_angles": {joint: degrees}, # ideal form
    "tolerance_deg": {joint: degrees}, # acceptable deviation
    "rep_counter": {
        "joint": str,                  # angle that oscillates for a rep
        "up_threshold": float,         # angle considered "up" / contracted
        "down_threshold": float,       # angle considered "down" / extended
    },
    "corrections": {joint: {
        "too_high": str,
        "too_low":  str,
    }},
    "tips": [str],
}

Angle targets derived from:
  - Google ML-Kit pose classification guide (slide 41)
  - BlazePose paper (arxiv 2006.10204)
  - Standard exercise science references
"""

EXERCISES = {

    # ─────────────────────────────────────────
    #  BICEP CURL (Dumbbell)
    # ─────────────────────────────────────────
    "bicep_curl": {
        "name": "Bicep Curl",
        "muscles": ["biceps brachii", "brachialis"],
        "joints_to_check": ["left_elbow", "right_elbow", "left_shoulder", "right_shoulder", "trunk"],
        "target_angles": {
            "left_elbow_down":   160,   # fully extended
            "left_elbow_up":      40,   # fully contracted
            "right_elbow_down":  160,
            "right_elbow_up":     40,
            "left_shoulder":      15,   # arm close to body
            "right_shoulder":     15,
            "trunk":               5,   # no swinging
        },
        "tolerance_deg": {
            "left_elbow":    15,
            "right_elbow":   15,
            "left_shoulder": 20,
            "right_shoulder":20,
            "trunk":         10,
        },
        "rep_counter": {
            "joint":          "left_elbow",   # track left elbow
            "up_threshold":    55,            # curl is "up"
            "down_threshold": 150,            # arm is "down"
        },
        "corrections": {
            "left_elbow": {
                "too_high": "Extend your left arm more at the bottom",
                "too_low":  "Curl your left arm higher – full range of motion!",
            },
            "right_elbow": {
                "too_high": "Extend your right arm more at the bottom",
                "too_low":  "Curl your right arm higher – full range of motion!",
            },
            "left_shoulder": {
                "too_high": "Keep left elbow pinned to your side",
                "too_low":  "Don't let left shoulder drop too far back",
            },
            "right_shoulder": {
                "too_high": "Keep right elbow pinned to your side",
                "too_low":  "Don't let right shoulder drop too far back",
            },
            "trunk": {
                "too_high": "Don't swing your back – control the weight",
                "too_low":  "Stand upright, don't lean backward",
            },
        },
        "tips": [
            "Keep your elbows glued to your sides",
            "Exhale on the way up, inhale on the way down",
            "Squeeze the bicep at the top of each rep",
        ],
    },

    # ─────────────────────────────────────────
    #  SQUAT
    # ─────────────────────────────────────────
    "squat": {
        "name": "Squat",
        "muscles": ["quadriceps", "glutes", "hamstrings", "core"],
        "joints_to_check": ["left_knee", "right_knee", "left_hip", "right_hip", "trunk"],
        "target_angles": {
            "left_knee_down":   90,    # parallel depth
            "right_knee_down":  90,
            "left_knee_up":    170,    # standing
            "right_knee_up":   170,
            "left_hip":         90,
            "right_hip":        90,
            "trunk":            10,    # slight forward lean is ok
        },
        "tolerance_deg": {
            "left_knee":  15,
            "right_knee": 15,
            "left_hip":   20,
            "right_hip":  20,
            "trunk":      15,
        },
        "rep_counter": {
            "joint":          "left_knee",
            "up_threshold":   160,
            "down_threshold": 110,
        },
        "corrections": {
            "left_knee": {
                "too_high": "Go deeper – aim for parallel or below",
                "too_low":  "Don't let knees cave or go too far in",
            },
            "right_knee": {
                "too_high": "Go deeper on your right side",
                "too_low":  "Watch right knee alignment",
            },
            "left_hip": {
                "too_high": "Sit your hips back more",
                "too_low":  "Don't lean too far forward",
            },
            "trunk": {
                "too_high": "Keep chest up – don't lean too far forward",
                "too_low":  "Slight forward lean is normal",
            },
        },
        "tips": [
            "Feet shoulder-width apart, toes slightly out",
            "Push your knees out over your toes",
            "Drive through your heels to stand up",
            "Keep your chest tall throughout the movement",
        ],
    },

    # ─────────────────────────────────────────
    #  PUSH-UP
    # ─────────────────────────────────────────
    "push_up": {
        "name": "Push-Up",
        "muscles": ["pectorals", "triceps", "anterior deltoid", "core"],
        "joints_to_check": ["left_elbow", "right_elbow", "left_shoulder", "right_shoulder", "trunk"],
        "target_angles": {
            "left_elbow_down":   90,   # bottom of push-up
            "right_elbow_down":  90,
            "left_elbow_up":    160,   # top (arms not locked)
            "right_elbow_up":   160,
            "left_shoulder":     45,
            "right_shoulder":    45,
            "trunk":              5,   # plank-straight body
        },
        "tolerance_deg": {
            "left_elbow":    15,
            "right_elbow":   15,
            "left_shoulder": 20,
            "right_shoulder":20,
            "trunk":          8,
        },
        "rep_counter": {
            "joint":          "left_elbow",
            "up_threshold":   150,
            "down_threshold": 105,
        },
        "corrections": {
            "left_elbow": {
                "too_high": "Lower your chest closer to the floor",
                "too_low":  "Don't lock out your elbows at the top",
            },
            "right_elbow": {
                "too_high": "Lower your chest closer to the floor",
                "too_low":  "Don't lock out your elbows",
            },
            "trunk": {
                "too_high": "Hips are sagging – engage your core!",
                "too_low":  "Hips too high – lower into a straight plank",
            },
        },
        "tips": [
            "Keep your body in a straight line from head to heels",
            "Elbows at ~45° from your torso, not flared wide",
            "Breathe in on the way down, out on the way up",
        ],
    },

    # ─────────────────────────────────────────
    #  SHOULDER PRESS
    # ─────────────────────────────────────────
    "shoulder_press": {
        "name": "Shoulder Press",
        "muscles": ["deltoids", "triceps", "trapezius"],
        "joints_to_check": ["left_elbow", "right_elbow", "left_shoulder", "right_shoulder", "trunk"],
        "target_angles": {
            "left_elbow_down":   90,
            "right_elbow_down":  90,
            "left_elbow_up":    170,
            "right_elbow_up":   170,
            "left_shoulder":     90,
            "right_shoulder":    90,
            "trunk":              5,
        },
        "tolerance_deg": {
            "left_elbow":    15,
            "right_elbow":   15,
            "left_shoulder": 20,
            "right_shoulder":20,
            "trunk":         10,
        },
        "rep_counter": {
            "joint":          "left_elbow",
            "up_threshold":   155,
            "down_threshold":  100,
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
                "too_high": "Don't arch your lower back – brace your core",
                "too_low":  "Stand tall – slight lean is ok",
            },
        },
        "tips": [
            "Start with elbows at 90° at shoulder height",
            "Don't arch your back – tighten your core",
            "Press directly overhead, not forward",
        ],
    },

    # ─────────────────────────────────────────
    #  LATERAL RAISE
    # ─────────────────────────────────────────
    "lateral_raise": {
        "name": "Lateral Raise",
        "muscles": ["medial deltoid"],
        "joints_to_check": ["left_shoulder", "right_shoulder", "trunk"],
        "target_angles": {
            "left_shoulder_up":   90,
            "right_shoulder_up":  90,
            "left_shoulder_down": 10,
            "right_shoulder_down":10,
            "trunk":               5,
        },
        "tolerance_deg": {
            "left_shoulder":  15,
            "right_shoulder": 15,
            "trunk":          10,
        },
        "rep_counter": {
            "joint":          "left_shoulder",
            "up_threshold":   75,
            "down_threshold": 30,
        },
        "corrections": {
            "left_shoulder": {
                "too_high": "Don't raise above shoulder height – risk of impingement",
                "too_low":  "Raise arms to shoulder level (90°)",
            },
            "right_shoulder": {
                "too_high": "Don't raise above shoulder height",
                "too_low":  "Raise arms to shoulder level",
            },
            "trunk": {
                "too_high": "Stop swinging – lighter weight or slower tempo",
                "too_low":  "Stand straight",
            },
        },
        "tips": [
            "Lead with your elbows, not your wrists",
            "Slight bend in the elbow is fine",
            "Go light – this isolates a small muscle",
        ],
    },

    # ─────────────────────────────────────────
    #  DEADLIFT
    # ─────────────────────────────────────────
    "deadlift": {
        "name": "Deadlift",
        "muscles": ["hamstrings", "glutes", "lower back", "traps"],
        "joints_to_check": ["left_hip", "right_hip", "left_knee", "right_knee", "trunk"],
        "target_angles": {
            "left_hip_down":   45,
            "right_hip_down":  45,
            "left_hip_up":    170,
            "right_hip_up":   170,
            "left_knee":      160,   # slight bend throughout
            "right_knee":     160,
            "trunk":           10,   # neutral spine
        },
        "tolerance_deg": {
            "left_hip":   15,
            "right_hip":  15,
            "left_knee":  20,
            "right_knee": 20,
            "trunk":      12,
        },
        "rep_counter": {
            "joint":          "left_hip",
            "up_threshold":   155,
            "down_threshold":  80,
        },
        "corrections": {
            "left_hip": {
                "too_high": "Hinge deeper at the hip – push hips back",
                "too_low":  "Don't round your lower back – hip angle too acute",
            },
            "trunk": {
                "too_high": "CRITICAL: Straighten your back immediately!",
                "too_low":  "Keep a neutral spine – don't hyperextend",
            },
            "left_knee": {
                "too_high": "Keep a slight bend in your knees",
                "too_low":  "Don't squat the deadlift – hinge at the hip",
            },
        },
        "tips": [
            "Neutral spine throughout – no rounding!",
            "Bar (or weights) close to your body",
            "Push the floor away, don't pull the weight up",
            "Squeeze glutes at the top",
        ],
    },

    # ─────────────────────────────────────────
    #  LUNGE
    # ─────────────────────────────────────────
    "lunge": {
        "name": "Lunge",
        "muscles": ["quadriceps", "glutes", "hamstrings"],
        "joints_to_check": ["left_knee", "right_knee", "left_hip", "trunk"],
        "target_angles": {
            "left_knee_down":   90,
            "right_knee_down":  90,
            "left_knee_up":    170,
            "right_knee_up":   170,
            "left_hip":         90,
            "trunk":             5,
        },
        "tolerance_deg": {
            "left_knee":  15,
            "right_knee": 15,
            "left_hip":   20,
            "trunk":      10,
        },
        "rep_counter": {
            "joint":          "left_knee",
            "up_threshold":   155,
            "down_threshold": 110,
        },
        "corrections": {
            "left_knee": {
                "too_high": "Step further forward – front knee at 90°",
                "too_low":  "Front knee shouldn't go past your toes",
            },
            "right_knee": {
                "too_high": "Lower your back knee closer to the floor",
                "too_low":  "Back knee too close to floor – control the descent",
            },
            "trunk": {
                "too_high": "Keep your torso upright",
                "too_low":  "Don't lean too far forward",
            },
        },
        "tips": [
            "Keep front knee directly over your ankle",
            "Back knee hovers just above the floor",
            "Step far enough that both knees reach 90°",
        ],
    },

    # ─────────────────────────────────────────
    #  PLANK (static – checks form only)
    # ─────────────────────────────────────────
    "plank": {
        "name": "Plank",
        "muscles": ["core", "shoulders", "glutes"],
        "joints_to_check": ["left_elbow", "right_elbow", "trunk", "left_hip", "right_hip"],
        "target_angles": {
            "left_elbow":   90,
            "right_elbow":  90,
            "trunk":         5,
            "left_hip":    175,
            "right_hip":   175,
        },
        "tolerance_deg": {
            "left_elbow":  15,
            "right_elbow": 15,
            "trunk":        8,
            "left_hip":    10,
            "right_hip":   10,
        },
        "rep_counter": None,   # timed hold – no rep counting
        "corrections": {
            "trunk": {
                "too_high": "Hips sagging – lift your hips and brace core",
                "too_low":  "Hips too high – lower into a straight line",
            },
            "left_hip": {
                "too_high": "Keep hips in line with your body",
                "too_low":  "Don't piked your hips up",
            },
        },
        "tips": [
            "Squeeze every muscle: glutes, abs, quads",
            "Breathe steadily – don't hold your breath",
            "Gaze at the floor slightly in front of hands",
        ],
    },
}


def get_exercise(name: str):
    """Returns exercise config dict or None."""
    return EXERCISES.get(name)


def list_exercises():
    return {k: v["name"] for k, v in EXERCISES.items()}
