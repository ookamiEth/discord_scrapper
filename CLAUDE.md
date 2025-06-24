# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack Discord scraper application with self-bot capabilities. It consists of:
- **Backend**: FastAPI with PostgreSQL database and Redis queue
- **Frontend**: React + TypeScript dashboard for managing scraping jobs
- **Worker**: Background job processor for Discord scraping
- **Self-bot**: Advanced anti-detection Discord client implementation

## Common Commands

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
│   │   ├── pages/           # Page components
│   │   ├── services/        # API client services
│   │   └── store/           # Redux store
│   └── package.json
├── scripts/                   # Utility scripts
│   └── clean_start.sh        # Database reset and startup script
├── exports/                   # Export directory for scraped data
├── docker-compose.yml         # Docker services configuration
├── .env.example              # Environment variables template
└── CLAUDE.md                 # This file
```

## Important Notes

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