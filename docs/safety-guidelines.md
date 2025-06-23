# Safety Guidelines for Discord Self-Bot Usage

## Overview

This document provides comprehensive safety guidelines to minimize the risk of detection when using the Discord self-bot scraper. Following these guidelines does not guarantee safety but significantly reduces risk.

## Pre-Operation Checklist

- [ ] Using a test/alt account (NOT your main account)
- [ ] Token encryption key is set in environment
- [ ] Anti-detection settings are configured
- [ ] You understand and accept the ToS violation risks
- [ ] VPN/proxy configured (optional but recommended)

## Operational Guidelines

### 1. Timing and Schedule

**DO:**
- Operate during normal human hours (9 AM - 11 PM local time)
- Take regular breaks (10-30 minutes every 2 hours)
- Vary your active hours day-to-day
- Limit sessions to 2-4 hours maximum

**DON'T:**
- Run 24/7 operations
- Maintain perfectly consistent schedules
- Operate during typical "bot hours" (3-6 AM)

### 2. Rate Limiting

**Recommended Limits:**
- Messages per minute: 2-4 (with variation)
- Messages per hour: 80 maximum
- Channels per session: 3-5
- Servers per day: 1-2

### 3. Behavioral Patterns

**Human-like Behaviors to Emulate:**
- Variable typing speeds and delays
- Occasional longer pauses (reading comprehension)
- Burst activity followed by quiet periods
- Mistakes and corrections (though not implemented)

**Bot-like Behaviors to Avoid:**
- Consistent timing between actions
- Perfect patterns or sequences
- Instant responses to events
- Accessing channels in predictable order

### 4. API Interaction

**Safe Practices:**
- Use random delays between 3-12 seconds
- Add gaussian noise to all delays
- Take burst breaks after 10-20 messages
- Mix different types of API calls

### 5. Error Handling

**When Errors Occur:**
- Circuit breaker will activate after 3 consecutive failures
- Wait for cooldown period (5 minutes minimum)
- Don't immediately retry failed operations
- Monitor error patterns for anomalies

## Risk Indicators

### Low Risk (Green)
- Risk score < 0.3
- Normal operation can continue
- Standard delays apply

### Medium Risk (Yellow) 
- Risk score 0.3 - 0.7
- Increase delays by 50%
- Reduce activity rate
- Consider taking a break

### High Risk (Red)
- Risk score > 0.7
- Immediate pause recommended
- Extended break required (30+ minutes)
- Review recent activity patterns

## Detection Indicators

Watch for these warning signs:
- Sudden API errors or rate limits
- Account verification requests
- Unusual Discord client behavior
- Connection drops or timeouts

## Emergency Procedures

If you suspect detection:
1. **Immediately stop all operations**
2. **Do not attempt to log in repeatedly**
3. **Wait at least 24 hours before any activity**
4. **Consider the account compromised**
5. **Rotate to a new account if necessary**

## Best Practices Summary

1. **Less is More**: It's better to scrape slowly than risk detection
2. **Randomness is Key**: Add variation to everything
3. **Monitor Constantly**: Watch risk scores and metrics
4. **Trust the Safety Systems**: If the system says pause, pause
5. **Have Backups**: Always have backup accounts ready

## Configuration Recommendations

```env
# Conservative settings for maximum safety
SELFBOT_MIN_DELAY=5
SELFBOT_MAX_DELAY=15
SELFBOT_MESSAGES_PER_HOUR=60
SELFBOT_ACTIVE_HOURS_START=10
SELFBOT_ACTIVE_HOURS_END=22
```

## Final Notes

Remember that no system is foolproof. Discord actively monitors for self-bot usage and their detection methods evolve constantly. The safest approach is to not use self-bots at all. If you choose to proceed, do so with full awareness of the risks and consequences.

Always prioritize account safety over scraping speed. A slow, careful approach is far better than a banned account.