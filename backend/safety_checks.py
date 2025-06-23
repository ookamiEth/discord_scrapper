"""
Safety checks and warnings for self-bot usage
"""
import os
from datetime import datetime
from typing import Dict, List

class SelfBotSafetyManager:
    def __init__(self):
        self.warning_accepted = os.getenv('SELFBOT_WARNING_ACCEPTED', 'false').lower() == 'true'
        self.detection_thresholds = {
            'messages_per_hour': 100,
            'channels_per_hour': 10,
            'continuous_operation_hours': 4
        }
    
    def check_safety_compliance(self) -> Dict[str, any]:
        """Verify safety measures are in place"""
        checks = {
            'warning_accepted': self.warning_accepted,
            'encryption_enabled': bool(os.getenv('TOKEN_ENCRYPTION_KEY')),
            'rate_limits_configured': all([
                os.getenv('SELFBOT_MIN_DELAY'),
                os.getenv('SELFBOT_MAX_DELAY'),
                os.getenv('SELFBOT_MESSAGES_PER_HOUR')
            ]),
            'test_mode': os.getenv('ENVIRONMENT', 'production') != 'production'
        }
        
        return {
            'compliant': all(checks.values()),
            'checks': checks,
            'warnings': self._generate_warnings(checks)
        }
    
    def _generate_warnings(self, checks: Dict) -> List[str]:
        warnings = []
        
        if not checks['warning_accepted']:
            warnings.append("User has not accepted self-bot usage warning")
        
        if not checks['encryption_enabled']:
            warnings.append("Token encryption is not configured")
        
        if not checks['rate_limits_configured']:
            warnings.append("Anti-detection rate limits not configured")
        
        return warnings
    
    def calculate_detection_risk(self, session_stats: Dict) -> float:
        """Calculate risk score (0-1) based on usage patterns"""
        risk_score = 0.0
        
        # Check message rate
        if session_stats.get('messages_per_hour', 0) > self.detection_thresholds['messages_per_hour']:
            risk_score += 0.3
        
        # Check channel diversity
        if session_stats.get('channels_accessed', 0) > self.detection_thresholds['channels_per_hour']:
            risk_score += 0.2
        
        # Check continuous operation
        operation_hours = (datetime.now() - session_stats.get('started_at', datetime.now())).seconds / 3600
        if operation_hours > self.detection_thresholds['continuous_operation_hours']:
            risk_score += 0.3
        
        # Check for human-like patterns
        if not session_stats.get('breaks_taken', 0):
            risk_score += 0.2
        
        return min(risk_score, 1.0)