"""
Metrics collection and monitoring for My Newsletters Voice Assistant
Tracks application performance, usage, and health metrics
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """Individual metric data point"""
    name: str
    type: MetricType
    value: float
    timestamp: float
    tags: Dict[str, str] = None
    metadata: Dict[str, Any] = None


class MetricsCollector:
    """Collects and manages application metrics"""
    
    def __init__(self, app_name: str = "my-newsletters", flush_interval: int = 60):
        self.app_name = app_name
        self.flush_interval = flush_interval
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self.start_time = time.time()
        
    def increment(self, name: str, value: float = 1, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        key = self._make_key(name, tags)
        self.counters[key] += value
        self._record_metric(name, MetricType.COUNTER, self.counters[key], tags)
    
    def gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric"""
        key = self._make_key(name, tags)
        self.gauges[key] = value
        self._record_metric(name, MetricType.GAUGE, value, tags)
    
    def histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a histogram metric"""
        self._record_metric(name, MetricType.HISTOGRAM, value, tags)
    
    def timer(self, name: str, tags: Dict[str, str] = None):
        """Context manager for timing operations"""
        return TimerContext(self, name, tags)
    
    def record_duration(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Record a duration metric"""
        key = self._make_key(name, tags)
        self.timers[key].append(duration)
        self._record_metric(name, MetricType.TIMER, duration, tags)
    
    def _make_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """Create a unique key for a metric"""
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name},{tag_str}"
        return name
    
    def _record_metric(self, name: str, metric_type: MetricType, value: float, tags: Dict[str, str] = None):
        """Record a metric data point"""
        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            timestamp=time.time(),
            tags=tags or {}
        )
        self.metrics[name].append(metric)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        return {
            "app_name": self.app_name,
            "uptime_seconds": time.time() - self.start_time,
            "timestamp": datetime.utcnow().isoformat(),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timers": self._get_timer_stats(),
            "recent_metrics": self._get_recent_metrics()
        }
    
    def _get_timer_stats(self) -> Dict[str, Dict[str, float]]:
        """Calculate timer statistics"""
        stats = {}
        for key, values in self.timers.items():
            if values:
                sorted_values = sorted(values)
                stats[key] = {
                    "count": len(values),
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "p50": sorted_values[len(sorted_values) // 2],
                    "p95": sorted_values[int(len(sorted_values) * 0.95)],
                    "p99": sorted_values[int(len(sorted_values) * 0.99)]
                }
        return stats
    
    def _get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent metric events"""
        all_metrics = []
        for metric_list in self.metrics.values():
            all_metrics.extend([asdict(m) for m in metric_list])
        
        # Sort by timestamp and return most recent
        all_metrics.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_metrics[:limit]
    
    async def export_metrics(self, filepath: str = None):
        """Export metrics to file"""
        if not filepath:
            filepath = f"logs/metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w") as f:
            json.dump(self.get_metrics(), f, indent=2, default=str)
    
    def reset(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.counters.clear()
        self.gauges.clear()
        self.timers.clear()


class TimerContext:
    """Context manager for timing operations"""
    
    def __init__(self, collector: MetricsCollector, name: str, tags: Dict[str, str] = None):
        self.collector = collector
        self.name = name
        self.tags = tags
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.collector.record_duration(self.name, duration, self.tags)


class ApplicationMetrics:
    """Application-specific metrics tracking"""
    
    def __init__(self):
        self.collector = MetricsCollector()
        
    # API Metrics
    def track_api_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """Track API request metrics"""
        self.collector.increment("api.requests.total", tags={"endpoint": endpoint, "method": method})
        self.collector.increment(f"api.requests.status.{status_code}")
        self.collector.record_duration("api.request.duration", duration, tags={"endpoint": endpoint})
        
        if status_code >= 500:
            self.collector.increment("api.errors.5xx", tags={"endpoint": endpoint})
        elif status_code >= 400:
            self.collector.increment("api.errors.4xx", tags={"endpoint": endpoint})
    
    # Authentication Metrics
    def track_auth_attempt(self, success: bool, provider: str = "gmail"):
        """Track authentication attempts"""
        status = "success" if success else "failure"
        self.collector.increment("auth.attempts", tags={"status": status, "provider": provider})
    
    def track_token_refresh(self, success: bool):
        """Track token refresh attempts"""
        status = "success" if success else "failure"
        self.collector.increment("auth.token.refresh", tags={"status": status})
    
    # Newsletter Processing Metrics
    def track_newsletter_fetch(self, count: int, duration: float):
        """Track newsletter fetching"""
        self.collector.increment("newsletters.fetched", value=count)
        self.collector.record_duration("newsletters.fetch.duration", duration)
        self.collector.gauge("newsletters.fetch.batch_size", count)
    
    def track_newsletter_parse(self, success: bool, story_count: int, duration: float):
        """Track newsletter parsing"""
        status = "success" if success else "failure"
        self.collector.increment("newsletters.parsed", tags={"status": status})
        if success:
            self.collector.histogram("newsletters.stories.count", story_count)
        self.collector.record_duration("newsletters.parse.duration", duration)
    
    # Audio Processing Metrics
    def track_audio_generation(self, success: bool, duration: float, text_length: int):
        """Track audio generation"""
        status = "success" if success else "failure"
        self.collector.increment("audio.generated", tags={"status": status})
        self.collector.record_duration("audio.generation.duration", duration)
        self.collector.histogram("audio.text.length", text_length)
    
    def track_audio_cache(self, hit: bool):
        """Track audio cache hits/misses"""
        status = "hit" if hit else "miss"
        self.collector.increment("audio.cache", tags={"status": status})
    
    # Voice Session Metrics
    def track_voice_session(self, action: str, duration: float = None):
        """Track voice session events"""
        self.collector.increment("voice.session.actions", tags={"action": action})
        if duration:
            self.collector.record_duration("voice.session.duration", duration, tags={"action": action})
    
    def track_voice_interruption(self, trigger: str):
        """Track voice interruptions"""
        self.collector.increment("voice.interruptions", tags={"trigger": trigger})
    
    # System Metrics
    def track_database_query(self, query_type: str, duration: float):
        """Track database query performance"""
        self.collector.record_duration("database.query.duration", duration, tags={"type": query_type})
        self.collector.increment("database.queries", tags={"type": query_type})
    
    def track_background_job(self, job_name: str, success: bool, duration: float):
        """Track background job execution"""
        status = "success" if success else "failure"
        self.collector.increment("jobs.executed", tags={"job": job_name, "status": status})
        self.collector.record_duration("jobs.duration", duration, tags={"job": job_name})
    
    def track_websocket_connection(self, event: str):
        """Track WebSocket connections"""
        self.collector.increment("websocket.connections", tags={"event": event})
        if event == "connect":
            current = self.collector.gauges.get("websocket.active", 0)
            self.collector.gauge("websocket.active", current + 1)
        elif event == "disconnect":
            current = self.collector.gauges.get("websocket.active", 0)
            self.collector.gauge("websocket.active", max(0, current - 1))
    
    # Health Metrics
    def update_health_status(self, service: str, healthy: bool):
        """Update service health status"""
        value = 1 if healthy else 0
        self.collector.gauge(f"health.{service}", value)
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get system health report"""
        metrics = self.collector.get_metrics()
        
        # Calculate health scores
        error_rate = 0
        if "api.requests.total" in metrics["counters"]:
            total_requests = metrics["counters"]["api.requests.total"]
            errors = metrics["counters"].get("api.errors.5xx", 0) + metrics["counters"].get("api.errors.4xx", 0)
            error_rate = (errors / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "status": "healthy" if error_rate < 5 else "degraded" if error_rate < 10 else "unhealthy",
            "uptime": metrics["uptime_seconds"],
            "error_rate": error_rate,
            "active_connections": metrics["gauges"].get("websocket.active", 0),
            "services": {
                "database": bool(metrics["gauges"].get("health.database", 0)),
                "redis": bool(metrics["gauges"].get("health.redis", 0)),
                "elevenlabs": bool(metrics["gauges"].get("health.elevenlabs", 0)),
                "gmail": bool(metrics["gauges"].get("health.gmail", 0))
            }
        }


# Global metrics instance
app_metrics = ApplicationMetrics()