"""
pose_correction.py
------------------
Computes form score (0-100) by comparing observed angles
to target angles for the current phase of movement.

KEY FIX: Form score now accounts for rep state properly.
- During DOWN phase: compare to _down targets
- During UP phase:   compare to _up targets
- During WAITING:    compare to _down targets (starting position)

Also fixes:
- Wider tolerances so good form scores high
- Phase-aware scoring (curl at top vs bottom judged differently)
- Weighted joints (some joints matter more than others)
- Score smoothing so it doesn't jump wildly frame to frame
"""

from exercises.exercise_db import get_exercise
from collections import deque


# Smooth form score over last N frames so it doesn't flicker
_score_buffer = deque(maxlen=8)


def evaluate_pose(
    exercise_key: str,
    observed_angles: dict,
    rep_state: str = "waiting"
) -> dict:
    """
    Parameters
    ----------
    exercise_key    : e.g. "bicep_curl"
    observed_angles : output of get_all_angles()
    rep_state       : "up" | "down" | "waiting"

    Returns
    -------
    {
        form_score   : int 0-100
        corrections  : [str]
        joint_status : {joint: "ok"|"too_high"|"too_low"}
        color        : "green"|"yellow"|"red"
    }
    """
    global _score_buffer

    ex = get_exercise(exercise_key)
    if ex is None:
        return {
            "form_score":   0,
            "corrections":  ["Unknown exercise"],
            "joint_status": {},
            "color":        "red",
        }

    targets    = ex["target_angles"]
    tolerances = ex["tolerance_deg"]
    corr_db    = ex["corrections"]
    joints     = ex["joints_to_check"]

    # Joint importance weights
    # Key joints matter more than secondary ones
    WEIGHTS = {
        "left_elbow":     2.0,
        "right_elbow":    2.0,
        "left_knee":      2.0,
        "right_knee":     2.0,
        "left_hip":       2.0,
        "right_hip":      2.0,
        "left_shoulder":  1.0,
        "right_shoulder": 1.0,
        "trunk":          1.5,   # important for safety
        "left_ankle":     0.5,
        "right_ankle":    0.5,
    }

    corrections  = []
    joint_status = {}
    total_penalty   = 0.0
    total_weight    = 0.0

    for joint in joints:
        observed = observed_angles.get(joint)
        if observed is None:
            continue

        # ── Pick correct target based on rep phase ────────────
        # Try phase-specific target first, fall back to plain
        if rep_state == "up":
            target_key = f"{joint}_up"
        else:
            target_key = f"{joint}_down"

        if target_key in targets:
            target = targets[target_key]
        elif joint in targets:
            target = targets[joint]
        else:
            continue   # no target for this joint — skip

        tol    = tolerances.get(joint, 25)   # default 25° tolerance
        weight = WEIGHTS.get(joint, 1.0)
        diff   = observed - target

        total_weight += weight

        if abs(diff) <= tol:
            # Within tolerance — perfect
            joint_status[joint] = "ok"

        elif diff > tol:
            # Angle too HIGH
            joint_status[joint] = "too_high"
            # Penalty proportional to how far outside tolerance
            excess  = diff - tol
            # Cap penalty at 50° excess
            penalty = min(excess / 50.0, 1.0) * weight
            total_penalty += penalty

            msg = corr_db.get(joint, {}).get("too_high")
            if msg:
                corrections.append(msg)

        else:
            # Angle too LOW
            joint_status[joint] = "too_low"
            excess  = tol - diff   # diff is negative so tol-diff > tol
            penalty = min(excess / 50.0, 1.0) * weight
            total_penalty += penalty

            msg = corr_db.get(joint, {}).get("too_low")
            if msg:
                corrections.append(msg)

    # ── Compute raw score ─────────────────────────────────────
    if total_weight == 0:
        raw_score = 100
    else:
        # penalty_ratio: 0 = perfect, 1 = worst possible
        penalty_ratio = total_penalty / total_weight
        raw_score     = max(0, round(100 - penalty_ratio * 100))

    # ── Smooth score over last 8 frames ──────────────────────
    # Prevents score from jumping 40 points in one frame
    _score_buffer.append(raw_score)
    form_score = round(sum(_score_buffer) / len(_score_buffer))

    # ── Deduplicate corrections ───────────────────────────────
    seen   = set()
    unique = []
    for c in corrections:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    # ── Color coding ──────────────────────────────────────────
    if form_score >= 75:
        color = "green"
    elif form_score >= 50:
        color = "yellow"
    else:
        color = "red"

    return {
        "form_score":   form_score,
        "corrections":  unique,
        "joint_status": joint_status,
        "color":        color,
    }


def reset_score_buffer():
    """Call when changing exercise to clear smoothing buffer."""
    global _score_buffer
    _score_buffer.clear()