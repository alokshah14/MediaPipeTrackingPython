"""
Session Log Analyzer for MediaPipe Finger Individuation Game

This module provides tools to load, analyze, and visualize session data
from the finger individuation game. Use in Jupyter notebooks or standalone.

Usage:
    from analysis.session_analyzer import SessionAnalyzer

    analyzer = SessionAnalyzer()
    analyzer.load_session('session_logs/session_20260206_082618.json')
    analyzer.plot_session_overview()
    analyzer.plot_trial(1)
"""

import json
import os
import glob
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

# Plotting imports - will gracefully handle if not available
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.gridspec import GridSpec
    from mpl_toolkits.mplot3d import Axes3D
    from mpl_toolkits.mplot3d.art3d import Line3DCollection
    import matplotlib.animation as animation
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Install with: pip install matplotlib")

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Warning: pandas not installed. Install with: pip install pandas")


# Finger display configuration
FINGER_ORDER = [
    'left_pinky', 'left_ring', 'left_middle', 'left_index', 'left_thumb',
    'right_thumb', 'right_index', 'right_middle', 'right_ring', 'right_pinky'
]

FINGER_COLORS = {
    'left_pinky': '#FF6B6B',
    'left_ring': '#FFA94D',
    'left_middle': '#FFD93D',
    'left_index': '#6BCB77',
    'left_thumb': '#4D96FF',
    'right_thumb': '#4D96FF',
    'right_index': '#6BCB77',
    'right_middle': '#FFD93D',
    'right_ring': '#FFA94D',
    'right_pinky': '#FF6B6B',
}

FINGER_SHORT_NAMES = {
    'left_pinky': 'L5', 'left_ring': 'L4', 'left_middle': 'L3',
    'left_index': 'L2', 'left_thumb': 'L1',
    'right_thumb': 'R1', 'right_index': 'R2', 'right_middle': 'R3',
    'right_ring': 'R4', 'right_pinky': 'R5',
}


@dataclass
class Trial:
    """Represents a single trial (finger press event)."""
    number: int
    timestamp: str
    elapsed_seconds: float
    target_finger: str
    pressed_finger: str
    is_correct: bool
    score: int
    lives: int
    difficulty: str

    # Hand tracking data
    left_hand: Optional[Dict]
    right_hand: Optional[Dict]

    # Biomechanics (if available)
    reaction_time_ms: float = 0
    mlr: float = 0
    target_path_length: float = 0
    is_clean_trial: bool = False
    coupled_keypress: bool = False
    non_target_paths: Dict = None


class SessionAnalyzer:
    """Analyzer for session log files."""

    def __init__(self):
        self.session_data = None
        self.trials: List[Trial] = []
        self.session_file = None

    def load_session(self, filepath: str) -> bool:
        """
        Load a session log file.

        Args:
            filepath: Path to session JSON file

        Returns:
            True if loaded successfully
        """
        try:
            with open(filepath, 'r') as f:
                self.session_data = json.load(f)
            self.session_file = filepath
            self._parse_trials()
            print(f"Loaded session: {self.session_data.get('session_id', 'unknown')}")
            print(f"  Duration: {self.session_data.get('duration_seconds', 0):.1f}s")
            print(f"  Trials: {len(self.trials)}")
            return True
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading session: {e}")
            return False

    def _parse_trials(self):
        """Parse events into Trial objects."""
        self.trials = []
        trial_num = 0

        for event in self.session_data.get('events', []):
            if event.get('type') != 'finger_press':
                continue

            trial_num += 1

            # Extract hand data
            tracking = event.get('hand_tracking', {})
            left_hand = tracking.get('left_hand')
            right_hand = tracking.get('right_hand')

            # Extract biomechanics if available
            bio = event.get('biomechanics', {})

            trial = Trial(
                number=trial_num,
                timestamp=event.get('timestamp', ''),
                elapsed_seconds=event.get('elapsed_seconds', 0),
                target_finger=event.get('target_finger', ''),
                pressed_finger=event.get('finger_pressed', ''),
                is_correct=event.get('is_correct', False),
                score=event.get('game_state', {}).get('score', 0),
                lives=event.get('game_state', {}).get('lives', 0),
                difficulty=event.get('game_state', {}).get('difficulty', ''),
                left_hand=left_hand,
                right_hand=right_hand,
                reaction_time_ms=bio.get('reaction_time_ms', 0),
                mlr=bio.get('motion_leakage_ratio', 0),
                target_path_length=bio.get('target_path_length_mm', 0),
                is_clean_trial=bio.get('is_clean_trial', False),
                coupled_keypress=bio.get('coupled_keypress', False),
                non_target_paths=bio.get('non_target_path_lengths', {}),
            )
            self.trials.append(trial)

    def get_trial(self, trial_number: int) -> Optional[Trial]:
        """Get a specific trial by number (1-indexed)."""
        if 1 <= trial_number <= len(self.trials):
            return self.trials[trial_number - 1]
        return None

    def get_summary(self) -> Dict:
        """Get session summary statistics."""
        if not self.trials:
            return {}

        correct = sum(1 for t in self.trials if t.is_correct)
        clean = sum(1 for t in self.trials if t.is_clean_trial)
        coupled = sum(1 for t in self.trials if t.coupled_keypress)

        mlr_values = [t.mlr for t in self.trials if t.mlr > 0]
        rt_values = [t.reaction_time_ms for t in self.trials if t.reaction_time_ms > 0]

        return {
            'session_id': self.session_data.get('session_id', ''),
            'duration_seconds': self.session_data.get('duration_seconds', 0),
            'total_trials': len(self.trials),
            'correct_trials': correct,
            'accuracy': correct / len(self.trials) * 100 if self.trials else 0,
            'clean_trials': clean,
            'clean_rate': clean / len(self.trials) * 100 if self.trials else 0,
            'coupled_keypresses': coupled,
            'coupled_rate': coupled / len(self.trials) * 100 if self.trials else 0,
            'avg_mlr': np.mean(mlr_values) if mlr_values else 0,
            'avg_reaction_time_ms': np.mean(rt_values) if rt_values else 0,
            'final_score': self.session_data.get('final_score', 0),
        }

    def to_dataframe(self) -> 'pd.DataFrame':
        """Convert trials to pandas DataFrame."""
        if not HAS_PANDAS:
            raise ImportError("pandas is required for this function")

        data = []
        for t in self.trials:
            row = {
                'trial': t.number,
                'elapsed_s': t.elapsed_seconds,
                'target': t.target_finger,
                'pressed': t.pressed_finger,
                'correct': t.is_correct,
                'score': t.score,
                'lives': t.lives,
                'difficulty': t.difficulty,
                'reaction_time_ms': t.reaction_time_ms,
                'mlr': t.mlr,
                'path_length_mm': t.target_path_length,
                'clean_trial': t.is_clean_trial,
                'coupled': t.coupled_keypress,
            }
            data.append(row)

        return pd.DataFrame(data)

    # ========== Plotting Methods ==========

    def plot_session_overview(self, figsize: Tuple[int, int] = (14, 10)):
        """
        Plot comprehensive session overview with multiple subplots.

        Shows:
        - Trial timeline with correct/incorrect markers
        - Reaction time over trials
        - MLR over trials
        - Finger accuracy breakdown
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib is required for plotting")

        if not self.trials:
            print("No trials to plot")
            return

        fig = plt.figure(figsize=figsize)
        gs = GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3)

        # 1. Trial timeline
        ax1 = fig.add_subplot(gs[0, :])
        self._plot_trial_timeline(ax1)

        # 2. Reaction time over trials
        ax2 = fig.add_subplot(gs[1, 0])
        self._plot_reaction_times(ax2)

        # 3. MLR over trials
        ax3 = fig.add_subplot(gs[1, 1])
        self._plot_mlr(ax3)

        # 4. Finger accuracy
        ax4 = fig.add_subplot(gs[2, 0])
        self._plot_finger_accuracy(ax4)

        # 5. Score progression
        ax5 = fig.add_subplot(gs[2, 1])
        self._plot_score_progression(ax5)

        summary = self.get_summary()
        fig.suptitle(
            f"Session {summary['session_id']} | "
            f"{summary['total_trials']} trials | "
            f"{summary['accuracy']:.1f}% accuracy | "
            f"Score: {summary['final_score']}",
            fontsize=14, fontweight='bold'
        )

        plt.tight_layout()
        return fig

    def _plot_trial_timeline(self, ax):
        """Plot trial timeline with target/pressed fingers."""
        trials_x = [t.elapsed_seconds for t in self.trials]

        # Plot each trial as a point
        for t in self.trials:
            color = FINGER_COLORS.get(t.target_finger, 'gray')
            marker = 'o' if t.is_correct else 'x'
            size = 100 if t.is_correct else 150

            ax.scatter(t.elapsed_seconds, 0, c=[color], marker=marker, s=size,
                      edgecolors='black' if t.is_correct else 'red', linewidths=2)

            # Add finger label above
            ax.text(t.elapsed_seconds, 0.3, FINGER_SHORT_NAMES.get(t.target_finger, '?'),
                   ha='center', va='bottom', fontsize=8, rotation=45)

        ax.set_xlim(-1, max(trials_x) + 1)
        ax.set_ylim(-1, 1)
        ax.set_xlabel('Time (seconds)')
        ax.set_title('Trial Timeline (O=correct, X=wrong)')
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
        ax.set_yticks([])

        # Legend for finger colors
        patches = [mpatches.Patch(color=FINGER_COLORS[f], label=FINGER_SHORT_NAMES[f])
                  for f in FINGER_ORDER[:5]]  # Just left hand for legend
        ax.legend(handles=patches, loc='upper right', ncol=5, fontsize=8)

    def _plot_reaction_times(self, ax):
        """Plot reaction times over trials."""
        trial_nums = [t.number for t in self.trials]
        rts = [t.reaction_time_ms for t in self.trials]
        colors = ['green' if t.is_correct else 'red' for t in self.trials]

        ax.bar(trial_nums, rts, color=colors, alpha=0.7, edgecolor='black')
        ax.axhline(y=np.mean([r for r in rts if r > 0]), color='blue',
                  linestyle='--', label=f'Mean: {np.mean([r for r in rts if r > 0]):.0f}ms')
        ax.set_xlabel('Trial')
        ax.set_ylabel('Reaction Time (ms)')
        ax.set_title('Reaction Time per Trial')
        ax.legend()

    def _plot_mlr(self, ax):
        """Plot Motion Leakage Ratio over trials."""
        trial_nums = [t.number for t in self.trials]
        mlrs = [t.mlr for t in self.trials]
        colors = ['green' if t.is_clean_trial else 'orange' if t.mlr < 0.5 else 'red'
                 for t in self.trials]

        ax.bar(trial_nums, mlrs, color=colors, alpha=0.7, edgecolor='black')
        ax.axhline(y=0.10, color='green', linestyle='--', label='Clean threshold (0.10)')
        ax.set_xlabel('Trial')
        ax.set_ylabel('Motion Leakage Ratio')
        ax.set_title('MLR per Trial (lower = better isolation)')
        ax.legend()

    def _plot_finger_accuracy(self, ax):
        """Plot accuracy breakdown by finger."""
        finger_correct = {f: 0 for f in FINGER_ORDER}
        finger_total = {f: 0 for f in FINGER_ORDER}

        for t in self.trials:
            if t.target_finger in finger_total:
                finger_total[t.target_finger] += 1
                if t.is_correct:
                    finger_correct[t.target_finger] += 1

        fingers = [f for f in FINGER_ORDER if finger_total[f] > 0]
        accuracies = [finger_correct[f] / finger_total[f] * 100 if finger_total[f] > 0 else 0
                     for f in fingers]
        colors = [FINGER_COLORS[f] for f in fingers]
        labels = [FINGER_SHORT_NAMES[f] for f in fingers]

        bars = ax.bar(labels, accuracies, color=colors, edgecolor='black')
        ax.axhline(y=100, color='gray', linestyle='-', alpha=0.3)
        ax.set_ylabel('Accuracy (%)')
        ax.set_title('Accuracy by Finger')
        ax.set_ylim(0, 110)

        # Add count labels on bars
        for bar, finger in zip(bars, fingers):
            count = finger_total[finger]
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                   f'n={count}', ha='center', va='bottom', fontsize=8)

    def _plot_score_progression(self, ax):
        """Plot score progression over time."""
        times = [t.elapsed_seconds for t in self.trials]
        scores = [t.score for t in self.trials]

        ax.plot(times, scores, 'b-o', markersize=4)
        ax.fill_between(times, scores, alpha=0.3)
        ax.set_xlabel('Time (seconds)')
        ax.set_ylabel('Score')
        ax.set_title('Score Progression')

    def plot_trial(self, trial_number: int, figsize: Tuple[int, int] = (12, 8)):
        """
        Plot detailed view of a single trial including hand positions.

        Args:
            trial_number: Trial number (1-indexed)
            figsize: Figure size
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib is required for plotting")

        trial = self.get_trial(trial_number)
        if not trial:
            print(f"Trial {trial_number} not found")
            return

        fig, axes = plt.subplots(1, 2, figsize=figsize)

        # Left plot: Top-down view (X-Z plane)
        self._plot_hand_top_view(axes[0], trial)

        # Right plot: Side view (X-Y plane)
        self._plot_hand_side_view(axes[1], trial)

        # Title with trial info
        status = "CORRECT" if trial.is_correct else "WRONG"
        clean = " | CLEAN" if trial.is_clean_trial else ""
        fig.suptitle(
            f"Trial {trial.number}: Target={FINGER_SHORT_NAMES.get(trial.target_finger, '?')} | "
            f"Pressed={FINGER_SHORT_NAMES.get(trial.pressed_finger, '?')} | "
            f"{status}{clean}\n"
            f"RT={trial.reaction_time_ms:.0f}ms | MLR={trial.mlr:.3f}",
            fontsize=12, fontweight='bold'
        )

        plt.tight_layout()
        return fig

    def _plot_hand_top_view(self, ax, trial: Trial):
        """Plot top-down view of hands (X-Z plane)."""
        ax.set_title('Top View (X-Z plane)')
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Z (mm)')

        self._draw_hand(ax, trial.left_hand, 'left', trial.target_finger, 'xz')
        self._draw_hand(ax, trial.right_hand, 'right', trial.target_finger, 'xz')

        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        ax.axvline(x=0, color='gray', linestyle='-', alpha=0.5)

    def _plot_hand_side_view(self, ax, trial: Trial):
        """Plot side view of hands (X-Y plane)."""
        ax.set_title('Front View (X-Y plane)')
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm) - Height')

        self._draw_hand(ax, trial.left_hand, 'left', trial.target_finger, 'xy')
        self._draw_hand(ax, trial.right_hand, 'right', trial.target_finger, 'xy')

        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        ax.axvline(x=0, color='gray', linestyle='-', alpha=0.5)

    def _draw_hand(self, ax, hand_data: Optional[Dict], hand_type: str,
                   target_finger: str, plane: str):
        """Draw a hand on the given axes."""
        if hand_data is None:
            return

        palm = hand_data.get('palm_position', {})
        palm_x, palm_y, palm_z = palm.get('x', 0), palm.get('y', 0), palm.get('z', 0)

        if plane == 'xz':
            palm_plot = (palm_x, palm_z)
        else:  # xy
            palm_plot = (palm_x, palm_y)

        # Draw palm
        ax.scatter(*palm_plot, s=200, c='gray', alpha=0.5, marker='o', label=f'{hand_type} palm')

        # Draw fingers
        fingers = hand_data.get('fingers', {})
        for finger_name, finger_data in fingers.items():
            full_name = f"{hand_type}_{finger_name}"
            tip = finger_data.get('tip_position', {})
            tip_x, tip_y, tip_z = tip.get('x', 0), tip.get('y', 0), tip.get('z', 0)

            if plane == 'xz':
                tip_plot = (tip_x, tip_z)
            else:
                tip_plot = (tip_x, tip_y)

            color = FINGER_COLORS.get(full_name, 'gray')
            is_target = full_name == target_finger

            # Draw line from palm to finger
            ax.plot([palm_plot[0], tip_plot[0]], [palm_plot[1], tip_plot[1]],
                   color=color, linewidth=2 if is_target else 1, alpha=0.5)

            # Draw fingertip
            size = 150 if is_target else 80
            marker = '*' if is_target else 'o'
            ax.scatter(*tip_plot, s=size, c=[color], marker=marker,
                      edgecolors='black' if is_target else 'none', linewidths=2)

            # Label
            ax.annotate(FINGER_SHORT_NAMES.get(full_name, finger_name),
                       tip_plot, textcoords="offset points", xytext=(0, 5),
                       ha='center', fontsize=8)

    def plot_all_trials_sequence(self, figsize: Tuple[int, int] = (16, 4)):
        """
        Plot all trials in a horizontal sequence showing finger positions.

        Good for seeing patterns across the entire session.
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib is required for plotting")

        if not self.trials:
            print("No trials to plot")
            return

        n_trials = len(self.trials)
        fig, axes = plt.subplots(1, n_trials, figsize=(max(16, n_trials * 1.5), 4))

        if n_trials == 1:
            axes = [axes]

        for i, trial in enumerate(self.trials):
            ax = axes[i]
            self._plot_mini_trial(ax, trial)

        fig.suptitle('All Trials Sequence (Top View)', fontsize=12, fontweight='bold')
        plt.tight_layout()
        return fig

    def _plot_mini_trial(self, ax, trial: Trial):
        """Plot a mini version of a trial for sequence view."""
        ax.set_xlim(-250, 250)
        ax.set_ylim(-50, 200)
        ax.set_aspect('equal')
        ax.axis('off')

        # Draw both hands
        for hand_data, hand_type in [(trial.left_hand, 'left'), (trial.right_hand, 'right')]:
            if hand_data is None:
                continue

            fingers = hand_data.get('fingers', {})
            for finger_name, finger_data in fingers.items():
                full_name = f"{hand_type}_{finger_name}"
                tip = finger_data.get('tip_position', {})

                color = FINGER_COLORS.get(full_name, 'gray')
                is_target = full_name == trial.target_finger

                size = 80 if is_target else 30
                ax.scatter(tip.get('x', 0), tip.get('z', 0), s=size, c=[color],
                          marker='*' if is_target else 'o',
                          edgecolors='black' if is_target else 'none')

        # Trial label
        status_color = 'green' if trial.is_correct else 'red'
        ax.set_title(f"#{trial.number}\n{FINGER_SHORT_NAMES.get(trial.target_finger, '?')}",
                    fontsize=8, color=status_color)

    def plot_finger_heatmap(self, figsize: Tuple[int, int] = (10, 6)):
        """
        Plot heatmap of target vs pressed fingers (confusion matrix style).
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib is required for plotting")

        # Build confusion matrix
        matrix = np.zeros((10, 10))
        for trial in self.trials:
            if trial.target_finger in FINGER_ORDER and trial.pressed_finger in FINGER_ORDER:
                target_idx = FINGER_ORDER.index(trial.target_finger)
                pressed_idx = FINGER_ORDER.index(trial.pressed_finger)
                matrix[target_idx, pressed_idx] += 1

        fig, ax = plt.subplots(figsize=figsize)

        im = ax.imshow(matrix, cmap='Blues')

        # Labels
        labels = [FINGER_SHORT_NAMES[f] for f in FINGER_ORDER]
        ax.set_xticks(range(10))
        ax.set_yticks(range(10))
        ax.set_xticklabels(labels)
        ax.set_yticklabels(labels)
        ax.set_xlabel('Pressed Finger')
        ax.set_ylabel('Target Finger')
        ax.set_title('Target vs Pressed Finger Matrix')

        # Add counts to cells
        for i in range(10):
            for j in range(10):
                if matrix[i, j] > 0:
                    color = 'white' if matrix[i, j] > matrix.max() / 2 else 'black'
                    ax.text(j, i, int(matrix[i, j]), ha='center', va='center', color=color)

        # Highlight diagonal
        for i in range(10):
            ax.add_patch(plt.Rectangle((i-0.5, i-0.5), 1, 1, fill=False,
                                       edgecolor='green', linewidth=2))

        plt.colorbar(im, label='Count')
        plt.tight_layout()
        return fig

    # ========== 3D Visualization Methods ==========

    def plot_3d_session(self, figsize: Tuple[int, int] = (14, 10),
                        show_trajectories: bool = True,
                        color_by: str = 'finger'):
        """
        Plot full 3D visualization of the entire session.

        Shows all hand positions across all trials in 3D space.

        Args:
            figsize: Figure size
            show_trajectories: If True, draw lines connecting finger positions over time
            color_by: 'finger' (color by finger), 'time' (gradient over time),
                     'correct' (green/red by correctness)
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib is required for plotting")

        if not self.trials:
            print("No trials to plot")
            return

        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')

        # Collect all finger positions over time
        finger_trajectories = {f: {'x': [], 'y': [], 'z': [], 't': []} for f in FINGER_ORDER}
        palm_trajectories = {'left': {'x': [], 'y': [], 'z': []},
                            'right': {'x': [], 'y': [], 'z': []}}

        for trial in self.trials:
            t = trial.elapsed_seconds

            for hand_data, hand_type in [(trial.left_hand, 'left'), (trial.right_hand, 'right')]:
                if hand_data is None:
                    continue

                # Palm position
                palm = hand_data.get('palm_position', {})
                palm_trajectories[hand_type]['x'].append(palm.get('x', 0))
                palm_trajectories[hand_type]['y'].append(palm.get('y', 0))
                palm_trajectories[hand_type]['z'].append(palm.get('z', 0))

                # Finger positions
                fingers = hand_data.get('fingers', {})
                for finger_name, finger_data in fingers.items():
                    full_name = f"{hand_type}_{finger_name}"
                    tip = finger_data.get('tip_position', {})
                    finger_trajectories[full_name]['x'].append(tip.get('x', 0))
                    finger_trajectories[full_name]['y'].append(tip.get('y', 0))
                    finger_trajectories[full_name]['z'].append(tip.get('z', 0))
                    finger_trajectories[full_name]['t'].append(t)

        # Normalize time for color mapping
        all_times = [trial.elapsed_seconds for trial in self.trials]
        t_min, t_max = min(all_times), max(all_times)

        # Plot finger positions and trajectories
        for finger_name in FINGER_ORDER:
            traj = finger_trajectories[finger_name]
            if not traj['x']:
                continue

            x, y, z = np.array(traj['x']), np.array(traj['y']), np.array(traj['z'])

            # Determine colors
            if color_by == 'finger':
                color = FINGER_COLORS.get(finger_name, 'gray')
                colors = [color] * len(x)
            elif color_by == 'time':
                cmap = plt.cm.viridis
                colors = [cmap((t - t_min) / (t_max - t_min + 0.001)) for t in traj['t']]
            else:  # color_by == 'correct'
                colors = []
                for i, trial in enumerate(self.trials):
                    if i < len(x):
                        colors.append('green' if trial.is_correct else 'red')

            # Plot points
            for i in range(len(x)):
                c = colors[i] if i < len(colors) else 'gray'
                is_target = self.trials[i].target_finger == finger_name if i < len(self.trials) else False
                size = 100 if is_target else 30
                marker = '*' if is_target else 'o'
                ax.scatter(x[i], z[i], y[i], c=[c], s=size, marker=marker, alpha=0.7)

            # Draw trajectory lines
            if show_trajectories and len(x) > 1:
                color = FINGER_COLORS.get(finger_name, 'gray')
                ax.plot(x, z, y, color=color, alpha=0.3, linewidth=1)

        # Labels and title
        ax.set_xlabel('X (mm) - Left/Right')
        ax.set_ylabel('Z (mm) - Forward/Back')
        ax.set_zlabel('Y (mm) - Height')

        summary = self.get_summary()
        ax.set_title(f"3D Session Replay: {summary['total_trials']} trials | "
                    f"{summary['accuracy']:.1f}% accuracy\n"
                    f"(Stars = target fingers)")

        # Add legend for fingers
        legend_elements = [mpatches.Patch(color=FINGER_COLORS[f],
                          label=FINGER_SHORT_NAMES[f]) for f in FINGER_ORDER[:5]]
        ax.legend(handles=legend_elements, loc='upper left', title='Left Hand')

        plt.tight_layout()
        return fig

    def plot_3d_trial(self, trial_number: int, figsize: Tuple[int, int] = (12, 9)):
        """
        Plot a single trial in full 3D with hand skeleton.

        Args:
            trial_number: Trial number (1-indexed)
            figsize: Figure size
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib is required for plotting")

        trial = self.get_trial(trial_number)
        if not trial:
            print(f"Trial {trial_number} not found")
            return

        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')

        # Draw both hands
        self._draw_hand_3d(ax, trial.left_hand, 'left', trial.target_finger)
        self._draw_hand_3d(ax, trial.right_hand, 'right', trial.target_finger)

        # Labels
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Z (mm)')
        ax.set_zlabel('Y (mm) - Height')

        # Title
        status = "CORRECT" if trial.is_correct else "WRONG"
        clean = " | CLEAN" if trial.is_clean_trial else ""
        ax.set_title(
            f"Trial {trial.number} (3D): Target={FINGER_SHORT_NAMES.get(trial.target_finger, '?')} | "
            f"Pressed={FINGER_SHORT_NAMES.get(trial.pressed_finger, '?')} | {status}{clean}\n"
            f"RT={trial.reaction_time_ms:.0f}ms | MLR={trial.mlr:.3f}",
            fontsize=11
        )

        # Set equal aspect ratio
        self._set_axes_equal_3d(ax)

        plt.tight_layout()
        return fig

    def _draw_hand_3d(self, ax, hand_data: Optional[Dict], hand_type: str, target_finger: str):
        """Draw a 3D hand skeleton."""
        if hand_data is None:
            return

        palm = hand_data.get('palm_position', {})
        palm_x, palm_y, palm_z = palm.get('x', 0), palm.get('y', 0), palm.get('z', 0)

        # Draw palm
        ax.scatter(palm_x, palm_z, palm_y, s=300, c='gray', alpha=0.5, marker='o')

        # Draw fingers
        fingers = hand_data.get('fingers', {})
        for finger_name, finger_data in fingers.items():
            full_name = f"{hand_type}_{finger_name}"
            tip = finger_data.get('tip_position', {})
            tip_x, tip_y, tip_z = tip.get('x', 0), tip.get('y', 0), tip.get('z', 0)

            color = FINGER_COLORS.get(full_name, 'gray')
            is_target = full_name == target_finger

            # Draw line from palm to fingertip
            ax.plot([palm_x, tip_x], [palm_z, tip_z], [palm_y, tip_y],
                   color=color, linewidth=3 if is_target else 1.5, alpha=0.7)

            # Draw fingertip
            size = 200 if is_target else 80
            marker = '*' if is_target else 'o'
            ax.scatter(tip_x, tip_z, tip_y, s=size, c=[color], marker=marker,
                      edgecolors='black' if is_target else 'none', linewidths=2)

            # Label
            ax.text(tip_x, tip_z, tip_y + 10, FINGER_SHORT_NAMES.get(full_name, ''),
                   fontsize=8, ha='center')

    def _set_axes_equal_3d(self, ax):
        """Set equal aspect ratio for 3D plot."""
        limits = np.array([ax.get_xlim3d(), ax.get_ylim3d(), ax.get_zlim3d()])
        origin = np.mean(limits, axis=1)
        radius = 0.5 * np.max(np.abs(limits[:, 1] - limits[:, 0]))
        ax.set_xlim3d([origin[0] - radius, origin[0] + radius])
        ax.set_ylim3d([origin[1] - radius, origin[1] + radius])
        ax.set_zlim3d([origin[2] - radius, origin[2] + radius])

    def plot_finger_trajectories_3d(self, fingers: List[str] = None,
                                     figsize: Tuple[int, int] = (12, 8)):
        """
        Plot 3D trajectories of specific fingers over the session.

        Args:
            fingers: List of finger names to plot (default: all target fingers)
            figsize: Figure size
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib is required for plotting")

        if not self.trials:
            print("No trials to plot")
            return

        # Default to fingers that were targets
        if fingers is None:
            fingers = list(set(t.target_finger for t in self.trials))

        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')

        for finger_name in fingers:
            x_vals, y_vals, z_vals = [], [], []

            for trial in self.trials:
                hand_type = 'left' if 'left' in finger_name else 'right'
                hand_data = trial.left_hand if hand_type == 'left' else trial.right_hand

                if hand_data is None:
                    continue

                finger_short = finger_name.replace(f'{hand_type}_', '')
                fingers_data = hand_data.get('fingers', {})
                if finger_short in fingers_data:
                    tip = fingers_data[finger_short].get('tip_position', {})
                    x_vals.append(tip.get('x', 0))
                    y_vals.append(tip.get('y', 0))
                    z_vals.append(tip.get('z', 0))

            if x_vals:
                color = FINGER_COLORS.get(finger_name, 'gray')
                # Plot trajectory
                ax.plot(x_vals, z_vals, y_vals, color=color, linewidth=2,
                       label=FINGER_SHORT_NAMES.get(finger_name, finger_name), alpha=0.7)
                # Plot points
                ax.scatter(x_vals, z_vals, y_vals, c=[color], s=50, alpha=0.5)
                # Mark start and end
                ax.scatter(x_vals[0], z_vals[0], y_vals[0], c=[color], s=150, marker='^',
                          edgecolors='black', label=f'{FINGER_SHORT_NAMES.get(finger_name, "")} start')
                ax.scatter(x_vals[-1], z_vals[-1], y_vals[-1], c=[color], s=150, marker='s',
                          edgecolors='black')

        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Z (mm)')
        ax.set_zlabel('Y (mm) - Height')
        ax.set_title('Finger Trajectories Over Session\n(Triangle=start, Square=end)')
        ax.legend(loc='upper left', fontsize=8)

        self._set_axes_equal_3d(ax)
        plt.tight_layout()
        return fig

    def animate_session(self, interval: int = 500, figsize: Tuple[int, int] = (12, 9),
                        save_path: str = None):
        """
        Create an animated 3D replay of the session.

        Args:
            interval: Milliseconds between frames
            figsize: Figure size
            save_path: If provided, save animation to this path (e.g., 'session.gif')

        Returns:
            matplotlib animation object (display in Jupyter with HTML(anim.to_jshtml()))
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib is required for plotting")

        if not self.trials:
            print("No trials to animate")
            return

        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')

        # Initialize empty plot elements
        scatter_plots = {}
        line_plots = {}

        def init():
            ax.set_xlabel('X (mm)')
            ax.set_ylabel('Z (mm)')
            ax.set_zlabel('Y (mm) - Height')
            ax.set_xlim(-250, 250)
            ax.set_ylim(-50, 200)
            ax.set_zlim(150, 350)
            return []

        def update(frame):
            ax.clear()
            ax.set_xlabel('X (mm)')
            ax.set_ylabel('Z (mm)')
            ax.set_zlabel('Y (mm) - Height')
            ax.set_xlim(-250, 250)
            ax.set_ylim(-50, 200)
            ax.set_zlim(150, 350)

            trial = self.trials[frame]

            # Draw hands
            self._draw_hand_3d(ax, trial.left_hand, 'left', trial.target_finger)
            self._draw_hand_3d(ax, trial.right_hand, 'right', trial.target_finger)

            # Title with trial info
            status = "CORRECT" if trial.is_correct else "WRONG"
            status_color = 'green' if trial.is_correct else 'red'
            ax.set_title(
                f"Trial {trial.number}/{len(self.trials)} | "
                f"Target: {FINGER_SHORT_NAMES.get(trial.target_finger, '?')} | "
                f"{status}\n"
                f"Time: {trial.elapsed_seconds:.1f}s | Score: {trial.score}",
                fontsize=12, color=status_color
            )

            return []

        anim = animation.FuncAnimation(fig, update, init_func=init,
                                       frames=len(self.trials), interval=interval,
                                       blit=False, repeat=True)

        if save_path:
            print(f"Saving animation to {save_path}...")
            anim.save(save_path, writer='pillow', fps=1000//interval)
            print("Done!")

        return anim

    def plot_press_positions_3d(self, figsize: Tuple[int, int] = (12, 8)):
        """
        Plot only the pressed finger positions in 3D, colored by correctness.

        Shows where the pressed finger was at the moment of each press.
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib is required for plotting")

        if not self.trials:
            print("No trials to plot")
            return

        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')

        correct_x, correct_y, correct_z = [], [], []
        wrong_x, wrong_y, wrong_z = [], [], []

        for trial in self.trials:
            # Get the pressed finger position
            pressed = trial.pressed_finger
            hand_type = 'left' if 'left' in pressed else 'right'
            hand_data = trial.left_hand if hand_type == 'left' else trial.right_hand

            if hand_data is None:
                continue

            finger_short = pressed.replace(f'{hand_type}_', '')
            fingers_data = hand_data.get('fingers', {})

            if finger_short in fingers_data:
                tip = fingers_data[finger_short].get('tip_position', {})
                x, y, z = tip.get('x', 0), tip.get('y', 0), tip.get('z', 0)

                if trial.is_correct:
                    correct_x.append(x)
                    correct_y.append(y)
                    correct_z.append(z)
                else:
                    wrong_x.append(x)
                    wrong_y.append(y)
                    wrong_z.append(z)

        # Plot correct presses
        if correct_x:
            ax.scatter(correct_x, correct_z, correct_y, c='green', s=100,
                      alpha=0.7, label=f'Correct ({len(correct_x)})', marker='o')

        # Plot wrong presses
        if wrong_x:
            ax.scatter(wrong_x, wrong_z, wrong_y, c='red', s=150,
                      alpha=0.7, label=f'Wrong ({len(wrong_x)})', marker='x')

        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Z (mm)')
        ax.set_zlabel('Y (mm) - Height')
        ax.set_title('Pressed Finger Positions (3D)\nGreen=Correct, Red=Wrong')
        ax.legend()

        self._set_axes_equal_3d(ax)
        plt.tight_layout()
        return fig


def list_sessions(directory: str = 'session_logs') -> List[str]:
    """List all available session files."""
    pattern = os.path.join(directory, 'session_*.json')
    files = glob.glob(pattern)
    files.sort(reverse=True)  # Most recent first

    print(f"Found {len(files)} session files:")
    for f in files[:10]:  # Show first 10
        basename = os.path.basename(f)
        print(f"  {basename}")

    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more")

    return files


def compare_sessions(filepaths: List[str]) -> 'pd.DataFrame':
    """
    Compare multiple sessions side by side.

    Args:
        filepaths: List of session file paths

    Returns:
        DataFrame with comparison data
    """
    if not HAS_PANDAS:
        raise ImportError("pandas is required for this function")

    data = []
    for fp in filepaths:
        analyzer = SessionAnalyzer()
        if analyzer.load_session(fp):
            summary = analyzer.get_summary()
            summary['file'] = os.path.basename(fp)
            data.append(summary)

    return pd.DataFrame(data)


# Quick usage example when run directly
if __name__ == '__main__':
    print("Session Analyzer - Quick Demo")
    print("=" * 40)

    # List available sessions
    sessions = list_sessions()

    if sessions:
        # Load most recent
        analyzer = SessionAnalyzer()
        analyzer.load_session(sessions[0])

        # Print summary
        summary = analyzer.get_summary()
        print("\nSession Summary:")
        for key, value in summary.items():
            print(f"  {key}: {value}")

        # Show DataFrame if pandas available
        if HAS_PANDAS:
            print("\nTrials DataFrame:")
            df = analyzer.to_dataframe()
            print(df.head(10))

        # Plot if matplotlib available
        if HAS_MATPLOTLIB:
            print("\nGenerating plots...")
            analyzer.plot_session_overview()
            plt.show()
