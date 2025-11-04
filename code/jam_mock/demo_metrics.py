"""
Demo Metrics Collection for BorgLife Phase 1

Comprehensive metrics tracking for demo execution, performance monitoring,
and operational insights.
"""

import time
import json
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict


@dataclass
class StepMetrics:
    """Metrics for a single demo step."""
    step_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def complete(self, success: bool = True, error: Optional[str] = None):
        """Mark step as complete and calculate duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error_message = error


@dataclass
class DemoRunMetrics:
    """Complete metrics for a demo run."""
    run_id: str
    start_time: float
    end_time: Optional[float] = None
    total_duration: Optional[float] = None
    success: bool = False
    
    # Step metrics
    steps: List[StepMetrics] = field(default_factory=list)
    
    # Financial metrics
    transaction_fee: Decimal = Decimal('0')
    task_cost: Decimal = Decimal('0')
    total_cost: Decimal = Decimal('0')
    
    # Transaction details
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    block_hash: Optional[str] = None
    confirmation_time: Optional[float] = None
    
    # DNA metrics
    original_dna_hash: Optional[str] = None
    encoded_dna_hash: Optional[str] = None
    dna_integrity_verified: Optional[bool] = None
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_step(self, step_name: str) -> StepMetrics:
        """Add a new step and return it for tracking."""
        step = StepMetrics(step_name=step_name, start_time=time.time())
        self.steps.append(step)
        return step
    
    def complete_run(self, success: bool = True):
        """Mark run as complete."""
        self.end_time = time.time()
        self.total_duration = self.end_time - self.start_time
        self.success = success
        self.total_cost = self.transaction_fee + self.task_cost


class DemoMetricsCollector:
    """
    Comprehensive metrics collector for BorgLife Phase 1 demo.
    
    Tracks performance, costs, success rates, and provides historical analysis.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize metrics collector.
        
        Args:
            storage_path: Directory to store metrics (default: ~/.borglife/metrics)
        """
        self.storage_path = Path(storage_path) if storage_path else Path.home() / ".borglife" / "metrics"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Current run metrics
        self.current_run: Optional[DemoRunMetrics] = None
        
        # Historical metrics storage
        self.metrics_file = self.storage_path / "demo_runs.jsonl"
    
    def start_run(self, run_id: Optional[str] = None) -> DemoRunMetrics:
        """Start tracking a new demo run."""
        if not run_id:
            run_id = f"run_{int(time.time())}_{id(self)}"
        
        self.current_run = DemoRunMetrics(
            run_id=run_id,
            start_time=time.time()
        )
        return self.current_run
    
    def record_step_start(self, step_name: str) -> StepMetrics:
        """Record the start of a demo step."""
        if not self.current_run:
            raise ValueError("No active run - call start_run() first")
        return self.current_run.add_step(step_name)
    
    def record_transaction(self, tx_hash: str, fee: Decimal, block_number: Optional[int] = None,
                          block_hash: Optional[str] = None):
        """Record transaction details."""
        if not self.current_run:
            raise ValueError("No active run")
        
        self.current_run.transaction_hash = tx_hash
        self.current_run.transaction_fee = fee
        self.current_run.block_number = block_number
        self.current_run.block_hash = block_hash
    
    def record_confirmation(self, confirmation_time: float):
        """Record block confirmation time."""
        if not self.current_run:
            raise ValueError("No active run")
        self.current_run.confirmation_time = confirmation_time
    
    def record_dna_hashes(self, original_hash: str, encoded_hash: str, integrity_verified: bool):
        """Record DNA integrity metrics."""
        if not self.current_run:
            raise ValueError("No active run")
        
        self.current_run.original_dna_hash = original_hash
        self.current_run.encoded_dna_hash = encoded_hash
        self.current_run.dna_integrity_verified = integrity_verified
    
    def record_error(self, error_message: str):
        """Record an error during demo execution."""
        if not self.current_run:
            raise ValueError("No active run")
        self.current_run.errors.append(error_message)
    
    def record_warning(self, warning_message: str):
        """Record a warning during demo execution."""
        if not self.current_run:
            raise ValueError("No active run")
        self.current_run.warnings.append(warning_message)
    
    def complete_run(self, success: bool = True) -> DemoRunMetrics:
        """Complete the current run and persist metrics."""
        if not self.current_run:
            raise ValueError("No active run")
        
        self.current_run.complete_run(success)
        
        # Persist to storage
        self._save_metrics(self.current_run)
        
        run_metrics = self.current_run
        self.current_run = None
        return run_metrics
   
    def _save_metrics(self, metrics: DemoRunMetrics):
        """Save metrics to JSONL file."""
        try:
            metrics_dict = asdict(metrics)
            
            # Convert Decimal to float for JSON serialization
            metrics_dict['transaction_fee'] = float(metrics_dict['transaction_fee'])
            metrics_dict['task_cost'] = float(metrics_dict['task_cost'])
            metrics_dict['total_cost'] = float(metrics_dict['total_cost'])
            
            with open(self.metrics_file, 'a') as f:
                f.write(json.dumps(metrics_dict) + '\n')
        except Exception as e:
            print(f"Warning: Failed to save metrics: {e}")
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent demo run metrics."""
        runs = []
        
        if not self.metrics_file.exists():
            return runs
        
        try:
            with open(self.metrics_file, 'r') as f:
                lines = f.readlines()
                
            # Get last N lines
            recent_lines = lines[-limit:] if len(lines) > limit else lines
            
            for line in recent_lines:
                runs.append(json.loads(line))
            
            return runs
        except Exception as e:
            print(f"Error loading metrics: {e}")
            return []
    
    def get_success_rate(self, last_n_runs: int = 20) -> float:
        """Calculate success rate from recent runs."""
        recent = self.get_recent_runs(last_n_runs)
        if not recent:
            return 0.0
        
        successful = sum(1 for run in recent if run['success'])
        return successful / len(recent)
    
    def get_average_metrics(self, last_n_runs: int = 20) -> Dict[str, Any]:
        """Calculate average metrics from recent runs."""
        recent = self.get_recent_runs(last_n_runs)
        if not recent:
            return {}
        
        # Calculate averages
        total_duration = sum(run.get('total_duration', 0) for run in recent if run.get('total_duration'))
        total_cost = sum(run.get('total_cost', 0) for run in recent)
        total_fee = sum(run.get('transaction_fee', 0) for run in recent)
        confirmation_times = [run.get('confirmation_time', 0) for run in recent if run.get('confirmation_time')]
        
        return {
            'runs_analyzed': len(recent),
            'success_rate': self.get_success_rate(last_n_runs),
            'avg_duration': total_duration / len(recent),
            'avg_cost': total_cost / len(recent),
            'avg_transaction_fee': total_fee / len(recent),
            'avg_confirmation_time': sum(confirmation_times) / len(confirmation_times) if confirmation_times else 0,
            'total_runs': len(recent)
        }
    
    def generate_report(self, last_n_runs: int = 20) -> str:
        """Generate a formatted metrics report."""
        avg_metrics = self.get_average_metrics(last_n_runs)
        
        if not avg_metrics:
            return "No metrics available yet"
        
        report = f"""
========================================
BORGLIFE DEMO METRICS REPORT
========================================

Analysis Period: Last {avg_metrics['runs_analyzed']} runs

SUCCESS RATE: {avg_metrics['success_rate']*100:.1f}%

PERFORMANCE:
- Average Duration: {avg_metrics['avg_duration']:.2f}s
- Average Confirmation: {avg_metrics['avg_confirmation_time']:.2f}s

COSTS:
- Average Transaction Fee: {avg_metrics['avg_transaction_fee']:.6f} WND
- Average Total Cost: {avg_metrics['avg_cost']:.6f} WND

========================================
Total Runs Analyzed: {avg_metrics['total_runs']}
========================================
"""
        return report


class DemoAlertManager:
    """
    Alert management for demo operations.
    
    Monitors for low balance, performance degradation, and error spikes.
    """
    
    def __init__(self, metrics_collector: DemoMetricsCollector):
        """Initialize alert manager."""
        self.metrics = metrics_collector
        
        # Alert thresholds
        self.low_balance_threshold = Decimal('0.1')  # WND
        self.error_rate_threshold = 0.2  # 20% error rate
        self.performance_degradation_threshold = 2.0  # 2x slower than average
    
    def check_balance_alert(self, current_balance: Decimal) -> Optional[str]:
        """Check if balance is low and return alert message."""
        if current_balance < self.low_balance_threshold:
            return f"⚠️  LOW BALANCE ALERT: {current_balance} WND (threshold: {self.low_balance_threshold} WND)"
        return None
    
    def check_performance_alert(self, current_duration: float) -> Optional[str]:
        """Check if performance is degraded."""
        avg_metrics = self.metrics.get_average_metrics(10)
        
        if not avg_metrics:
            return None
        
        avg_duration = avg_metrics.get('avg_duration', 0)
        if avg_duration > 0 and current_duration > avg_duration * self.performance_degradation_threshold:
            return f"⚠️  PERFORMANCE DEGRADATION: {current_duration:.2f}s (avg: {avg_duration:.2f}s)"
        
        return None
    
    def check_error_rate_alert(self) -> Optional[str]:
        """Check if error rate is too high."""
        success_rate = self.metrics.get_success_rate(20)
        error_rate = 1.0 - success_rate
        
        if error_rate > self.error_rate_threshold:
            return f"⚠️  HIGH ERROR RATE: {error_rate*100:.1f}% (threshold: {self.error_rate_threshold*100:.1f}%)"
        
        return None
    
    def check_all_alerts(self, current_balance: Optional[Decimal] = None,
                        current_duration: Optional[float] = None) -> List[str]:
        """Check all alert conditions and return active alerts."""
        alerts = []
        
        if current_balance is not None:
            alert = self.check_balance_alert(current_balance)
            if alert:
                alerts.append(alert)
        
        if current_duration is not None:
            alert = self.check_performance_alert(current_duration)
            if alert:
                alerts.append(alert)
        
        alert = self.check_error_rate_alert()
        if alert:
            alerts.append(alert)
        
        return alerts