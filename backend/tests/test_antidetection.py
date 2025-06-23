"""
Test anti-detection measures
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import json
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from http_client import AntiDetectionHTTPClient, BrowserProfile, SessionProfileManager
from discord_client import AntiDetectionBot, AntiDetectionHTTPClient as DiscordHTTPClient
from browser_automation import BrowserAutomation, ChallengeTracker, BrowserPool


class TestBrowserProfiles:
    """Test browser profile management"""
    
    def test_profile_weights(self):
        """Test that profile weights sum to 100"""
        total_weight = sum(profile['weight'] for profile in BrowserProfile.PROFILES.values())
        assert total_weight == 100
    
    def test_weighted_profile_distribution(self):
        """Test that weighted selection favors common browsers"""
        profiles_selected = {}
        
        for _ in range(1000):
            profile = BrowserProfile.get_weighted_profile()
            name = profile['name']
            profiles_selected[name] = profiles_selected.get(name, 0) + 1
        
        # Chrome Windows should be most common
        assert profiles_selected.get('chrome_win', 0) > profiles_selected.get('safari_mac', 0)
        
        # All profiles should be selected at least once
        assert len(profiles_selected) == len(BrowserProfile.PROFILES)
    
    def test_session_profile_persistence(self):
        """Test that profiles persist for sessions"""
        manager = SessionProfileManager()
        
        # Get profile for session
        profile1 = manager.get_or_create_profile('session_1')
        profile2 = manager.get_or_create_profile('session_1')
        
        # Should be the same profile
        assert profile1['name'] == profile2['name']
        
        # Different session should get potentially different profile
        profile3 = manager.get_or_create_profile('session_2')
        # Can't guarantee different, but should be tracked separately
        assert len(manager._profile_cache) == 2


class TestAntiDetectionHTTPClient:
    """Test HTTP client anti-detection features"""
    
    @pytest.mark.asyncio
    async def test_session_rotation(self):
        """Test that sessions rotate after threshold"""
        client = AntiDetectionHTTPClient()
        initial_profile = client.profile['name']
        
        # Force rotation
        client.session_rotation_count = client.max_requests_per_session
        
        assert client._should_rotate_session()
        
        # Rotate and check profile changed
        client._rotate_session()
        # Profile might be the same by chance, but session should be reset
        assert client.session_rotation_count == 0
    
    @pytest.mark.asyncio
    async def test_header_randomization(self):
        """Test that headers are randomized"""
        client = AntiDetectionHTTPClient()
        
        # Mock the curl session
        with patch.object(client, 'curl_session') as mock_session:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.text = '{}'
            mock_session.request.return_value = mock_response
            
            # Make multiple requests
            headers_orders = []
            for _ in range(5):
                await client.request('GET', 'https://example.com')
                # Get the headers that were passed
                call_args = mock_session.request.call_args
                if call_args and call_args[1].get('headers'):
                    headers_orders.append(list(call_args[1]['headers'].keys()))
            
            # Headers should have different orders (not guaranteed but likely)
            unique_orders = [str(order) for order in headers_orders]
            # At least some variation expected
            assert len(set(unique_orders)) > 1
    
    @pytest.mark.asyncio
    async def test_timing_variance(self):
        """Test that request timings have variance"""
        client = AntiDetectionHTTPClient()
        
        # Simulate multiple requests with consistent timing
        for i in range(10):
            client.last_request_time = datetime.now()
            client.request_timings.append(1.0)  # Consistent 1 second
        
        # This should trigger timing variance on next request
        client._add_timing_variance()
        
        # Can't test the actual delay without mocking asyncio.sleep
        # But we can verify the variance detection logic
        assert len(client.request_timings) <= 20  # Max 20 timings kept
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting per client type"""
        client = AntiDetectionHTTPClient()
        
        with patch('asyncio.sleep') as mock_sleep:
            # Exceed burst limit
            for _ in range(10):
                await client._apply_rate_limit('curl_cffi')
            
            # Should have triggered rate limit
            mock_sleep.assert_called()
    
    @pytest.mark.asyncio 
    async def test_javascript_challenge_detection(self):
        """Test JavaScript challenge detection"""
        client = AntiDetectionHTTPClient()
        
        # Test various challenge responses
        challenge_response = {
            'status': 403,
            'text': 'Checking your browser... challenge-platform'
        }
        assert client._is_javascript_challenge(challenge_response)
        
        normal_response = {
            'status': 200,
            'text': 'Normal response'
        }
        assert not client._is_javascript_challenge(normal_response)
    
    def test_profile_stats(self):
        """Test client statistics tracking"""
        client = AntiDetectionHTTPClient('test_session')
        stats = client.get_stats()
        
        assert stats['session_id'] == 'test_session'
        assert 'profile' in stats
        assert stats['requests_made'] == 0
        assert 'session_age' in stats


class TestDiscordIntegration:
    """Test Discord client integration"""
    
    @pytest.mark.asyncio
    async def test_critical_endpoints(self):
        """Test that critical endpoints use anti-detection"""
        from discord_client import CRITICAL_ENDPOINTS
        
        # Verify critical endpoints are defined
        assert '/users/@me' in CRITICAL_ENDPOINTS
        assert '/channels' in CRITICAL_ENDPOINTS
        assert '/messages' in CRITICAL_ENDPOINTS
    
    @pytest.mark.asyncio
    async def test_header_introduction_schedule(self):
        """Test gradual header introduction"""
        http_client = DiscordHTTPClient(session_id='test')
        
        # At start, should have minimal headers
        headers = await http_client._get_headers()
        assert 'User-Agent' in headers
        assert 'X-Super-Properties' not in headers  # Not introduced yet
        
        # Simulate 5 minutes passing
        http_client.session_start_time = datetime.now() - timedelta(seconds=301)
        headers = await http_client._get_headers()
        assert 'X-Super-Properties' in headers  # Should be introduced now
    
    def test_super_properties_generation(self):
        """Test X-Super-Properties header generation"""
        http_client = DiscordHTTPClient(session_id='test')
        
        # Mock profile
        http_client.http_client.profile = {
            'name': 'chrome_win',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        super_props = http_client._get_super_properties()
        
        # Should be base64 encoded JSON
        import base64
        decoded = json.loads(base64.b64decode(super_props))
        
        assert decoded['os'] == 'Windows'
        assert decoded['browser'] == 'Chrome'
        assert 'client_build_number' in decoded


class TestBrowserAutomation:
    """Test browser automation for challenges"""
    
    def test_challenge_tracker_limits(self):
        """Test challenge tracking and limits"""
        tracker = ChallengeTracker()
        
        # Should allow first challenges
        assert tracker.should_auto_solve('session_1')
        
        # Record challenges up to limit
        for _ in range(3):
            tracker.record_challenge('session_1', True)
        
        # Should not allow more
        assert not tracker.should_auto_solve('session_1')
        
        # Different session should be allowed
        assert tracker.should_auto_solve('session_2')
    
    def test_consecutive_failure_tracking(self):
        """Test consecutive failure detection"""
        tracker = ChallengeTracker()
        
        # Record failures
        for _ in range(5):
            tracker.record_challenge('session_1', False)
        
        # Should detect too many failures
        assert tracker.too_many_failures('session_1')
        
        # Success should reset
        tracker.record_challenge('session_1', True)
        assert not tracker.too_many_failures('session_1')
    
    @pytest.mark.asyncio
    async def test_browser_pool_concurrency(self):
        """Test browser pool concurrent limits"""
        pool = BrowserPool(max_concurrent=2)
        
        # Should initialize
        await pool.initialize()
        assert pool.browser_queue.qsize() == 2
        
        # Acquire browsers up to limit
        browsers = []
        for _ in range(2):
            browser = await asyncio.wait_for(pool.acquire(), timeout=1.0)
            browsers.append(browser)
        
        # Pool should be exhausted
        assert pool.browser_queue.empty()
        
        # Release one
        await pool.release(browsers[0])
        assert pool.browser_queue.qsize() == 1


class TestFallbackChain:
    """Test fallback mechanisms"""
    
    @pytest.mark.asyncio
    async def test_http_client_fallback(self):
        """Test fallback from curl_cffi to tls_client"""
        client = AntiDetectionHTTPClient()
        
        # Mock curl_cffi to fail
        with patch.object(client, '_curl_cffi_request', side_effect=Exception("curl failed")):
            # Mock tls_client to succeed
            with patch.object(client, '_tls_client_request', return_value={'status': 200}):
                result = await client.request('GET', 'https://example.com')
                assert result['status'] == 200
    
    @pytest.mark.asyncio
    async def test_discord_fallback(self):
        """Test Discord client fallback to original method"""
        from discord_client import AntiDetectionHTTPClient
        from unittest.mock import MagicMock
        
        http_client = AntiDetectionHTTPClient()
        http_client._original_request = AsyncMock(return_value={'data': 'success'})
        
        # Mock anti-detection to fail
        with patch.object(http_client, '_anti_detection_request', side_effect=Exception("Anti-detection failed")):
            # Should fallback
            route = Mock()
            route.url = '/channels/123/messages'  # Critical endpoint
            
            result = await http_client.request(route)
            assert result == {'data': 'success'}
            http_client._original_request.assert_called_once()


class TestSafetyIntegration:
    """Test integration with existing safety features"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_compatibility(self):
        """Test that circuit breaker works with anti-detection"""
        from worker import CircuitBreaker
        
        breaker = CircuitBreaker(failure_threshold=2)
        
        # Mock function that fails
        async def failing_request():
            raise Exception("Request failed")
        
        # Should allow retries up to threshold
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_request)
        
        # Should open circuit
        with pytest.raises(Exception, match="Circuit breaker opened"):
            await breaker.call(failing_request)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])