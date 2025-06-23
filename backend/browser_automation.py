"""
Browser automation for handling JavaScript challenges
"""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import asyncio
from typing import Dict, Optional, List
import logging
import os
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class BrowserAutomationConfig:
    """Configuration for browser automation"""
    AUTO_SOLVE_LIMIT = 3
    AUTO_SOLVE_WINDOW = 1800  # 30 minutes
    MAX_CONSECUTIVE_FAILURES = 5
    HEADLESS = os.getenv('BROWSER_AUTOMATION_HEADLESS', 'true').lower() == 'true'
    TIMEOUT = int(os.getenv('BROWSER_AUTOMATION_TIMEOUT', '30'))
    MAX_CONCURRENT = int(os.getenv('BROWSER_AUTOMATION_MAX_CONCURRENT', '2'))
    RESOURCE_LIMIT_MB = int(os.getenv('BROWSER_AUTOMATION_RESOURCE_LIMIT_MB', '512'))


class ChallengeTracker:
    """Track JavaScript challenges per user/session"""
    def __init__(self):
        self.challenges = defaultdict(list)  # session_id -> list of timestamps
        self.consecutive_failures = defaultdict(int)
        self.total_challenges = 0
        self.successful_solves = 0
    
    def should_auto_solve(self, session_id: str) -> bool:
        """Check if we should auto-solve for this session"""
        now = datetime.now()
        
        # Clean old entries
        if session_id in self.challenges:
            self.challenges[session_id] = [
                ts for ts in self.challenges[session_id]
                if (now - ts).seconds < BrowserAutomationConfig.AUTO_SOLVE_WINDOW
            ]
        
        # Check limit
        recent_challenges = len(self.challenges[session_id])
        return recent_challenges < BrowserAutomationConfig.AUTO_SOLVE_LIMIT
    
    def record_challenge(self, session_id: str, success: bool):
        """Record a challenge attempt"""
        self.challenges[session_id].append(datetime.now())
        self.total_challenges += 1
        
        if success:
            self.consecutive_failures[session_id] = 0
            self.successful_solves += 1
        else:
            self.consecutive_failures[session_id] += 1
    
    def too_many_failures(self, session_id: str) -> bool:
        """Check if too many consecutive failures"""
        return self.consecutive_failures[session_id] >= BrowserAutomationConfig.MAX_CONSECUTIVE_FAILURES
    
    def get_stats(self) -> Dict:
        """Get challenge statistics"""
        return {
            'total_challenges': self.total_challenges,
            'successful_solves': self.successful_solves,
            'success_rate': self.successful_solves / max(1, self.total_challenges),
            'active_sessions': len(self.challenges),
        }


class BrowserPool:
    """Manage pool of browser instances"""
    def __init__(self, max_concurrent: int = 2):
        self.max_concurrent = max_concurrent
        self.active_browsers = 0
        self.browser_queue = asyncio.Queue(maxsize=max_concurrent)
        self._initialized = False
    
    async def initialize(self):
        """Initialize browser pool"""
        if self._initialized:
            return
        
        # Pre-create browsers
        for _ in range(self.max_concurrent):
            await self.browser_queue.put(None)  # Placeholder
        
        self._initialized = True
    
    async def acquire(self) -> Optional['BrowserAutomation']:
        """Acquire a browser from pool"""
        await self.initialize()
        
        # Wait for available slot
        await self.browser_queue.get()
        
        try:
            browser = BrowserAutomation()
            self.active_browsers += 1
            return browser
        except Exception as e:
            logger.error(f"Failed to create browser: {e}")
            # Return slot to queue
            await self.browser_queue.put(None)
            return None
    
    async def release(self, browser: Optional['BrowserAutomation']):
        """Release browser back to pool"""
        if browser:
            try:
                await browser.close()
            except:
                pass
            self.active_browsers -= 1
        
        # Return slot to queue
        await self.browser_queue.put(None)
    
    def get_stats(self) -> Dict:
        """Get pool statistics"""
        return {
            'max_concurrent': self.max_concurrent,
            'active_browsers': self.active_browsers,
            'available_slots': self.browser_queue.qsize(),
        }


class BrowserAutomation:
    """Handle JavaScript challenges using real browser"""
    
    def __init__(self):
        self.driver = None
        self.start_time = datetime.now()
        self._init_driver()
    
    def _init_driver(self):
        """Initialize undetected Chrome driver"""
        options = uc.ChromeOptions()
        
        # Anti-detection options
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Performance options
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-software-rasterizer')
        
        # Memory optimization
        options.add_argument('--memory-pressure-off')
        options.add_argument(f'--max_old_space_size={BrowserAutomationConfig.RESOURCE_LIMIT_MB}')
        
        # Headless mode
        if BrowserAutomationConfig.HEADLESS:
            options.add_argument('--headless=new')  # New headless mode
            options.add_argument('--window-size=1920,1080')
        
        # Additional privacy
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')  # Re-enable per page
        
        try:
            # Create driver with specific Chrome version
            self.driver = uc.Chrome(options=options, version_main=112)
            
            # Set timeouts
            self.driver.set_page_load_timeout(BrowserAutomationConfig.TIMEOUT)
            self.driver.implicitly_wait(10)
            
            logger.info("Browser automation initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise
    
    async def solve_challenge(self, url: str, headers: Dict[str, str]) -> Optional[Dict[str, str]]:
        """Solve JavaScript challenge and return cookies/headers"""
        loop = asyncio.get_event_loop()
        
        def _solve():
            try:
                # Set headers using CDP
                self.driver.execute_cdp_cmd('Network.enable', {})
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    'userAgent': headers.get('User-Agent', self.driver.execute_script('return navigator.userAgent'))
                })
                
                # Set additional headers
                extra_headers = {}
                for key, value in headers.items():
                    if key.lower() not in ['user-agent', 'cookie']:
                        extra_headers[key] = value
                
                if extra_headers:
                    self.driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                        'headers': extra_headers
                    })
                
                # Enable JavaScript for this page
                self.driver.execute_cdp_cmd('Emulation.setScriptExecutionDisabled', {
                    'value': False
                })
                
                # Navigate to URL
                logger.info(f"Navigating to {url} for challenge solving")
                self.driver.get(url)
                
                # Wait for challenge to complete
                challenge_complete = self._wait_for_challenge_completion()
                
                if not challenge_complete:
                    raise Exception("Challenge completion timeout")
                
                # Extract cookies and other data
                cookies = self.driver.get_cookies()
                
                # Get any additional headers set by JavaScript
                local_storage = self.driver.execute_script("return window.localStorage")
                session_storage = self.driver.execute_script("return window.sessionStorage")
                
                result = {
                    'cookies': '; '.join([f"{c['name']}={c['value']}" for c in cookies]),
                    'user_agent': self.driver.execute_script("return navigator.userAgent"),
                    'local_storage': local_storage,
                    'session_storage': session_storage,
                }
                
                logger.info("Successfully solved JavaScript challenge")
                return result
                
            except Exception as e:
                logger.error(f"Browser automation failed: {e}")
                # Take screenshot for debugging
                if self.driver and not BrowserAutomationConfig.HEADLESS:
                    try:
                        self.driver.save_screenshot(f"challenge_error_{datetime.now().timestamp()}.png")
                    except:
                        pass
                return None
        
        return await loop.run_in_executor(None, _solve)
    
    def _wait_for_challenge_completion(self) -> bool:
        """Wait for challenge to complete with multiple strategies"""
        wait = WebDriverWait(self.driver, BrowserAutomationConfig.TIMEOUT)
        
        # Strategy 1: Wait for specific completion indicators
        completion_indicators = [
            (By.TAG_NAME, 'body'),                    # Page loads
            (By.ID, 'app-mount'),                     # Discord app mount
            (By.CLASS_NAME, 'app'),                   # Discord app
            (By.CSS_SELECTOR, '[data-app-loaded]'),  # Custom indicator
        ]
        
        for indicator in completion_indicators:
            try:
                wait.until(EC.presence_of_element_located(indicator))
                # Additional wait for dynamic content
                wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
                return True
            except:
                continue
        
        # Strategy 2: Check for challenge elements disappearing
        challenge_selectors = [
            '.challenge-container',
            '#challenge-form',
            '.cf-challenge',
        ]
        
        for selector in challenge_selectors:
            try:
                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, selector)))
                return True
            except:
                continue
        
        # Strategy 3: Check URL change
        original_url = self.driver.current_url
        try:
            wait.until(lambda driver: driver.current_url != original_url)
            return True
        except:
            pass
        
        return False
    
    async def close(self):
        """Close browser instance"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def get_resource_usage(self) -> Dict:
        """Get browser resource usage"""
        if not self.driver:
            return {}
        
        try:
            # Get memory info via JavaScript
            memory_info = self.driver.execute_script("""
                return {
                    jsHeapSizeLimit: performance.memory.jsHeapSizeLimit,
                    totalJSHeapSize: performance.memory.totalJSHeapSize,
                    usedJSHeapSize: performance.memory.usedJSHeapSize
                }
            """)
            
            return {
                'uptime_seconds': (datetime.now() - self.start_time).seconds,
                'memory_mb': memory_info.get('usedJSHeapSize', 0) / 1024 / 1024,
                'memory_limit_mb': memory_info.get('jsHeapSizeLimit', 0) / 1024 / 1024,
            }
        except:
            return {}


# Global instances
_browser_pool = None
_challenge_tracker = ChallengeTracker()


def get_browser_pool() -> BrowserPool:
    """Get or create browser pool"""
    global _browser_pool
    if _browser_pool is None:
        _browser_pool = BrowserPool(BrowserAutomationConfig.MAX_CONCURRENT)
    return _browser_pool


async def handle_javascript_challenge(url: str, headers: Dict[str, str], 
                                    session_id: str) -> Optional[Dict[str, str]]:
    """Main entry point for handling JavaScript challenges"""
    
    # Check if we should auto-solve
    if not _challenge_tracker.should_auto_solve(session_id):
        logger.warning(f"Challenge limit reached for session {session_id}")
        return None
    
    # Check for too many failures
    if _challenge_tracker.too_many_failures(session_id):
        logger.error(f"Too many consecutive failures for session {session_id}")
        return None
    
    pool = get_browser_pool()
    browser = None
    
    try:
        # Acquire browser from pool
        browser = await pool.acquire()
        if not browser:
            raise Exception("Failed to acquire browser from pool")
        
        # Solve challenge
        result = await browser.solve_challenge(url, headers)
        
        # Record result
        _challenge_tracker.record_challenge(session_id, result is not None)
        
        return result
        
    except Exception as e:
        logger.error(f"Challenge handling failed: {e}")
        _challenge_tracker.record_challenge(session_id, False)
        return None
        
    finally:
        # Release browser back to pool
        if browser:
            await pool.release(browser)


def get_automation_stats() -> Dict:
    """Get browser automation statistics"""
    pool = get_browser_pool()
    return {
        'challenge_tracker': _challenge_tracker.get_stats(),
        'browser_pool': pool.get_stats(),
        'config': {
            'headless': BrowserAutomationConfig.HEADLESS,
            'timeout': BrowserAutomationConfig.TIMEOUT,
            'auto_solve_limit': BrowserAutomationConfig.AUTO_SOLVE_LIMIT,
        }
    }