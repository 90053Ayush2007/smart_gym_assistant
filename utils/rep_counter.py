"""
rep_counter.py
--------------
A simple finite-state-machine rep counter.

State machine:
  WAITING  → angle crosses down_threshold  → DOWN
  DOWN     → angle crosses up_threshold    → UP
  UP       → angle crosses down_threshold  → DOWN  (rep counted!)

Works with any oscillating joint angle (e.g. elbow for curls, knee for squats).
"""

import time


class RepCounter:
    STATE_WAITING = "waiting"
    STATE_DOWN    = "down"
    STATE_UP      = "up"

    def __init__(self, up_threshold: float, down_threshold: float):
        """
        up_threshold   – angle (°) that marks the 'top' of the movement
        down_threshold – angle (°) that marks the 'bottom' / extended position

        For a bicep curl:
            up_threshold   =  55  (arm curled, elbow angle small)
            down_threshold = 150  (arm extended, elbow angle large)

        For a squat:
            up_threshold   = 160  (standing)
            down_threshold = 110  (parallel depth)
        """
        self.up_threshold   = up_threshold
        self.down_threshold = down_threshold

        self.state    = self.STATE_WAITING
        self.reps     = 0
        self.history  = []   # list of (timestamp, angle) for analytics
        self._partial = False  # True once we've seen the DOWN state

    def update(self, angle: float) -> dict:
        """
        Feed the current joint angle.
        Returns a dict with:
          reps       – cumulative rep count
          state      – current FSM state
          rep_just_counted – True if a rep was completed this frame
        """
        rep_just_counted = False
        self.history.append((time.time(), angle))

        if self.state == self.STATE_WAITING:
            # Wait for the user to reach the starting position
            if angle >= self.down_threshold:
                self.state = self.STATE_DOWN
                self._partial = True

        elif self.state == self.STATE_DOWN:
            # Extended / bottom position → wait for contraction
            if angle <= self.up_threshold:
                self.state = self.STATE_UP

        elif self.state == self.STATE_UP:
            # Contracted / top position → return to bottom = 1 rep
            if angle >= self.down_threshold:
                self.reps += 1
                self.state = self.STATE_DOWN
                rep_just_counted = True

        return {
            "reps":             self.reps,
            "state":            self.state,
            "rep_just_counted": rep_just_counted,
            "angle":            round(angle, 1),
        }

    def reset(self):
        self.state   = self.STATE_WAITING
        self.reps    = 0
        self.history = []
        self._partial = False

    def session_stats(self) -> dict:
        """Basic analytics over the session."""
        if len(self.history) < 2:
            return {}
        angles = [a for _, a in self.history]
        return {
            "total_reps":   self.reps,
            "min_angle":    round(min(angles), 1),
            "max_angle":    round(max(angles), 1),
            "avg_angle":    round(sum(angles) / len(angles), 1),
            "duration_sec": round(self.history[-1][0] - self.history[0][0], 1),
        }
