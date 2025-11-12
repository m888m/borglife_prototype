"""
Progress Reporter for BorgLife Demo
Real-time progress reporting during demo execution with user-friendly updates.
"""

from typing import Dict, Any, Optional, Callable
from datetime import datetime
import time
import sys


class DemoProgressReporter:
    """Report progress during demo execution"""

    def __init__(self, show_progress: bool = True, progress_callback: Optional[Callable] = None):
        self.show_progress = show_progress
        self.progress_callback = progress_callback
        self.current_step = None
        self.step_start_time = None
        self.overall_start_time = None
        self.step_progress = {}

    def start_demo(self, demo_name: str = "BorgLife Phase 1 Demo"):
        """Start overall demo progress tracking"""
        self.overall_start_time = time.time()
        self._report_progress("demo_start", 0, f"🚀 Starting {demo_name}...")

    def end_demo(self, success: bool = True):
        """End overall demo progress tracking"""
        if self.overall_start_time:
            total_time = time.time() - self.overall_start_time
            status = "✅ Completed successfully" if success else "❌ Failed"
            self._report_progress("demo_end", 100, f"{status} in {total_time:.1f}s")

    def start_step(self, step_name: str, description: str = ""):
        """Start tracking a specific step"""
        self.current_step = step_name
        self.step_start_time = time.time()
        self.step_progress[step_name] = {
            'start_time': self.step_start_time,
            'description': description,
            'progress': 0,
            'status': 'running'
        }
        self._report_progress(step_name, 0, f"🔄 {description}")

    def update_step_progress(self, step_name: str, progress: float, message: str = ""):
        """Update progress for a specific step"""
        if step_name in self.step_progress:
            self.step_progress[step_name]['progress'] = min(100, max(0, progress))

            if message:
                self.step_progress[step_name]['message'] = message

            self._report_progress(step_name, progress, message)

    def complete_step(self, step_name: str, success: bool = True):
        """Mark a step as completed"""
        if step_name in self.step_progress:
            self.step_progress[step_name]['status'] = 'completed' if success else 'failed'
            self.step_progress[step_name]['end_time'] = time.time()

            duration = self.step_progress[step_name]['end_time'] - self.step_progress[step_name]['start_time']

            status_icon = "✅" if success else "❌"
            self._report_progress(step_name, 100, f"{status_icon} Completed in {duration:.1f}s")

    def report_step_progress(self, step: str, progress: float, message: str):
        """Main interface for reporting step progress"""
        self.update_step_progress(step, progress, message)

    def get_step_status(self, step_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific step"""
        return self.step_progress.get(step_name)

    def get_overall_progress(self) -> Dict[str, Any]:
        """Get overall demo progress"""
        if not self.overall_start_time:
            return {'progress': 0, 'status': 'not_started'}

        elapsed = time.time() - self.overall_start_time
        completed_steps = sum(1 for step in self.step_progress.values() if step['status'] == 'completed')
        total_steps = len(self.step_progress)

        if total_steps == 0:
            progress = 0
        else:
            progress = (completed_steps / total_steps) * 100

        return {
            'progress': round(progress, 1),
            'elapsed_time': round(elapsed, 1),
            'completed_steps': completed_steps,
            'total_steps': total_steps,
            'current_step': self.current_step,
            'status': 'running'
        }

    def _report_progress(self, step: str, progress: float, message: str):
        """Internal method to report progress"""
        if not self.show_progress:
            return

        # Format progress bar
        bar_width = 30
        filled = int(bar_width * progress / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Create progress line
        progress_line = f"\r[{bar}] {progress:5.1f}% {message}"

        # Print to console (overwrite previous line)
        print(progress_line, end='', flush=True)

        # Add newline for completed steps
        if progress >= 100 or "Completed" in message or "Failed" in message:
            print()

        # Call external callback if provided
        if self.progress_callback:
            try:
                self.progress_callback({
                    'step': step,
                    'progress': progress,
                    'message': message,
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception as e:
                print(f"Progress callback error: {e}")

    def show_step_summary(self):
        """Show summary of all steps"""
        if not self.step_progress:
            return

        print("\n📊 Demo Step Summary:")
        print("-" * 50)

        for step_name, step_info in self.step_progress.items():
            status_icon = {
                'running': '🔄',
                'completed': '✅',
                'failed': '❌'
            }.get(step_info['status'], '❓')

            duration = ""
            if 'end_time' in step_info and 'start_time' in step_info:
                duration = f" ({step_info['end_time'] - step_info['start_time']:.1f}s)"

            print(f"{status_icon} {step_name}: {step_info['description']}{duration}")

        overall = self.get_overall_progress()
        print(f"\n⏱️  Total Time: {overall['elapsed_time']}s")
        print(f"📈 Success Rate: {overall['completed_steps']}/{overall['total_steps']} steps")

    def reset(self):
        """Reset progress tracking"""
        self.current_step = None
        self.step_start_time = None
        self.overall_start_time = None
        self.step_progress = {}


class BorgLifeDemoProgress:
    """Specialized progress reporter for BorgLife demo steps"""

    STEPS = {
        'dna_loading': {'name': 'DNA Loading', 'weight': 10},
        'proto_borg_init': {'name': 'Proto-Borg Initialization', 'weight': 15},
        'task_execution': {'name': 'Task Execution', 'weight': 20},
        'phenotype_encoding': {'name': 'Phenotype Encoding', 'weight': 15},
        'transaction_prep': {'name': 'Transaction Preparation', 'weight': 10},
        'blockchain_submit': {'name': 'Blockchain Submission', 'weight': 15},
        'confirmation_wait': {'name': 'Block Confirmation', 'weight': 10},
        'integrity_verify': {'name': 'Integrity Verification', 'weight': 5}
    }

    def __init__(self, **kwargs):
        self.reporter = DemoProgressReporter(**kwargs)
        self.current_overall_progress = 0

    def start_demo(self):
        """Start BorgLife demo with specialized progress tracking"""
        self.reporter.start_demo("BorgLife DNA Storage Demo")

    def update_step(self, step_key: str, progress: float, message: str = ""):
        """Update progress for a specific BorgLife step"""
        if step_key not in self.STEPS:
            return

        step_info = self.STEPS[step_key]
        step_name = step_info['name']

        # Calculate overall progress
        step_weight = step_info['weight']
        step_contribution = (progress / 100) * step_weight

        # Sum up all completed steps plus current step progress
        completed_weight = sum(
            info['weight'] for key, info in self.STEPS.items()
            if key != step_key and self.reporter.get_step_status(info['name'])
            and self.reporter.get_step_status(info['name'])['status'] == 'completed'
        )

        overall_progress = completed_weight + step_contribution

        # Update step progress
        self.reporter.report_step_progress(step_name, progress, message)

        # Update overall progress display
        self._show_overall_progress(overall_progress)

    def complete_step(self, step_key: str, success: bool = True):
        """Mark BorgLife step as completed"""
        if step_key not in self.STEPS:
            return

        step_name = self.STEPS[step_key]['name']
        self.reporter.complete_step(step_name, success)

        # Recalculate overall progress
        completed_weight = sum(
            info['weight'] for info in self.STEPS.values()
            if self.reporter.get_step_status(info['name'])
            and self.reporter.get_step_status(info['name'])['status'] == 'completed'
        )

        self._show_overall_progress(completed_weight)

    def _show_overall_progress(self, progress: float):
        """Show overall demo progress"""
        progress = min(100, max(0, progress))

        if abs(progress - self.current_overall_progress) > 1:  # Only update if significant change
            self.current_overall_progress = progress
            self.reporter._report_progress("overall", progress, f"Overall Progress: {progress:.1f}%")

    def end_demo(self, success: bool = True):
        """End demo with final summary"""
        self.reporter.end_demo(success)
        self.reporter.show_step_summary()