"""
Custom Discord client with anti-detection HTTP backend
"""
import discord
from discord.ext import commands
from discord.http import Route, HTTPClient
from typing import Any, Dict, Optional, Union
import json
import asyncio
import logging
import base64
from datetime import datetime, timedelta
import os

from http_client import get_http_client
from config import settings

logger = logging.getLogger(__name__)


# Critical endpoints for anti-detection (highest risk)
CRITICAL_ENDPOINTS = [
    '/users/@me',
    '/guilds',
    '/channels',
    '/messages',
    '/gateway',
    '/auth/login',
]

# Header introduction schedule (seconds after session start)
HEADER_INTRODUCTION_SCHEDULE = [
    (0, ['Authorization', 'User-Agent']),      # Always
    (300, ['X-Super-Properties']),             # After 5 minutes
    (900, ['X-Discord-Locale']),               # After 15 minutes
    (1800, ['X-Debug-Options']),               # After 30 minutes
]

# Cache for Discord build numbers
_build_number_cache = {
    'number': 199933,
    'last_updated': datetime.now(),
}


class AntiDetectionHTTPClient(HTTPClient):
    """Discord HTTP client using anti-detection measures"""
    
    def __init__(self, connector=None, *, proxy=None, proxy_auth=None, 
                 loop=None, unsync_clock=True, session_id=None):
        super().__init__(connector, proxy=proxy, proxy_auth=proxy_auth, 
                        loop=loop, unsync_clock=unsync_clock)
        self.session_id = session_id
        self.http_client = get_http_client(session_id)
        self.session_start_time = datetime.now()
        self._original_request = super().request  # Store original method
        
    async def request(self, route: Route, *, files: Any = None, form: Any = None,
                     **kwargs: Any) -> Any:
        """Override request method to use anti-detection for critical endpoints"""
        
        # Check if this is a critical endpoint
        is_critical = any(endpoint in str(route.url) for endpoint in CRITICAL_ENDPOINTS)
        
        # Use anti-detection client only if enabled and for critical endpoints
        if settings.enable_anti_detection and is_critical:
            try:
                return await self._anti_detection_request(route, files=files, form=form, **kwargs)
            except Exception as e:
                logger.error(f"Anti-detection request failed: {e}")
                # Fallback to original if configured
                if settings.anti_detection_fallback:
                    logger.warning("Falling back to standard request")
                    return await self._original_request(route, files=files, form=form, **kwargs)
                raise
        else:
            # Use original request method for non-critical endpoints
            return await self._original_request(route, files=files, form=form, **kwargs)
    
    async def _anti_detection_request(self, route: Route, *, files: Any = None, 
                                     form: Any = None, **kwargs: Any) -> Any:
        """Make request using anti-detection HTTP client"""
        
        method = route.method
        url = f"{self.BASE}{route.path}"
        
        # Prepare headers
        headers = await self._get_headers()
        
        # Handle different content types
        data = None
        json_data = None
        
        if form:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            data = form
        elif kwargs.get('json'):
            headers['Content-Type'] = 'application/json'
            json_data = kwargs['json']
        
        # Make request with retries
        for attempt in range(5):  # Discord.py default is 5
            try:
                response = await self.http_client.request(
                    method, url, headers=headers, data=data, json_data=json_data
                )
                
                # Handle rate limits
                if response['status'] == 429:
                    retry_after = response.get('json', {}).get('retry_after', 5)
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    continue
                
                # Success
                if 200 <= response['status'] < 300:
                    return response.get('json') or response.get('text')
                
                # Client error
                if response['status'] >= 400:
                    raise discord.HTTPException(
                        {'status': response['status']}, 
                        response.get('json', {'message': response.get('text', 'Unknown error')})
                    )
                    
            except discord.HTTPException:
                raise
            except Exception as e:
                if attempt == 4:  # Last attempt
                    raise
                wait_time = 1 + attempt * 2
                logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get headers with gradual introduction based on session age"""
        headers = {}
        
        # Always include authorization
        if hasattr(self, 'token'):
            headers['Authorization'] = self.token
        
        # Get browser profile from HTTP client
        profile = self.http_client.get_current_profile()
        headers['User-Agent'] = profile['user_agent']
        
        # Calculate session age
        session_age = (datetime.now() - self.session_start_time).total_seconds()
        
        # Gradually introduce headers
        for age_threshold, header_list in HEADER_INTRODUCTION_SCHEDULE:
            if session_age >= age_threshold:
                if 'X-Super-Properties' in header_list:
                    headers['X-Super-Properties'] = self._get_super_properties()
                if 'X-Discord-Locale' in header_list:
                    headers['X-Discord-Locale'] = 'en-US'
                if 'X-Debug-Options' in header_list:
                    headers['X-Debug-Options'] = 'bugReporterEnabled'
        
        # Add common Discord headers
        headers.update({
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        })
        
        return headers
    
    def _get_super_properties(self) -> str:
        """Generate X-Super-Properties header"""
        # Get browser profile
        profile = self.http_client.get_current_profile()
        
        # Determine OS and browser from profile
        if 'chrome_win' in profile['name']:
            os_name = "Windows"
            browser = "Chrome"
            browser_version = "112.0.0.0"
            os_version = "10"
        elif 'chrome_mac' in profile['name']:
            os_name = "Mac OS X"
            browser = "Chrome"
            browser_version = "112.0.0.0"
            os_version = "10.15.7"
        elif 'firefox_win' in profile['name']:
            os_name = "Windows"
            browser = "Firefox"
            browser_version = "110.0"
            os_version = "10"
        else:  # safari_mac
            os_name = "Mac OS X"
            browser = "Safari"
            browser_version = "16.0"
            os_version = "10.15.7"
        
        # Get current build number
        build_number = self._get_discord_build_number()
        
        properties = {
            "os": os_name,
            "browser": browser,
            "device": "",
            "system_locale": "en-US",
            "browser_user_agent": profile['user_agent'],
            "browser_version": browser_version,
            "os_version": os_version,
            "referrer": "",
            "referring_domain": "",
            "referrer_current": "",
            "referring_domain_current": "",
            "release_channel": "stable",
            "client_build_number": build_number,
            "client_event_source": None
        }
        
        return base64.b64encode(json.dumps(properties).encode()).decode()
    
    def _get_discord_build_number(self) -> int:
        """Get current Discord build number (with caching)"""
        global _build_number_cache
        
        # Check if cache is still valid (update daily)
        if (datetime.now() - _build_number_cache['last_updated']).days >= 1:
            # In production, this would fetch from Discord or GitHub
            # For now, use a recent known build number
            _build_number_cache['number'] = 199933
            _build_number_cache['last_updated'] = datetime.now()
        
        return _build_number_cache['number']


class AntiDetectionBot(commands.Bot):
    """Discord bot with anti-detection HTTP client"""
    
    def __init__(self, *args, session_id: Optional[str] = None, **kwargs):
        self.session_id = session_id
        super().__init__(*args, **kwargs)
        
    async def login(self, token: str) -> None:
        """Override login to use our HTTP client"""
        # Create our custom HTTP client
        self.http = AntiDetectionHTTPClient(
            connector=self.connector,
            proxy=self.proxy,
            proxy_auth=self.proxy_auth,
            loop=self.loop,
            unsync_clock=self._connection.unsync_clock,
            session_id=self.session_id
        )
        
        # Set the token
        self.http.token = token
        self._connection.http = self.http
        
        # Continue with normal login
        await self._connection.static_login(token)


# Monkey-patch discord.py-self if needed
def patch_discord_http():
    """Monkey-patch discord.py-self's HTTPClient for backwards compatibility"""
    if not settings.enable_anti_detection:
        return
    
    # Store original for fallback
    import discord.http
    _original_request = discord.http.HTTPClient.request
    
    async def patched_request(self, route, **kwargs):
        # Check if this is a critical endpoint
        is_critical = any(endpoint in str(route.url) for endpoint in CRITICAL_ENDPOINTS)
        
        if is_critical and hasattr(self, '_anti_detection_client'):
            try:
                # Use anti-detection client
                return await self._anti_detection_client.request(route, **kwargs)
            except Exception as e:
                logger.error(f"Anti-detection request failed: {e}")
                if settings.anti_detection_fallback:
                    return await _original_request(self, route, **kwargs)
                raise
        
        return await _original_request(self, route, **kwargs)
    
    # Apply patch
    discord.http.HTTPClient.request = patched_request
    logger.info("Discord HTTP client patched for anti-detection")


# Auto-patch on import if enabled
if settings.enable_anti_detection:
    patch_discord_http()