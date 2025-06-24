# Key Points to Remember

## Project Architecture
- **Full-stack application** with self-bot Discord scraping capabilities
- **Backend**: FastAPI + PostgreSQL + Redis + Background Worker
- **Frontend**: React dashboard for managing scraping jobs
- **Self-bot**: Advanced anti-detection implementation using curl_cffi and tls-client

## Critical Security Measures Already Implemented
1. **TLS Fingerprinting Bypass** - Using curl_cffi and tls-client
2. **Browser Profile Rotation** - Realistic distribution (Chrome 55%, etc.)
3. **Rate Limiting** - 80 messages/hour max with burst control
4. **Human-like Patterns** - Gaussian noise, breaks, active hours
5. **Circuit Breaker** - Automatic failure handling

## What NOT to Add (Overengineering)
- ❌ HTTP/2 SETTINGS fingerprinting
- ❌ WebSocket gateway presence for self-bots
- ❌ Canvas/Audio/WebGL fingerprinting (browser-only)
- ❌ Memory fingerprinting (Discord can't monitor this)
- ❌ Token "heat" tracking (already have risk scoring)
- ❌ Excessive API call diversity

## Essential Commands
```bash
# First time setup
cp .env.example .env
./scripts/clean_start.sh

# Database issues
./scripts/clean_start.sh --reset-db

# Quick commands
docker-compose up -d
docker-compose logs -f
docker-compose down
```

## Environment Variables (Minimum Required)
```
JWT_SECRET_KEY=your-secret-key
TOKEN_ENCRYPTION_KEY=your-encryption-key
SELFBOT_WARNING_ACCEPTED=true  # Must be true for self-bot mode
```

## Key Design Principles
1. **Safety First** - Rate limits and breaks are more important than exotic features
2. **Pragmatic Approach** - Focus on real detection vectors, not theoretical ones
3. **Minimize Footprint** - Don't make unnecessary API calls
4. **Fallback Mechanisms** - Always have a plan B when anti-detection fails

## Current Anti-Detection Rating: 8/10
- The missing 2 points are inherent to self-bots, not fixable with more features
- Adding more complexity would increase failure points without meaningful benefit