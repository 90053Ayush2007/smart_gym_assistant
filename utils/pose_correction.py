"""
pose_correction.py
------------------
Compares observed joint angles to exercise targets and generates
human-readable correction messages + a form score (0-100).
"""

from exercises.exercise_db import get_exercise


def evaluate_pose(exercise_key: str, observed_angles: dict, rep_state: str = "down") -> dict:
    """
    Parameters
    ----------
    exercise_key    : key into EXERCISES dict  e.g. "squat"
    observed_angles : output of pose_angles.get_all_angles()
    rep_state       : "up" | "down" | "waiting"  (from RepCounter)

    Returns
    -------
    {
        "form_score":    int,            # 0-100
        "corrections":   [str],          # list of feedback messages
        "joint_status":  {joint: "ok"|"too_high"|"too_low"},
        "color":         "green"|"yellow"|"red",
    }
    """
    ex = get_exercise(exercise_key)
    if ex is None:
        return {"form_score": 0, "corrections": ["Unknown exercise"], "joint_status": {}, "color": "red"}

    targets    = ex["target_angles"]
    tolerances = ex["tolerance_deg"]
    corr_db    = ex["corrections"]
    joints     = ex["joints_to_check"]

    corrections  = []
    joint_status = {}
    penalty      = 0

    for joint in joints:
        observed = observed_angles.get(joint)
        if observed is None:
            continue

        # Pick the right target depending on whether we're at the top or bottom
        # Exercises define e.g. "left_knee_up" and "left_knee_down"
        target_key_state = f"{joint}_{rep_state}"
        target_key_plain = joint

        if target_key_state in targets:
            target = targets[target_key_state]
        elif target_key_plain in targets:
            target = targets[target_key_plain]
        else:
            continue

        tol = tolerances.get(joint, 20)
        diff = observed - target

        if abs(diff) <= tol:
            joint_status[joint] = "ok"
        elif diff > tol:
            joint_status[joint] = "too_high"
            penalty += min(diff - tol, 40)
            msg = corr_db.get(joint, {}).get("too_high")
            if msg:
                corrections.append(msg)
        else:
            joint_status[joint] = "too_low"
            penalty += min(tol - diff, 40)  # tol - diff because diff is negative
            msg = corr_db.get(joint, {}).get("too_low")
            if msg:
                corrections.append(msg)

    # Deduplicate corrections
    seen = set()
    unique_corrections = []
    for c in corrections:
        if c not in seen:
            seen.add(c)
            unique_corrections.append(c)

    # Score: start at 100, subtract penalty (capped per joint)
    max_penalty = len(joints) * 40
    form_score  = max(0, round(100 - (penalty / max(max_penalty, 1)) * 100))

    if form_score >= 80:
        color = "green"
    elif form_score >= 50:
        color = "yellow"
    else:
        color = "red"

    return {
        "form_score":   form_score,
        "corrections":  unique_corrections,
        "joint_status": joint_status,
        "color":        color,
    }
