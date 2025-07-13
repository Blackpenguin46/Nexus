"""
Metrics collection and performance monitoring for the Manus agent system.

This module provides comprehensive metrics collection for monitoring agent
performance, success rates, and resource usage.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import psutil


@dataclass
class TaskMetrics:
    """Metrics for a single task execution."""
    task_id: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    iterations: int = 0
    tool_calls: int = 0
    errors: int = 0
    memory_peak_mb: float = 0.0
    cpu_peak_percent: float = 0.0


@dataclass
class PerformanceSnapshot:
    """Snapshot of system performance at a point in time."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_usage_percent: float
    network_io: Optional[Dict[str, int]] = None


class MetricsCollector:
    """
    Collects and aggregates performance metrics for the agent system.
    
    Tracks task performance, resource usage, error rates, and other
    operational metrics useful for monitoring and optimization.
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        
        # Task metrics
        self.current_tasks: Dict[str, TaskMetrics] = {}
        self.completed_tasks: deque = deque(maxlen=max_history)
        
        # Performance metrics
        self.performance_history: deque = deque(maxlen=max_history)
        
        # Aggregated metrics
        self.total_tasks = 0
        self.successful_tasks = 0
        self.total_iterations = 0
        self.total_tool_calls = 0
        self.total_errors = 0
        
        # Response time tracking
        self.response_times: deque = deque(maxlen=100)  # Last 100 response times
        
        # Error tracking
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_history: deque = deque(maxlen=100)
        
        # Tool usage tracking
        self.tool_usage: Dict[str, int] = defaultdict(int)
        self.tool_success_rate: Dict[str, List[bool]] = defaultdict(list)
        
        # System monitoring
        self.start_time = time.time()
        self._last_snapshot_time = 0
        self._snapshot_interval = 60  # 1 minute
        
        # Take initial performance snapshot
        self._take_performance_snapshot()
    
    def record_task_start(self, task_id: Optional[str] = None) -> str:
        """
        Record the start of a task.
        
        Args:
            task_id: Optional task ID, generated if not provided
            
        Returns:
            Task ID for tracking
        """
        if task_id is None:
            task_id = f"task_{int(time.time() * 1000)}"
        
        metrics = TaskMetrics(
            task_id=task_id,
            start_time=time.time()
        )
        
        self.current_tasks[task_id] = metrics
        self.total_tasks += 1
        
        return task_id
    
    def record_task_completion(
        self, 
        success: bool, 
        execution_time: Optional[float] = None,
        task_id: Optional[str] = None
    ) -> None:
        """
        Record the completion of a task.
        
        Args:
            success: Whether the task completed successfully
            execution_time: Task execution time in seconds
            task_id: Task ID to update
        """
        # Find the task to update
        if task_id and task_id in self.current_tasks:
            metrics = self.current_tasks.pop(task_id)
        elif self.current_tasks:
            # Use the most recent task if no ID specified
            metrics = self.current_tasks.pop(next(iter(self.current_tasks)))
        else:
            # Create a new metrics object if none found
            metrics = TaskMetrics(
                task_id=task_id or "unknown",
                start_time=time.time() - (execution_time or 0)
            )
        
        # Update metrics
        metrics.end_time = time.time()
        metrics.success = success
        
        if execution_time:
            self.response_times.append(execution_time)
        
        # Update aggregated metrics
        if success:
            self.successful_tasks += 1
        else:
            self.total_errors += 1
        
        # Store completed task
        self.completed_tasks.append(metrics)
        
        # Take performance snapshot periodically
        if time.time() - self._last_snapshot_time > self._snapshot_interval:
            self._take_performance_snapshot()
    
    def record_tool_usage(self, tool_name: str, success: bool) -> None:
        """Record tool usage statistics."""
        self.tool_usage[tool_name] += 1
        self.tool_success_rate[tool_name].append(success)
        
        # Keep only last 100 results per tool
        if len(self.tool_success_rate[tool_name]) > 100:
            self.tool_success_rate[tool_name].pop(0)
        
        self.total_tool_calls += 1
    
    def record_error(self, error_type: str, error_message: str) -> None:
        """Record an error occurrence."""
        self.error_counts[error_type] += 1
        self.error_history.append({
            "timestamp": datetime.utcnow(),
            "type": error_type,
            "message": error_message[:200]  # Truncate long messages
        })
    
    def record_iteration(self, task_id: Optional[str] = None) -> None:
        """Record an agent loop iteration."""
        self.total_iterations += 1
        
        if task_id and task_id in self.current_tasks:
            self.current_tasks[task_id].iterations += 1
    
    def _take_performance_snapshot(self) -> None:
        """Take a snapshot of current system performance."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O (optional, may not be available in all environments)
            network_io = None
            try:
                net_io = psutil.net_io_counters()
                network_io = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                }
            except Exception:
                pass  # Network stats may not be available
            
            snapshot = PerformanceSnapshot(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_mb=memory.used / (1024 * 1024),
                disk_usage_percent=disk.percent,
                network_io=network_io
            )
            
            self.performance_history.append(snapshot)
            self._last_snapshot_time = time.time()
            
        except Exception:
            # Don't let performance monitoring crash the agent
            pass
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all collected metrics."""
        uptime = time.time() - self.start_time
        
        # Calculate success rate
        success_rate = (
            self.successful_tasks / self.total_tasks 
            if self.total_tasks > 0 else 0.0
        )
        
        # Calculate average response time
        avg_response_time = (
            sum(self.response_times) / len(self.response_times)
            if self.response_times else 0.0
        )
        
        # Get current performance
        current_perf = None
        if self.performance_history:
            latest = self.performance_history[-1]
            current_perf = {
                "cpu_percent": latest.cpu_percent,
                "memory_percent": latest.memory_percent,
                "memory_mb": latest.memory_mb,
                "disk_usage_percent": latest.disk_usage_percent,
            }
        
        # Tool success rates
        tool_stats = {}
        for tool_name, results in self.tool_success_rate.items():
            success_count = sum(results)
            total_count = len(results)
            tool_stats[tool_name] = {
                "usage_count": self.tool_usage[tool_name],
                "success_rate": success_count / total_count if total_count > 0 else 0.0,
                "recent_calls": total_count
            }
        
        return {
            "uptime_seconds": uptime,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "success_rate": success_rate,
            "total_iterations": self.total_iterations,
            "total_tool_calls": self.total_tool_calls,
            "total_errors": self.total_errors,
            "average_response_time": avg_response_time,
            "current_performance": current_perf,
            "active_tasks": len(self.current_tasks),
            "tool_statistics": tool_stats,
            "recent_errors": len(self.error_history),
            "error_types": dict(self.error_counts),
        }
    
    def get_performance_trend(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Get performance trend over the specified time period.
        
        Args:
            minutes: Number of minutes to look back
            
        Returns:
            List of performance data points
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        trend_data = []
        for snapshot in self.performance_history:
            if snapshot.timestamp >= cutoff_time:
                trend_data.append({
                    "timestamp": snapshot.timestamp.isoformat(),
                    "cpu_percent": snapshot.cpu_percent,
                    "memory_percent": snapshot.memory_percent,
                    "memory_mb": snapshot.memory_mb,
                    "disk_usage_percent": snapshot.disk_usage_percent,
                })
        
        return trend_data
    
    def get_tool_performance(self) -> Dict[str, Any]:
        """Get detailed tool performance statistics."""
        tool_perf = {}
        
        for tool_name in self.tool_usage:
            usage_count = self.tool_usage[tool_name]
            success_results = self.tool_success_rate.get(tool_name, [])
            
            success_count = sum(success_results)
            total_calls = len(success_results)
            success_rate = success_count / total_calls if total_calls > 0 else 0.0
            
            tool_perf[tool_name] = {
                "total_usage": usage_count,
                "recent_calls": total_calls,
                "success_rate": success_rate,
                "success_count": success_count,
                "failure_count": total_calls - success_count,
            }
        
        return tool_perf
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors and their frequencies."""
        recent_errors = []
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        for error in self.error_history:
            if error["timestamp"] >= cutoff_time:
                recent_errors.append({
                    "timestamp": error["timestamp"].isoformat(),
                    "type": error["type"],
                    "message": error["message"],
                })
        
        return {
            "total_errors": self.total_errors,
            "error_types": dict(self.error_counts),
            "recent_errors": recent_errors,
            "error_rate": self.total_errors / self.total_tasks if self.total_tasks > 0 else 0.0,
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing or fresh starts)."""
        self.current_tasks.clear()
        self.completed_tasks.clear()
        self.performance_history.clear()
        self.response_times.clear()
        self.error_history.clear()
        
        self.total_tasks = 0
        self.successful_tasks = 0
        self.total_iterations = 0
        self.total_tool_calls = 0
        self.total_errors = 0
        
        self.error_counts.clear()
        self.tool_usage.clear()
        self.tool_success_rate.clear()
        
        self.start_time = time.time()
        self._take_performance_snapshot()