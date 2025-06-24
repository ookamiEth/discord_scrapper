# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack Discord scraper application with self-bot capabilities. It consists of:
- **Backend**: FastAPI with PostgreSQL database and Redis queue
- **Frontend**: React + TypeScript dashboard for managing scraping jobs
- **Worker**: Background job processor for Discord scraping
- **Self-bot**: Advanced anti-detection Discord client implementation

## Common Commands

### Quick Start & Shutdown

```bash
# Start the application
./start.sh                    # Easy startup script that starts all services

# Stop the application
# Option 1: Use the shutdown button in the web UI (profile menu → Shutdown App)
# Option 2: Run from terminal
docker-compose down           # Stop all services
```

### Docker Development

```bash
# Initial setup
cp .env.example .env  # Then edit with your keys
./scripts/clean_start.sh

# Quick commands
docker-compose up -d          # Start all services
docker-compose down           # Stop all services
docker-compose logs -f        # View logs
docker-compose ps            # Check service status

# Database management
./scripts/clean_start.sh --reset-db  # Full database reset
docker-compose exec backend alembic upgrade head  # Run migrations
docker-compose exec backend alembic stamp head    # Mark migrations as applied

# Development
docker-compose exec backend bash     # Backend shell
docker-compose exec worker bash      # Worker shell
docker-compose exec postgres psql -U discord_user -d discord_scraper  # Database shell
```

### Backend Development

```bash
# Inside backend container
python -m pytest                     # Run tests
python -m black .                    # Format code
python -m flake8                     # Lint code
alembic revision -m "description"    # Create new migration
```

### Frontend Development

```bash
# Inside frontend container or locally
npm run dev                          # Start development server
npm run build                        # Build production
npm run lint                         # Lint code
npm run type-check                   # Check TypeScript
```

## Repository Structure

```
discord_scrapper/
├── backend/                    # FastAPI backend application
│   ├── api/                   # API endpoints
│   ├── core/                  # Core utilities (security, config, etc.)
│   ├── crud/                  # Database operations
│   ├── models/                # SQLAlchemy models
│   ├── routers/               # API route handlers
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── servers.py        # Server management
│   │   ├── scraping.py       # Scraping jobs
│   │   └── system.py         # System control (shutdown)
│   ├── schemas/               # Pydantic schemas
│   ├── services/              # Business logic
│   │   ├── discord/          # Discord integration
│   │   │   ├── anti_detection/  # Anti-detection measures
│   │   │   └── selfbot.py    # Self-bot implementation
│   │   └── scraper/          # Scraping logic
│   ├── alembic/              # Database migrations
│   ├── main.py               # FastAPI app entry point
│   └── worker.py             # Background job processor
├── frontend/                  # React frontend application
│   ├── src/
│   │   ├── components/       # React components
│   │   │   └── Layout.tsx    # Main layout with shutdown button
│   │   ├── pages/           # Page components
│   │   ├── services/        # API client services
│   │   │   └── system.ts    # System API calls (shutdown)
│   │   └── store/           # Redux store
│   └── package.json
├── scripts/                   # Utility scripts
│   └── clean_start.sh        # Database reset and startup script
├── start.sh                   # Quick start script
├── exports/                   # Export directory for scraped data
├── docker-compose.yml         # Docker services configuration
├── .env.example              # Environment variables template
└── CLAUDE.md                 # This file
```

## Important Notes

### Shutdown Feature

The application includes a convenient shutdown feature to save system resources:

1. **Web UI Shutdown**: Click your profile icon → "Shutdown App" button (red power icon)
2. **Terminal Shutdown**: Run `docker-compose down`
3. **Auto-shutdown Protection**: Confirms before shutting down to prevent accidents
4. **Resource Efficiency**: Stops all Docker containers when not in use

To restart after shutdown, simply run `./start.sh`.

### Self-Bot Mode Safety

1. **Terms of Service**: Self-bots violate Discord's ToS. Use at your own risk.
2. **Rate Limiting**: The application enforces strict rate limits (80 messages/hour by default)
3. **Anti-Detection**: Advanced measures are implemented but detection is always possible
4. **Environment Setup**: You MUST set `SELFBOT_WARNING_ACCEPTED=true` to enable self-bot mode

### Security Keys

Generate secure keys for production:
```bash
# Generate JWT secret
openssl rand -base64 32

# Generate encryption key
openssl rand -base64 32
```

### Common Issues

1. **Database already exists**: Use `./scripts/clean_start.sh --reset-db`
2. **Missing discord.py-self**: Install in backend container: `pip install discord.py-self`
3. **Port conflicts**: Ensure ports 3000, 8000, 5432, 6379 are available
4. **Memory issues**: Increase Docker memory allocation in Docker Desktop settings

## Key Architecture Points

### Project Components
- **Full-stack application** with self-bot Discord scraping capabilities
- **Backend**: FastAPI + PostgreSQL + Redis + Background Worker
- **Frontend**: React dashboard for managing scraping jobs
- **Self-bot**: Advanced anti-detection implementation using curl_cffi and tls-client

### Critical Security Measures Already Implemented
1. **TLS Fingerprinting Bypass** - Using curl_cffi and tls-client
2. **Browser Profile Rotation** - Realistic distribution (Chrome 55%, etc.)
3. **Rate Limiting** - 80 messages/hour max with burst control
4. **Human-like Patterns** - Gaussian noise, breaks, active hours
5. **Circuit Breaker** - Automatic failure handling

### What NOT to Add (Overengineering)
- ❌ HTTP/2 SETTINGS fingerprinting
- ❌ WebSocket gateway presence for self-bots
- ❌ Canvas/Audio/WebGL fingerprinting (browser-only)
- ❌ Memory fingerprinting (Discord can't monitor this)
- ❌ Token "heat" tracking (already have risk scoring)
- ❌ Excessive API call diversity

### Environment Variables (Minimum Required)
```
JWT_SECRET_KEY=your-secret-key
TOKEN_ENCRYPTION_KEY=your-encryption-key
SELFBOT_WARNING_ACCEPTED=true  # Must be true for self-bot mode
```

### Key Design Principles
1. **Safety First** - Rate limits and breaks are more important than exotic features
2. **Pragmatic Approach** - Focus on real detection vectors, not theoretical ones
3. **Minimize Footprint** - Don't make unnecessary API calls
4. **Fallback Mechanisms** - Always have a plan B when anti-detection fails

### Current Anti-Detection Rating: 8/10
- The missing 2 points are inherent to self-bots, not fixable with more features
- Adding more complexity would increase failure points without meaningful benefit