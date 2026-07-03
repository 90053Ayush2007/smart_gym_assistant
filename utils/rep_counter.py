"""
rep_counter.py
--------------
Robust rep counter with:
  1. Angle smoothing buffer (no single-frame spikes)
  2. Hysteresis thresholds (prevents double counting)
  3. Minimum hold time (must stay in position briefly)
  4. Analytics per session
"""

import time
from collections import deque


class RepCounter:
    STATE_WAITING = "waiting"
    STATE_DOWN    = "down"
    STATE_UP      = "up"

    def __init__(
        self,
        up_threshold:   float,
        down_threshold: float,
        buffer_size:    int   = 5,
        hold_frames:    int   = 3,
        hysteresis:     float = 8.0,
    ):
        self.up_threshold   = up_threshold
        self.down_threshold = down_threshold
        self.buffer_size    = buffer_size
        self.hold_frames    = hold_frames
        self.hysteresis     = hysteresis

        self.state          = self.STATE_WAITING
        self.reps           = 0
        self.angle_buffer   = deque(maxlen=buffer_size)
        self.hold_counter   = 0
        self.pending_state  = None
        self.history        = []
        self.rep_timestamps = []
        self._start_time    = time.time()
        self.debug_info     = {}

    def update(self, raw_angle: float) -> dict:
        # Smooth angle
        self.angle_buffer.append(raw_angle)
        smoothed = sum(self.angle_buffer) / len(self.angle_buffer)
        self.history.append((time.time(), smoothed))

        rep_just_counted = False

        if self.state == self.STATE_WAITING:
            if smoothed >= self.down_threshold:
                self._try_transition(self.STATE_DOWN, smoothed)
            else:
                self.hold_counter  = 0
                self.pending_state = None

        elif self.state == self.STATE_DOWN:
            if smoothed <= (self.up_threshold + self.hysteresis):
                self._try_transition(self.STATE_UP, smoothed)
            else:
                if self.pending_state == self.STATE_UP:
                    self.hold_counter  = 0
                    self.pending_state = None

        elif self.state == self.STATE_UP:
            if smoothed >= (self.down_threshold - self.hysteresis):
                if self._try_transition(self.STATE_DOWN, smoothed):
                    self.reps += 1
                    self.rep_timestamps.append(time.time())
                    rep_just_counted = True
            else:
                if self.pending_state == self.STATE_DOWN:
                    self.hold_counter  = 0
                    self.pending_state = None

        self.debug_info = {
            "raw":      round(raw_angle, 1),
            "smoothed": round(smoothed, 1),
            "up_th":    self.up_threshold,
            "down_th":  self.down_threshold,
            "hold":     f"{self.hold_counter}/{self.hold_frames}",
            "pending":  self.pending_state or "none",
        }

        return {
            "reps":             self.reps,
            "state":            self.state,
            "rep_just_counted": rep_just_counted,
            "angle":            round(smoothed, 1),
            "raw_angle":        round(raw_angle, 1),
            "debug":            self.debug_info,
        }

    def _try_transition(self, new_state: str, angle: float) -> bool:
        if self.pending_state == new_state:
            self.hold_counter += 1
        else:
            self.pending_state = new_state
            self.hold_counter  = 1

        if self.hold_counter >= self.hold_frames:
            self.state         = new_state
            self.hold_counter  = 0
            self.pending_state = None
            return True
        return False

    def reset(self):
        self.state          = self.STATE_WAITING
        self.reps           = 0
        self.angle_buffer.clear()
        self.hold_counter   = 0
        self.pending_state  = None
        self.history        = []
        self.rep_timestamps = []
        self._start_time    = time.time()
        self.debug_info     = {}

    def session_stats(self) -> dict:
        if len(self.history) < 2:
            return {"total_reps": self.reps}
        angles   = [a for _, a in self.history]
        duration = self.history[-1][0] - self.history[0][0]
        if len(self.rep_timestamps) >= 2:
            intervals    = [
                self.rep_timestamps[i+1] - self.rep_timestamps[i]
                for i in range(len(self.rep_timestamps)-1)
            ]
            avg_rep_time = round(sum(intervals) / len(intervals), 1)
        else:
            avg_rep_time = 0
        return {
            "total_reps":      self.reps,
            "min_angle":       round(min(angles), 1),
            "max_angle":       round(max(angles), 1),
            "avg_angle":       round(sum(angles) / len(angles), 1),
            "duration_sec":    round(duration, 1),
            "avg_sec_per_rep": avg_rep_time,
        }