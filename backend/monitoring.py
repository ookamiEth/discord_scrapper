"""
Monitoring and risk assessment for self-bot activities
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class RiskMonitor:
    """Monitor self-bot activities and calculate risk scores"""
    
    def __init__(self):
        self.thresholds = {
            'messages_per_minute': 5,
            'consecutive_errors': 3,
            'risk_score_critical': 0.7,
            'channels_per_hour': 10,
            'session_duration_critical': 14400  # 4 hours
        }
        self.metrics = defaultdict(lambda: deque(maxlen=1000))
        self.session_start_times = {}
        self.error_counts = defaultdict(int)
        
    def log_activity(self, user_id: str, activity_type: str, metadata: Dict) -> float:
        """Log and analyze activity for risk"""
        key = f"{user_id}:{activity_type}"
        
        activity_entry = {
            'timestamp': datetime.now(),
            'metadata': metadata
        }
        
        self.metrics[key].append(activity_entry)
        
        # Calculate risk based on activity type
        risk = self.calculate_risk(user_id)
        
        if risk > self.thresholds['risk_score_critical']:
            logger.warning(
                f"HIGH RISK DETECTED for user {user_id}: {risk:.2f}",
                extra={'user_id': user_id, 'risk_score': risk}
            )
            
        return risk
    
    def calculate_risk(self, user_id: str) -> float:
        """Calculate risk score (0-1) based on usage patterns"""
        risk_factors = []
        
        # Factor 1: Message rate
        message_rate = self._calculate_message_rate(user_id)
        if message_rate > self.thresholds['messages_per_minute']:
            risk_factors.append(0.3 * (message_rate / self.thresholds['messages_per_minute']))
        
        # Factor 2: Channel diversity
        channels_accessed = self._count_unique_channels(user_id)
        if channels_accessed > self.thresholds['channels_per_hour']:
            risk_factors.append(0.2 * (channels_accessed / self.thresholds['channels_per_hour']))
        
        # Factor 3: Session duration
        session_duration = self._get_session_duration(user_id)
        if session_duration > self.thresholds['session_duration_critical']:
            risk_factors.append(0.3 * (session_duration / self.thresholds['session_duration_critical']))
        
        # Factor 4: Error rate
        error_rate = self._calculate_error_rate(user_id)
        if error_rate > 0.1:  # More than 10% errors
            risk_factors.append(0.2 * min(1.0, error_rate * 5))
        
        # Factor 5: Pattern consistency
        pattern_score = self._analyze_pattern_consistency(user_id)
        risk_factors.append(0.2 * pattern_score)
        
        return min(1.0, sum(risk_factors))
    
    def _calculate_message_rate(self, user_id: str) -> float:
        """Calculate messages per minute"""
        message_key = f"{user_id}:message_sent"
        recent_messages = [
            m for m in self.metrics[message_key]
            if m['timestamp'] > datetime.now() - timedelta(minutes=5)
        ]
        
        if not recent_messages:
            return 0.0
        
        time_span = (recent_messages[-1]['timestamp'] - recent_messages[0]['timestamp']).total_seconds() / 60
        if time_span == 0:
            return len(recent_messages)
        
        return len(recent_messages) / time_span
    
    def _count_unique_channels(self, user_id: str) -> int:
        """Count unique channels accessed in the last hour"""
        channel_key = f"{user_id}:channel_accessed"
        recent_accesses = [
            m for m in self.metrics[channel_key]
            if m['timestamp'] > datetime.now() - timedelta(hours=1)
        ]
        
        unique_channels = set()
        for access in recent_accesses:
            if 'channel_id' in access['metadata']:
                unique_channels.add(access['metadata']['channel_id'])
        
        return len(unique_channels)
    
    def _get_session_duration(self, user_id: str) -> float:
        """Get current session duration in seconds"""
        if user_id not in self.session_start_times:
            return 0.0
        
        return (datetime.now() - self.session_start_times[user_id]).total_seconds()
    
    def _calculate_error_rate(self, user_id: str) -> float:
        """Calculate error rate"""
        error_key = f"{user_id}:error"
        message_key = f"{user_id}:message_sent"
        
        recent_errors = len([
            e for e in self.metrics[error_key]
            if e['timestamp'] > datetime.now() - timedelta(minutes=30)
        ])
        
        recent_messages = len([
            m for m in self.metrics[message_key]
            if m['timestamp'] > datetime.now() - timedelta(minutes=30)
        ])
        
        if recent_messages == 0:
            return 0.0
        
        return recent_errors / recent_messages
    
    def _analyze_pattern_consistency(self, user_id: str) -> float:
        """Analyze if behavior patterns are too consistent (bot-like)"""
        message_key = f"{user_id}:message_sent"
        recent_messages = [
            m for m in self.metrics[message_key]
            if m['timestamp'] > datetime.now() - timedelta(minutes=10)
        ]
        
        if len(recent_messages) < 10:
            return 0.0
        
        # Calculate time deltas between messages
        deltas = []
        for i in range(1, len(recent_messages)):
            delta = (recent_messages[i]['timestamp'] - recent_messages[i-1]['timestamp']).total_seconds()
            deltas.append(delta)
        
        if not deltas:
            return 0.0
        
        # Check variance in timing
        avg_delta = sum(deltas) / len(deltas)
        variance = sum((d - avg_delta) ** 2 for d in deltas) / len(deltas)
        
        # Low variance = consistent timing = bot-like
        if variance < 2.0:  # Less than 2 seconds variance
            return 0.8
        elif variance < 5.0:
            return 0.4
        else:
            return 0.0
    
    def start_session(self, user_id: str):
        """Mark the start of a scraping session"""
        self.session_start_times[user_id] = datetime.now()
        self.log_activity(user_id, 'session_start', {})
    
    def end_session(self, user_id: str):
        """Mark the end of a scraping session"""
        if user_id in self.session_start_times:
            duration = self._get_session_duration(user_id)
            self.log_activity(user_id, 'session_end', {'duration': duration})
            del self.session_start_times[user_id]
    
    def should_pause(self, user_id: str) -> bool:
        """Determine if scraping should pause based on risk"""
        risk = self.calculate_risk(user_id)
        return risk > self.thresholds['risk_score_critical']
    
    def get_recommended_delay(self, user_id: str) -> float:
        """Get recommended delay based on current risk"""
        risk = self.calculate_risk(user_id)
        
        # Base delay of 3-12 seconds, increase with risk
        base_min = 3
        base_max = 12
        
        # Increase delays based on risk
        if risk > 0.5:
            multiplier = 1 + (risk - 0.5) * 4  # Up to 3x at max risk
            return base_min * multiplier, base_max * multiplier
        
        return base_min, base_max
    
    def get_metrics_summary(self, user_id: str) -> Dict:
        """Get summary of current metrics"""
        return {
            'risk_score': self.calculate_risk(user_id),
            'message_rate': self._calculate_message_rate(user_id),
            'channels_accessed': self._count_unique_channels(user_id),
            'session_duration': self._get_session_duration(user_id),
            'error_rate': self._calculate_error_rate(user_id),
            'should_pause': self.should_pause(user_id)
        }


# Global risk monitor instance
risk_monitor = RiskMonitor()