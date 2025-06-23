"""
Advanced HTTP client with anti-detection capabilities
"""
from curl_cffi import requests as curl_requests
from tls_client import Session as TLSSession
import random
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import aiohttp
import json
import logging
import os
from collections import defaultdict

logger = logging.getLogger(__name__)


class BrowserProfile:
    """Browser profiles for impersonation"""
    PROFILES = {
        'chrome_win': {
            'curl_cffi': 'chrome110',
            'tls_client': 'chrome_112',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'sec_ch_ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
            'sec_ch_ua_platform': '"Windows"',
            'weight': 55,  # Percentage weight for selection
        },
        'chrome_mac': {
            'curl_cffi': 'chrome110',
            'tls_client': 'chrome_112',
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'sec_ch_ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
            'sec_ch_ua_platform': '"macOS"',
            'weight': 25,
        },
        'firefox_win': {
            'curl_cffi': 'firefox109',
            'tls_client': 'firefox_110',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:110.0) Gecko/20100101 Firefox/110.0',
            'weight': 15,
        },
        'safari_mac': {
            'curl_cffi': 'safari16',
            'tls_client': 'safari_16_0',
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
            'weight': 5,
        }
    }
    
    @classmethod
    def get_random_profile(cls) -> Dict[str, Any]:
        """Get a random browser profile"""
        profile_name = random.choice(list(cls.PROFILES.keys()))
        return {'name': profile_name, **cls.PROFILES[profile_name]}
    
    @classmethod
    def get_weighted_profile(cls) -> Dict[str, Any]:
        """Get a browser profile based on realistic distribution weights"""
        profiles = list(cls.PROFILES.items())
        weights = [profile[1]['weight'] for profile in profiles]
        chosen = random.choices(profiles, weights=weights, k=1)[0]
        return {'name': chosen[0], **chosen[1]}


class SessionProfileManager:
    """Manage browser profiles per session"""
    def __init__(self):
        self._profile_cache = {}
        self._profile_timestamps = {}
    
    def get_or_create_profile(self, session_id: str) -> Dict[str, Any]:
        """Get existing or create new profile for session"""
        # Check if session has existing profile
        if session_id in self._profile_cache:
            # Check if profile should be rotated (after 2-4 hours)
            if session_id in self._profile_timestamps:
                age = (datetime.now() - self._profile_timestamps[session_id]).seconds
                if age > random.randint(7200, 14400):  # 2-4 hours
                    del self._profile_cache[session_id]
                    del self._profile_timestamps[session_id]
                else:
                    return self._profile_cache[session_id]
        
        # Create new profile for session
        profile = BrowserProfile.get_weighted_profile()
        self._profile_cache[session_id] = profile
        self._profile_timestamps[session_id] = datetime.now()
        return profile
    
    def clear_old_profiles(self):
        """Clean up old profiles"""
        now = datetime.now()
        expired = []
        for session_id, timestamp in self._profile_timestamps.items():
            if (now - timestamp).seconds > 14400:  # 4 hours
                expired.append(session_id)
        
        for session_id in expired:
            self._profile_cache.pop(session_id, None)
            self._profile_timestamps.pop(session_id, None)


class AntiDetectionHTTPClient:
    """HTTP client with advanced anti-detection features"""
    
    # Connection pool configuration
    CONNECTION_POOLS = {
        'chrome_win': {'max_connections': 10, 'keepalive': 60},
        'chrome_mac': {'max_connections': 10, 'keepalive': 60},
        'firefox_win': {'max_connections': 8, 'keepalive': 45},
        'safari_mac': {'max_connections': 6, 'keepalive': 30},
    }
    
    # Rate limits per client type
    RATE_LIMITS = {
        'curl_cffi': {'requests_per_second': 2, 'burst': 5},
        'tls_client': {'requests_per_second': 1.5, 'burst': 4},
        'browser_auto': {'requests_per_second': 0.5, 'burst': 2},
    }
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or 'default'
        self.profile_manager = SessionProfileManager()
        self.profile = self.profile_manager.get_or_create_profile(self.session_id)
        self.session_rotation_count = 0
        self.max_requests_per_session = random.randint(50, 150)
        self.curl_session = None
        self.tls_session = None
        self.last_request_time = None
        self.request_timings = []  # Track request timings for pattern analysis
        self.session_start_time = datetime.now()
        self.request_counts = defaultdict(int)  # Track requests per client type
        self._init_sessions()
    
    def _init_sessions(self):
        """Initialize HTTP sessions with browser impersonation"""
        try:
            # Initialize curl_cffi session
            self.curl_session = curl_requests.Session(
                impersonate=self.profile['curl_cffi']
            )
            
            # Initialize tls-client session
            self.tls_session = TLSSession(
                client_identifier=self.profile['tls_client']
            )
        except Exception as e:
            logger.error(f"Failed to initialize sessions: {e}")
            # Fall back to standard session if specialized clients fail
            self.curl_session = None
            self.tls_session = None
        
        # Set common headers
        self.default_headers = {
            'User-Agent': self.profile['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add Chrome-specific headers if using Chrome profile
        if 'chrome' in self.profile.get('curl_cffi', ''):
            self.default_headers.update({
                'sec-ch-ua': self.profile.get('sec_ch_ua', ''),
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': self.profile.get('sec_ch_ua_platform', ''),
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Sec-Fetch-Dest': 'document',
            })
    
    def _should_rotate_session(self) -> bool:
        """Determine if session should be rotated"""
        self.session_rotation_count += 1
        
        # Rotate based on request count
        if self.session_rotation_count >= self.max_requests_per_session:
            return True
        
        # Rotate based on time (every 30-60 minutes)
        session_age = (datetime.now() - self.session_start_time).seconds
        if session_age > random.randint(1800, 3600):
            return True
        
        return False
    
    def _rotate_session(self):
        """Rotate to a new browser profile and session"""
        logger.info("Rotating HTTP session and browser profile")
        
        # Close existing sessions
        if self.curl_session:
            try:
                self.curl_session.close()
            except:
                pass
        
        # Get new profile
        self.profile = self.profile_manager.get_or_create_profile(self.session_id)
        self.session_rotation_count = 0
        self.max_requests_per_session = random.randint(50, 150)
        self.session_start_time = datetime.now()
        
        # Reinitialize sessions
        self._init_sessions()
    
    def _add_timing_variance(self):
        """Add human-like timing variance between requests"""
        if self.last_request_time:
            # Calculate time since last request
            time_delta = (datetime.now() - self.last_request_time).total_seconds()
            
            # If requests are too regular, add extra delay
            if len(self.request_timings) > 5:
                recent_timings = self.request_timings[-5:]
                avg_timing = sum(recent_timings) / len(recent_timings)
                variance = sum((t - avg_timing) ** 2 for t in recent_timings) / len(recent_timings)
                
                # Low variance means bot-like behavior
                if variance < 2.0:
                    extra_delay = random.uniform(0.5, 3.0)
                    asyncio.create_task(asyncio.sleep(extra_delay))
            
            self.request_timings.append(time_delta)
            # Keep only last 20 timings
            self.request_timings = self.request_timings[-20:]
        
        self.last_request_time = datetime.now()
    
    async def _apply_rate_limit(self, client_type: str):
        """Apply rate limiting based on client type"""
        rate_limit = self.RATE_LIMITS.get(client_type, self.RATE_LIMITS['curl_cffi'])
        
        # Simple token bucket implementation
        current_count = self.request_counts[client_type]
        if current_count >= rate_limit['burst']:
            # Calculate wait time
            wait_time = 1.0 / rate_limit['requests_per_second']
            await asyncio.sleep(wait_time)
            self.request_counts[client_type] = 0
        else:
            self.request_counts[client_type] += 1
    
    async def request(self, method: str, url: str, headers: Optional[Dict] = None, 
                     data: Optional[Any] = None, json_data: Optional[Dict] = None,
                     use_tls_client: bool = False) -> Dict[str, Any]:
        """Make HTTP request with anti-detection measures"""
        
        # Check if session rotation needed
        if self._should_rotate_session():
            self._rotate_session()
        
        # Add timing variance
        self._add_timing_variance()
        
        # Merge headers
        request_headers = {**self.default_headers}
        if headers:
            request_headers.update(headers)
        
        # Randomly order headers (browsers don't always send headers in same order)
        header_items = list(request_headers.items())
        random.shuffle(header_items)
        request_headers = dict(header_items)
        
        try:
            # Choose client based on parameter or random
            if use_tls_client or random.random() < 0.3:  # 30% chance to use tls-client
                client_type = 'tls_client'
                await self._apply_rate_limit(client_type)
                response = await self._tls_client_request(
                    method, url, request_headers, data, json_data
                )
            else:
                client_type = 'curl_cffi'
                await self._apply_rate_limit(client_type)
                response = await self._curl_cffi_request(
                    method, url, request_headers, data, json_data
                )
            
            # Check for JavaScript challenge
            if self._is_javascript_challenge(response):
                logger.warning("JavaScript challenge detected, attempting browser automation")
                response = await self._handle_javascript_challenge(url, request_headers)
            
            return response
            
        except Exception as e:
            logger.error(f"Request failed with {client_type}: {e}")
            # Try alternate client on failure
            if not use_tls_client:
                return await self.request(method, url, headers, data, json_data, use_tls_client=True)
            raise
    
    async def _curl_cffi_request(self, method: str, url: str, headers: Dict,
                                data: Any, json_data: Dict) -> Dict[str, Any]:
        """Make request using curl_cffi"""
        
        if not self.curl_session:
            raise Exception("curl_cffi session not initialized")
        
        # curl_cffi is synchronous, so run in executor
        loop = asyncio.get_event_loop()
        
        def _make_request():
            if json_data:
                return self.curl_session.request(
                    method, url, headers=headers, json=json_data
                )
            else:
                return self.curl_session.request(
                    method, url, headers=headers, data=data
                )
        
        response = await loop.run_in_executor(None, _make_request)
        
        return {
            'status': response.status_code,
            'headers': dict(response.headers),
            'text': response.text,
            'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
        }
    
    async def _tls_client_request(self, method: str, url: str, headers: Dict,
                                 data: Any, json_data: Dict) -> Dict[str, Any]:
        """Make request using tls-client"""
        
        if not self.tls_session:
            raise Exception("tls-client session not initialized")
        
        # tls-client is also synchronous
        loop = asyncio.get_event_loop()
        
        def _make_request():
            if json_data:
                return self.tls_session.request(
                    method, url, headers=headers, json=json_data
                )
            else:
                return self.tls_session.request(
                    method, url, headers=headers, data=data
                )
        
        response = await loop.run_in_executor(None, _make_request)
        
        return {
            'status': response.status_code,
            'headers': dict(response.headers),
            'text': response.text,
            'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
        }
    
    def _is_javascript_challenge(self, response: Dict[str, Any]) -> bool:
        """Detect if response contains JavaScript challenge"""
        if response['status'] in [403, 503]:
            text = response.get('text', '')
            # Common challenge indicators
            challenge_indicators = [
                'challenge-platform',
                'jschl-answer',
                'cf-challenge',
                '__cf_chl_jschl_tk__',
                'Checking your browser',
                'DDoS protection by'
            ]
            return any(indicator in text for indicator in challenge_indicators)
        return False
    
    async def _handle_javascript_challenge(self, url: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Handle JavaScript challenge using browser automation"""
        if not os.getenv('ENABLE_BROWSER_AUTOMATION', 'true').lower() == 'true':
            raise Exception("Browser automation disabled")
        
        try:
            from browser_automation import handle_javascript_challenge
            
            # Get challenge solution from browser
            result = await handle_javascript_challenge(url, headers, self.session_id)
            
            if not result:
                raise Exception("Failed to solve JavaScript challenge")
            
            # Update headers with cookies from browser
            if 'cookies' in result:
                headers['Cookie'] = result['cookies']
            
            # Retry the request with new cookies/headers
            if hasattr(self, 'curl_session'):
                return await self._curl_cffi_request('GET', url, headers, None, None)
            else:
                return await self._tls_client_request('GET', url, headers, None, None)
                
        except ImportError:
            logger.error("Browser automation module not available")
            raise Exception("Browser automation not available")
        except Exception as e:
            logger.error(f"JavaScript challenge handling failed: {e}")
            raise
    
    def get_current_profile(self) -> Dict[str, Any]:
        """Get current browser profile"""
        return self.profile
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            'session_id': self.session_id,
            'profile': self.profile['name'],
            'requests_made': self.session_rotation_count,
            'session_age': (datetime.now() - self.session_start_time).seconds,
            'request_counts': dict(self.request_counts),
        }


# Global client instances per session
_http_clients: Dict[str, AntiDetectionHTTPClient] = {}

def get_http_client(session_id: Optional[str] = None) -> AntiDetectionHTTPClient:
    """Get or create HTTP client instance for session"""
    session_id = session_id or 'default'
    
    if session_id not in _http_clients:
        _http_clients[session_id] = AntiDetectionHTTPClient(session_id)
    
    return _http_clients[session_id]

def cleanup_old_clients():
    """Clean up old client instances"""
    # This should be called periodically
    for session_id in list(_http_clients.keys()):
        client = _http_clients[session_id]
        if (datetime.now() - client.session_start_time).seconds > 14400:  # 4 hours
            del _http_clients[session_id]