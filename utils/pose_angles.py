"""
pose_angles.py
--------------
Computes joint angles from BlazePose landmarks (33 keypoints).
Uses the same landmark indices as Google ML Kit / MediaPipe BlazePose.

Landmark indices (from slide 40 of the PDF):
  0: Nose           11: Left shoulder    23: Left hip
  1-10: Face        12: Right shoulder   24: Right hip
  11: L_shoulder    13: Left elbow       25: Left knee
  12: R_shoulder    14: Right elbow      26: Right knee
  13: L_elbow       15: Left wrist       27: Left ankle
  14: R_elbow       16: Right wrist      28: Right ankle
  ...               23: Left hip         ...
"""

import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose
PoseLandmark = mp_pose.PoseLandmark


def _vec(a, b):
    """Vector from point a to point b."""
    return np.array([b[0] - a[0], b[1] - a[1], b[2] - a[2]])


def angle_between(a, b, c):
    """
    Returns the angle (degrees) at joint B, formed by points A-B-C.
    Works in 3D using the landmark's x,y,z coordinates.
    """
    ba = _vec(b, a)
    bc = _vec(b, c)
    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def lm_to_xyz(landmarks, idx):
    """Extract (x, y, z) from a MediaPipe NormalizedLandmarkList."""
    lm = landmarks[idx]
    return (lm.x, lm.y, lm.z)


# ─────────────────────────────────────────────
#  Named angle extractors
# ─────────────────────────────────────────────

def get_all_angles(landmarks):
    """
    Given a list of 33 MediaPipe BlazePose landmarks,
    returns a dict of joint-angle names → degrees.
    """
    L = landmarks  # shorthand

    def xyz(idx):
        return lm_to_xyz(L, idx)

    angles = {}

    # ── Elbow angles ──────────────────────────────────────────
    angles["left_elbow"] = angle_between(
        xyz(PoseLandmark.LEFT_SHOULDER),
        xyz(PoseLandmark.LEFT_ELBOW),
        xyz(PoseLandmark.LEFT_WRIST),
    )
    angles["right_elbow"] = angle_between(
        xyz(PoseLandmark.RIGHT_SHOULDER),
        xyz(PoseLandmark.RIGHT_ELBOW),
        xyz(PoseLandmark.RIGHT_WRIST),
    )

    # ── Shoulder angles ───────────────────────────────────────
    angles["left_shoulder"] = angle_between(
        xyz(PoseLandmark.LEFT_ELBOW),
        xyz(PoseLandmark.LEFT_SHOULDER),
        xyz(PoseLandmark.LEFT_HIP),
    )
    angles["right_shoulder"] = angle_between(
        xyz(PoseLandmark.RIGHT_ELBOW),
        xyz(PoseLandmark.RIGHT_SHOULDER),
        xyz(PoseLandmark.RIGHT_HIP),
    )

    # ── Hip angles ────────────────────────────────────────────
    angles["left_hip"] = angle_between(
        xyz(PoseLandmark.LEFT_SHOULDER),
        xyz(PoseLandmark.LEFT_HIP),
        xyz(PoseLandmark.LEFT_KNEE),
    )
    angles["right_hip"] = angle_between(
        xyz(PoseLandmark.RIGHT_SHOULDER),
        xyz(PoseLandmark.RIGHT_HIP),
        xyz(PoseLandmark.RIGHT_KNEE),
    )

    # ── Knee angles ───────────────────────────────────────────
    angles["left_knee"] = angle_between(
        xyz(PoseLandmark.LEFT_HIP),
        xyz(PoseLandmark.LEFT_KNEE),
        xyz(PoseLandmark.LEFT_ANKLE),
    )
    angles["right_knee"] = angle_between(
        xyz(PoseLandmark.RIGHT_HIP),
        xyz(PoseLandmark.RIGHT_KNEE),
        xyz(PoseLandmark.RIGHT_ANKLE),
    )

    # ── Ankle angles ──────────────────────────────────────────
    angles["left_ankle"] = angle_between(
        xyz(PoseLandmark.LEFT_KNEE),
        xyz(PoseLandmark.LEFT_ANKLE),
        xyz(PoseLandmark.LEFT_FOOT_INDEX),
    )
    angles["right_ankle"] = angle_between(
        xyz(PoseLandmark.RIGHT_KNEE),
        xyz(PoseLandmark.RIGHT_ANKLE),
        xyz(PoseLandmark.RIGHT_FOOT_INDEX),
    )

    # ── Wrist / forearm (useful for curls) ────────────────────
    angles["left_wrist"] = angle_between(
        xyz(PoseLandmark.LEFT_ELBOW),
        xyz(PoseLandmark.LEFT_WRIST),
        xyz(PoseLandmark.LEFT_INDEX),
    )
    angles["right_wrist"] = angle_between(
        xyz(PoseLandmark.RIGHT_ELBOW),
        xyz(PoseLandmark.RIGHT_WRIST),
        xyz(PoseLandmark.RIGHT_INDEX),
    )

    # ── Trunk / torso lean (spine proxy) ─────────────────────
    # Angle at mid-hip between mid-shoulder and vertical
    mid_shoulder = np.mean([
        [L[PoseLandmark.LEFT_SHOULDER].x, L[PoseLandmark.LEFT_SHOULDER].y, L[PoseLandmark.LEFT_SHOULDER].z],
        [L[PoseLandmark.RIGHT_SHOULDER].x, L[PoseLandmark.RIGHT_SHOULDER].y, L[PoseLandmark.RIGHT_SHOULDER].z],
    ], axis=0)
    mid_hip = np.mean([
        [L[PoseLandmark.LEFT_HIP].x, L[PoseLandmark.LEFT_HIP].y, L[PoseLandmark.LEFT_HIP].z],
        [L[PoseLandmark.RIGHT_HIP].x, L[PoseLandmark.RIGHT_HIP].y, L[PoseLandmark.RIGHT_HIP].z],
    ], axis=0)
    # virtual point directly below mid_hip
    below_hip = mid_hip.copy()
    below_hip[1] += 0.1  # y increases downward in image space
    angles["trunk"] = angle_between(
        tuple(mid_shoulder), tuple(mid_hip), tuple(below_hip)
    )

    return angles
