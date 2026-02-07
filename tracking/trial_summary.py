"""Trial summary exporter for generating clean CSV/JSON trial data."""

import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, asdict

if TYPE_CHECKING:
    from .kinematics import TrialMetrics


@dataclass
class TrialRecord:
    """A single trial record with all biomechanical metrics."""
    trial_number: int
    timestamp: str
    elapsed_seconds: float

    # Finger info
    target_finger: str
    pressed_finger: str
    is_wrong_finger: bool

    # Timing
    reaction_time_ms: float

    # Position-based metrics (raw 3D fingertip movement)
    motion_leakage_ratio: float
    target_path_length_mm: float
    total_non_target_path_length_mm: float
    is_clean_trial: bool

    # Angle-based metrics (finger flexion, immune to hand repositioning)
    angle_based_mlr: float
    target_angle_path_deg: float
    total_non_target_angle_path_deg: float
    is_clean_trial_angle: bool

    # Other
    coupled_keypress: bool


@dataclass
class SessionSummary:
    """Session-level summary statistics."""
    session_id: str
    start_time: str
    end_time: str
    duration_seconds: float
    game_mode: str # New field

    # Trial counts
    total_trials: int
    correct_trials: int
    wrong_finger_trials: int
    clean_trials: int
    clean_trials_angle: int
    coupled_keypress_trials: int

    # Rates (percentages)
    wrong_finger_error_rate: float
    clean_trial_rate: float
    clean_trial_rate_angle: float
    coupled_keypress_rate: float

    # Position-based averages
    avg_reaction_time_ms: float
    avg_motion_leakage_ratio: float

    # Angle-based averages
    avg_angle_based_mlr: float

    # Score
    final_score: int


class TrialSummaryExporter:
    """Exports trial data to clean CSV and JSON formats."""

    def __init__(self, output_directory: str = "data/session_logs"):
        """
        Initialize the exporter.

        Args:
            output_directory: Directory to save summary files
        """
        self.output_directory = output_directory
        self.session_id: Optional[str] = None
        self.session_start_time: Optional[datetime] = None
        self.session_start_timestamp: Optional[float] = None
        self.trials: List[TrialRecord] = []

        os.makedirs(output_directory, exist_ok=True)

    def start_session(self):
        """Start a new session for recording trials."""
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_start_time = datetime.now()
        self.session_start_timestamp = datetime.now().timestamp()
        self.trials = []
        print(f"Trial summary session started: {self.session_id}")

    def record_trial(
        self,
        target_finger: str,
        pressed_finger: str,
        trial_metrics: 'TrialMetrics',
        timestamp: Optional[datetime] = None
    ):
        """
        Record a single trial with its metrics.

        Args:
            target_finger: The finger assigned to the missile
            pressed_finger: The finger the player pressed
            trial_metrics: Biomechanical metrics from KinematicsProcessor
            timestamp: Optional timestamp (defaults to now)
        """
        if not self.session_id:
            return

        now = timestamp or datetime.now()
        elapsed = (now.timestamp() - self.session_start_timestamp) if self.session_start_timestamp else 0

        trial = TrialRecord(
            trial_number=len(self.trials) + 1,
            timestamp=now.isoformat(),
            elapsed_seconds=round(elapsed, 3),
            target_finger=target_finger,
            pressed_finger=pressed_finger,
            is_wrong_finger=trial_metrics.is_wrong_finger,
            reaction_time_ms=round(trial_metrics.reaction_time_ms, 2),
            # Position-based metrics
            motion_leakage_ratio=round(trial_metrics.motion_leakage_ratio, 4),
            target_path_length_mm=round(trial_metrics.target_path_length, 2),
            total_non_target_path_length_mm=round(
                sum(trial_metrics.non_target_path_lengths.values()), 2
            ),
            is_clean_trial=trial_metrics.is_clean_trial,
            # Angle-based metrics
            angle_based_mlr=round(trial_metrics.angle_based_mlr, 4),
            target_angle_path_deg=round(trial_metrics.target_angle_path, 2),
            total_non_target_angle_path_deg=round(
                sum(trial_metrics.non_target_angle_paths.values()), 2
            ),
            is_clean_trial_angle=trial_metrics.is_clean_trial_angle,
            # Other
            coupled_keypress=trial_metrics.coupled_keypress
        )

        self.trials.append(trial)

    def _calculate_summary(self, final_score: int = 0, game_mode: str = "Unknown") -> SessionSummary:
        """Calculate session summary statistics."""
        total = len(self.trials)

        if total == 0:
            return SessionSummary(
                session_id=self.session_id or "",
                start_time=self.session_start_time.isoformat() if self.session_start_time else "",
                end_time=datetime.now().isoformat(),
                duration_seconds=0,
                game_mode=game_mode,
                total_trials=0,
                correct_trials=0,
                wrong_finger_trials=0,
                clean_trials=0,
                clean_trials_angle=0,
                coupled_keypress_trials=0,
                wrong_finger_error_rate=0.0,
                clean_trial_rate=0.0,
                clean_trial_rate_angle=0.0,
                coupled_keypress_rate=0.0,
                avg_reaction_time_ms=0.0,
                avg_motion_leakage_ratio=0.0,
                avg_angle_based_mlr=0.0,
                final_score=final_score
            )

        wrong_finger_count = sum(1 for t in self.trials if t.is_wrong_finger)
        clean_count = sum(1 for t in self.trials if t.is_clean_trial)
        clean_count_angle = sum(1 for t in self.trials if t.is_clean_trial_angle)
        coupled_count = sum(1 for t in self.trials if t.coupled_keypress)

        # Filter valid position-based MLR values (not inf)
        valid_mlr = [t.motion_leakage_ratio for t in self.trials
                     if t.motion_leakage_ratio != float('inf')]
        avg_mlr = sum(valid_mlr) / len(valid_mlr) if valid_mlr else 0.0

        # Filter valid angle-based MLR values (not inf)
        valid_angle_mlr = [t.angle_based_mlr for t in self.trials
                          if t.angle_based_mlr != float('inf')]
        avg_angle_mlr = sum(valid_angle_mlr) / len(valid_angle_mlr) if valid_angle_mlr else 0.0

        # Filter valid reaction times (positive)
        valid_rt = [t.reaction_time_ms for t in self.trials if t.reaction_time_ms > 0]
        avg_rt = sum(valid_rt) / len(valid_rt) if valid_rt else 0.0

        end_time = datetime.now()
        duration = (end_time.timestamp() - self.session_start_timestamp) if self.session_start_timestamp else 0

        return SessionSummary(
            session_id=self.session_id or "",
            start_time=self.session_start_time.isoformat() if self.session_start_time else "",
            end_time=end_time.isoformat(),
            duration_seconds=round(duration, 2),
            total_trials=total,
            correct_trials=total - wrong_finger_count,
            wrong_finger_trials=wrong_finger_count,
            clean_trials=clean_count,
            clean_trials_angle=clean_count_angle,
            coupled_keypress_trials=coupled_count,
            wrong_finger_error_rate=round((wrong_finger_count / total) * 100, 2),
            clean_trial_rate=round((clean_count / total) * 100, 2),
            clean_trial_rate_angle=round((clean_count_angle / total) * 100, 2),
            coupled_keypress_rate=round((coupled_count / total) * 100, 2),
            avg_reaction_time_ms=round(avg_rt, 2),
            avg_motion_leakage_ratio=round(avg_mlr, 4),
            avg_angle_based_mlr=round(avg_angle_mlr, 4),
            final_score=final_score
        )

    def end_session(self, final_score: int = 0, game_mode: str = "Unknown") -> Dict[str, str]:
        """
        End the session and export trial summary files.

        Args:
            final_score: Final game score
            game_mode: The game mode that was played

        Returns:
            Dictionary with paths to generated files
        """
        if not self.session_id:
            return {}

        summary = self._calculate_summary(final_score, game_mode)

        # Generate file paths
        base_name = f"trials_{self.session_id}"
        csv_path = os.path.join(self.output_directory, f"{base_name}.csv")
        json_path = os.path.join(self.output_directory, f"{base_name}.json")

        # Export CSV
        self._export_csv(csv_path, summary)

        # Export JSON
        self._export_json(json_path, summary)

        print(f"\nTrial Summary Exported:")
        print(f"  CSV:  {csv_path}")
        print(f"  JSON: {json_path}")
        print(f"\nSession Statistics:")
        print(f"  Total Trials:             {summary.total_trials}")
        print(f"  Wrong-Finger Error Rate:  {summary.wrong_finger_error_rate}%")
        print(f"  Coupled-Keypress Rate:    {summary.coupled_keypress_rate}%")
        print(f"  Avg Reaction Time:        {summary.avg_reaction_time_ms} ms")
        print(f"  --- Position-based ---")
        print(f"  Clean Trial Rate:         {summary.clean_trial_rate}%")
        print(f"  Avg MLR:                  {summary.avg_motion_leakage_ratio}")
        print(f"  --- Angle-based ---")
        print(f"  Clean Trial Rate (angle): {summary.clean_trial_rate_angle}%")
        print(f"  Avg MLR (angle):          {summary.avg_angle_based_mlr}")

        # Reset for next session
        result = {"csv": csv_path, "json": json_path}
        self.session_id = None
        self.session_start_time = None
        self.session_start_timestamp = None
        self.trials = []

        return result

    def _export_csv(self, filepath: str, summary: SessionSummary):
        """Export trials to CSV format."""
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow([
                'trial_number',
                'timestamp',
                'elapsed_seconds',
                'target_finger',
                'pressed_finger',
                'is_wrong_finger',
                'reaction_time_ms',
                'coupled_keypress',
                # Position-based
                'pos_mlr',
                'pos_target_path_mm',
                'pos_non_target_path_mm',
                'is_clean_trial_pos',
                # Angle-based
                'angle_mlr',
                'angle_target_path_deg',
                'angle_non_target_path_deg',
                'is_clean_trial_angle'
            ])

            # Write trial rows
            for trial in self.trials:
                writer.writerow([
                    trial.trial_number,
                    trial.timestamp,
                    trial.elapsed_seconds,
                    trial.target_finger,
                    trial.pressed_finger,
                    trial.is_wrong_finger,
                    trial.reaction_time_ms,
                    trial.coupled_keypress,
                    # Position-based
                    trial.motion_leakage_ratio,
                    trial.target_path_length_mm,
                    trial.total_non_target_path_length_mm,
                    trial.is_clean_trial,
                    # Angle-based
                    trial.angle_based_mlr,
                    trial.target_angle_path_deg,
                    trial.total_non_target_angle_path_deg,
                    trial.is_clean_trial_angle
                ])

            # Write blank row then summary
            writer.writerow([])
            writer.writerow(['--- SESSION SUMMARY ---'])
            writer.writerow(['session_id', summary.session_id])
            writer.writerow(['start_time', summary.start_time])
            writer.writerow(['end_time', summary.end_time])
            writer.writerow(['duration_seconds', summary.duration_seconds])
            writer.writerow(['game_mode', summary.game_mode])
            writer.writerow(['total_trials', summary.total_trials])
            writer.writerow(['correct_trials', summary.correct_trials])
            writer.writerow(['wrong_finger_trials', summary.wrong_finger_trials])
            writer.writerow(['coupled_keypress_trials', summary.coupled_keypress_trials])
            writer.writerow(['wrong_finger_error_rate_%', summary.wrong_finger_error_rate])
            writer.writerow(['coupled_keypress_rate_%', summary.coupled_keypress_rate])
            writer.writerow(['avg_reaction_time_ms', summary.avg_reaction_time_ms])
            writer.writerow(['--- Position-based ---'])
            writer.writerow(['clean_trials_pos', summary.clean_trials])
            writer.writerow(['clean_trial_rate_pos_%', summary.clean_trial_rate])
            writer.writerow(['avg_pos_mlr', summary.avg_motion_leakage_ratio])
            writer.writerow(['--- Angle-based ---'])
            writer.writerow(['clean_trials_angle', summary.clean_trials_angle])
            writer.writerow(['clean_trial_rate_angle_%', summary.clean_trial_rate_angle])
            writer.writerow(['avg_angle_mlr', summary.avg_angle_based_mlr])
            writer.writerow(['---'])
            writer.writerow(['final_score', summary.final_score])

    def _export_json(self, filepath: str, summary: SessionSummary):
        """Export trials to JSON format."""
        data = {
            "summary": asdict(summary),
            "trials": [asdict(trial) for trial in self.trials]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
