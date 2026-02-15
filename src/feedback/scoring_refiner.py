"""
Scoring Refiner — Automatically adjusts ICP scoring weights based on outreach outcomes.

Uses the Outcome Tracker's signal-level performance data to:
1. Increase points for signals correlated with high reply/interest rates
2. Decrease points for signals correlated with opt-outs or poor engagement
3. Adjust thresholds based on tier-level conversion rates
4. Persist changes to scoring_config.json with version history
"""

import json
import shutil
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from loguru import logger

from src.feedback.outcome_tracker import OutcomeTracker


# Minimum sample size required before adjusting a signal's weight
MIN_SAMPLE_SIZE = 10

# Maximum allowed change per refinement cycle (prevents wild swings)
MAX_POINT_DELTA = 2

# Baseline expected reply rate (used as reference)
BASELINE_REPLY_RATE = 5.0  # percent

# Weight decay factor for signals with no engagement data
DECAY_FACTOR = 0.95


class ScoringRefiner:
    """
    Reads outcome data, calculates weight adjustments, and writes
    updated scoring_config.json with a backup trail.
    """

    def __init__(self, config_path: str = "scoring_config.json", backup_dir: str = "data/config_history"):
        self.config_path = Path(config_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.tracker = OutcomeTracker()

    def _load_config(self) -> Dict[str, Any]:
        """Load the current scoring config."""
        with open(self.config_path, "r") as f:
            return json.load(f)

    def _save_config(self, config: Dict[str, Any]):
        """Save scoring config with a timestamped backup."""
        # Create backup
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"scoring_config_{timestamp}.json"
        shutil.copy2(self.config_path, backup_path)
        logger.info(f"Backed up config to {backup_path}")

        # Write updated config
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved updated scoring config to {self.config_path}")

    def _calculate_adjustment(self, signal_data: Dict[str, Any], global_reply_rate: float) -> Tuple[int, str]:
        """
        Calculate point adjustment for a single signal based on performance.

        Returns (delta, reason) where delta is the change in points.
        Positive = signal is performing well, increase weight.
        Negative = signal is underperforming, decrease weight.
        """
        sent = signal_data.get("emails_sent", 0)
        reply_rate = signal_data.get("reply_rate_pct", 0)
        interest_rate = signal_data.get("interest_rate_pct", 0)
        opt_out_rate = signal_data.get("opt_out_rate_pct", 0)

        # Not enough data to make a judgment
        if sent < MIN_SAMPLE_SIZE:
            return 0, f"Insufficient data ({sent}/{MIN_SAMPLE_SIZE} emails sent)"

        # Reference rate: use either global or baseline, whichever is available
        reference_rate = max(global_reply_rate, BASELINE_REPLY_RATE)

        # === High opt-out rate → strong negative signal ===
        if opt_out_rate > 10:
            delta = -min(MAX_POINT_DELTA, 2)
            return delta, f"High opt-out rate ({opt_out_rate}%)"

        # === Calculate performance ratio vs reference ===
        if reference_rate > 0:
            performance_ratio = reply_rate / reference_rate
        else:
            performance_ratio = 1.0

        # === Reply rate significantly above average → increase ===
        if performance_ratio >= 1.5 and interest_rate > 30:
            delta = min(MAX_POINT_DELTA, max(1, round(math.log2(performance_ratio))))
            return delta, f"Strong performer: {reply_rate}% reply rate ({performance_ratio:.1f}x reference), {interest_rate}% interest"

        if performance_ratio >= 1.2:
            delta = 1
            return delta, f"Above average: {reply_rate}% reply rate ({performance_ratio:.1f}x reference)"

        # === Reply rate significantly below average → decrease ===
        if performance_ratio <= 0.5 and sent >= MIN_SAMPLE_SIZE * 2:
            delta = -1
            return delta, f"Underperforming: {reply_rate}% reply rate ({performance_ratio:.1f}x reference)"

        return 0, f"Within normal range ({reply_rate}% reply, {performance_ratio:.1f}x reference)"

    def _adjust_thresholds(self, config: Dict[str, Any], tier_perf: Dict[str, Dict[str, Any]]) -> bool:
        """
        Adjust tier thresholds based on conversion rates.
        If medium_priority tier has better conversion than high_priority,
        the threshold may need lowering to capture more of those leads.
        """
        thresholds = config.get("thresholds", {})
        changed = False

        high_data = tier_perf.get("high_priority", {})
        medium_data = tier_perf.get("medium_priority", {})

        high_reply_rate = high_data.get("reply_rate_pct", 0)
        medium_reply_rate = medium_data.get("reply_rate_pct", 0)
        high_sent = high_data.get("sent", 0)
        medium_sent = medium_data.get("sent", 0)

        # Only adjust if we have enough data in both tiers
        if high_sent >= MIN_SAMPLE_SIZE and medium_sent >= MIN_SAMPLE_SIZE:
            # If medium tier is converting nearly as well as high,
            # consider lowering the high_fit threshold to include them
            if medium_reply_rate >= high_reply_rate * 0.8 and medium_reply_rate > 3:
                current_high = thresholds.get("high_fit", 15)
                new_high = max(current_high - 1, thresholds.get("medium_fit", 7) + 2)
                if new_high != current_high:
                    thresholds["high_fit"] = new_high
                    changed = True
                    logger.info(
                        f"Lowered high_fit threshold: {current_high} → {new_high} "
                        f"(medium tier reply rate {medium_reply_rate}% ≈ high tier {high_reply_rate}%)"
                    )

            # If high tier has very poor conversion, raise the threshold
            if high_reply_rate < 1 and high_sent >= MIN_SAMPLE_SIZE * 3:
                current_high = thresholds.get("high_fit", 15)
                new_high = min(current_high + 1, 25)
                if new_high != current_high:
                    thresholds["high_fit"] = new_high
                    changed = True
                    logger.info(
                        f"Raised high_fit threshold: {current_high} → {new_high} "
                        f"(high tier reply rate too low: {high_reply_rate}%)"
                    )

        config["thresholds"] = thresholds
        return changed

    def refine(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Main refinement loop:
        1. Generate outcome report
        2. Calculate adjustments for each signal
        3. Apply adjustments to config (or log changes in dry_run mode)
        4. Adjust thresholds if needed
        5. Save updated config with backup

        Returns a summary of changes made.
        """
        report = self.tracker.generate_report()
        config = self._load_config()

        global_reply_rate = report["global_stats"].get("reply_rate_pct", 0)
        signal_perf = report["signal_performance"]
        tier_perf = report["tier_performance"]

        changes = []
        signals_config = config.get("signals", {})

        for category, signals in signals_config.items():
            for signal_key, details in signals.items():
                perf_data = signal_perf.get(signal_key, {})

                if not perf_data:
                    # No outreach data for this signal yet
                    continue

                delta, reason = self._calculate_adjustment(perf_data, global_reply_rate)

                if delta != 0:
                    old_points = details.get("points", 0)
                    new_points = max(1, old_points + delta)  # Minimum 1 point

                    change_record = {
                        "signal": signal_key,
                        "category": category,
                        "old_points": old_points,
                        "new_points": new_points,
                        "delta": delta,
                        "reason": reason,
                    }
                    changes.append(change_record)

                    if not dry_run:
                        details["points"] = new_points

                    logger.info(
                        f"{'[DRY RUN] ' if dry_run else ''}"
                        f"Signal {signal_key}: {old_points} → {new_points} pts ({'+' if delta > 0 else ''}{delta}) — {reason}"
                    )

        # Adjust thresholds
        threshold_changed = False
        if not dry_run:
            threshold_changed = self._adjust_thresholds(config, tier_perf)

        # Save if changes were made
        if changes and not dry_run:
            # Add refinement metadata
            if "refinement_history" not in config:
                config["refinement_history"] = []

            config["refinement_history"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "changes": changes,
                "global_reply_rate": global_reply_rate,
                "threshold_adjusted": threshold_changed,
            })

            # Keep only last 20 refinement entries
            config["refinement_history"] = config["refinement_history"][-20:]

            self._save_config(config)

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "dry_run": dry_run,
            "global_reply_rate": global_reply_rate,
            "changes_count": len(changes),
            "changes": changes,
            "threshold_adjusted": threshold_changed,
        }

        if not changes:
            logger.info("No scoring adjustments needed at this time.")

        return summary

    def get_refinement_history(self) -> list:
        """Get the refinement history from config."""
        config = self._load_config()
        return config.get("refinement_history", [])


if __name__ == "__main__":
    refiner = ScoringRefiner()
    # Dry run first to see what would change
    summary = refiner.refine(dry_run=True)
    print(json.dumps(summary, indent=2))
