"""
Comprehensive test suite for self-bot safety features
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime, timedelta
import discord

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from worker import CircuitBreaker, get_human_delay, ANTI_DETECTION_CONFIG
from monitoring import RiskMonitor
from token_manager import validate_discord_token


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after reaching failure threshold"""
        breaker = CircuitBreaker(failure_threshold=2)
        mock_func = AsyncMock(side_effect=discord.HTTPException(Mock(), 'error'))
        
        # First two failures should not open the circuit
        with pytest.raises(discord.HTTPException):
            await breaker.call(mock_func)
        
        with pytest.raises(discord.HTTPException):
            await breaker.call(mock_func)
        
        # Third failure should open the circuit
        with pytest.raises(Exception, match="Circuit breaker opened"):
            await breaker.call(mock_func)
        
        # Subsequent calls should fail immediately
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await breaker.call(mock_func)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_after_timeout(self):
        """Test that circuit breaker resets after timeout period"""
        breaker = CircuitBreaker(failure_threshold=1, timeout=1)
        mock_func = AsyncMock(side_effect=discord.HTTPException(Mock(), 'error'))
        
        # Trigger circuit breaker
        with pytest.raises(discord.HTTPException):
            await breaker.call(mock_func)
        
        # Should be open
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await breaker.call(mock_func)
        
        # Wait for timeout
        await asyncio.sleep(1.1)
        
        # Should reset and allow retry
        with pytest.raises(discord.HTTPException):
            await breaker.call(mock_func)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success_resets_counter(self):
        """Test that successful calls reset the failure counter"""
        breaker = CircuitBreaker(failure_threshold=3)
        success_func = AsyncMock(return_value="success")
        fail_func = AsyncMock(side_effect=discord.HTTPException(Mock(), 'error'))
        
        # One failure
        with pytest.raises(discord.HTTPException):
            await breaker.call(fail_func)
        
        # Success should reset counter
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.failure_count == 0


class TestAntiDetection:
    """Test anti-detection mechanisms"""
    
    def test_human_delay_variation(self):
        """Test that delays have human-like variation"""
        delays = [get_human_delay() for _ in range(100)]
        
        # All delays should be positive
        assert all(d > 0 for d in delays)
        
        # Delays should be within reasonable range
        assert all(1 <= d <= 20 for d in delays)
        
        # Should have variation (not all the same)
        unique_delays = len(set(delays))
        assert unique_delays > 50, f"Only {unique_delays} unique delays out of 100"
        
        # Check distribution
        avg_delay = sum(delays) / len(delays)
        assert ANTI_DETECTION_CONFIG['min_delay'] <= avg_delay <= ANTI_DETECTION_CONFIG['max_delay'] + 2
    
    def test_anti_detection_config_values(self):
        """Test that anti-detection config has safe values"""
        assert ANTI_DETECTION_CONFIG['min_delay'] >= 3
        assert ANTI_DETECTION_CONFIG['max_delay'] >= ANTI_DETECTION_CONFIG['min_delay']
        assert ANTI_DETECTION_CONFIG['messages_per_hour_limit'] <= 100
        assert ANTI_DETECTION_CONFIG['session_duration_max'] <= 7200  # 2 hours


class TestRiskMonitor:
    """Test risk monitoring functionality"""
    
    def test_risk_calculation_normal_usage(self):
        """Test risk calculation for normal usage patterns"""
        monitor = RiskMonitor()
        user_id = "test_user"
        
        # Simulate normal usage
        for i in range(5):
            monitor.log_activity(user_id, "message_sent", {"channel_id": "123"})
            # Simulate realistic delays
            monitor.metrics[f"{user_id}:message_sent"][-1]['timestamp'] = \
                datetime.now() - timedelta(seconds=30 * (5 - i))
        
        risk = monitor.calculate_risk(user_id)
        assert risk < 0.5, f"Normal usage should have low risk, got {risk}"
    
    def test_risk_calculation_high_rate(self):
        """Test risk calculation for high message rate"""
        monitor = RiskMonitor()
        user_id = "test_user"
        
        # Simulate rapid messaging
        for i in range(20):
            monitor.log_activity(user_id, "message_sent", {"channel_id": "123"})
        
        risk = monitor.calculate_risk(user_id)
        assert risk > 0.5, f"High message rate should have high risk, got {risk}"
    
    def test_risk_calculation_bot_like_pattern(self):
        """Test risk calculation for bot-like consistent patterns"""
        monitor = RiskMonitor()
        user_id = "test_user"
        
        # Simulate consistent timing (bot-like)
        base_time = datetime.now()
        for i in range(15):
            activity = {"timestamp": base_time - timedelta(seconds=10 * i), "metadata": {}}
            monitor.metrics[f"{user_id}:message_sent"].append(activity)
        
        risk = monitor.calculate_risk(user_id)
        # Pattern consistency should contribute to risk
        assert risk > 0.0, "Bot-like patterns should increase risk"
    
    def test_should_pause_decision(self):
        """Test pause decision based on risk threshold"""
        monitor = RiskMonitor()
        user_id = "test_user"
        
        # Normal usage - should not pause
        monitor.log_activity(user_id, "message_sent", {})
        assert not monitor.should_pause(user_id)
        
        # Simulate high-risk behavior
        for _ in range(50):
            monitor.log_activity(user_id, "message_sent", {})
        
        # Should recommend pause
        assert monitor.should_pause(user_id)
    
    def test_recommended_delay_scaling(self):
        """Test that recommended delays increase with risk"""
        monitor = RiskMonitor()
        user_id = "test_user"
        
        # Low risk - normal delays
        low_risk_min, low_risk_max = monitor.get_recommended_delay(user_id)
        assert low_risk_min >= 3
        assert low_risk_max >= 12
        
        # Simulate high-risk behavior
        for _ in range(30):
            monitor.log_activity(user_id, "message_sent", {})
        
        # High risk - increased delays
        high_risk_min, high_risk_max = monitor.get_recommended_delay(user_id)
        assert high_risk_min > low_risk_min
        assert high_risk_max > low_risk_max


class TestTokenValidation:
    """Test token validation functionality"""
    
    @pytest.mark.asyncio
    async def test_validate_discord_token_invalid(self):
        """Test validation of invalid tokens"""
        # Test with mock to avoid actual API calls
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = Mock()
            mock_response.status = 401
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            is_valid, user_id = await validate_discord_token("invalid_token")
            assert not is_valid
            assert user_id is None
    
    @pytest.mark.asyncio
    async def test_validate_discord_token_valid(self):
        """Test validation of valid tokens"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={'id': '123456789'})
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            is_valid, user_id = await validate_discord_token("valid_token")
            assert is_valid
            assert user_id == '123456789'
    
    @pytest.mark.asyncio
    async def test_validate_discord_token_network_error(self):
        """Test token validation handles network errors gracefully"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.side_effect = Exception("Network error")
            
            is_valid, user_id = await validate_discord_token("any_token")
            assert not is_valid
            assert user_id is None


class TestIntegration:
    """Integration tests for self-bot safety features"""
    
    @pytest.mark.asyncio
    async def test_scraper_respects_rate_limits(self):
        """Test that scraper respects rate limits"""
        from worker import SelfBotScraper
        
        scraper = SelfBotScraper("test_token", "job_1", "session_1", Mock())
        scraper.rate_limit_tracker[datetime.now().hour] = ANTI_DETECTION_CONFIG['messages_per_hour_limit']
        
        with patch('asyncio.sleep') as mock_sleep:
            await scraper._check_rate_limits()
            # Should sleep when rate limit reached
            mock_sleep.assert_called()
    
    def test_safety_configuration(self):
        """Test that safety configurations are properly set"""
        from safety_checks import SelfBotSafetyManager
        
        # Mock environment variables
        with patch.dict('os.environ', {
            'TOKEN_ENCRYPTION_KEY': 'test_key',
            'SELFBOT_MIN_DELAY': '3',
            'SELFBOT_MAX_DELAY': '12',
            'SELFBOT_MESSAGES_PER_HOUR': '80'
        }):
            manager = SelfBotSafetyManager()
            compliance = manager.check_safety_compliance()
            
            assert compliance['checks']['encryption_enabled']
            assert compliance['checks']['rate_limits_configured']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])