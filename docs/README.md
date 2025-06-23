# Discord Self-Bot Scraper Documentation

⚠️ **CRITICAL WARNING** ⚠️

Using self-bots violates Discord's Terms of Service and can result in permanent account termination. This implementation is provided for educational and research purposes only. By using this software, you acknowledge and accept all risks.

## Documentation Contents

- [User Guide](user-guide.md) - Step-by-step instructions for setup and usage
- [Safety Guidelines](safety-guidelines.md) - Best practices for avoiding detection
- [API Reference](api-reference.md) - Complete API endpoint documentation
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [Legal Disclaimer](legal-disclaimer.md) - Legal warnings and ToS implications

## Quick Start

1. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   docker-compose up -d
   ```

2. **Run Database Migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

3. **Access the Application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs

## Key Features

- **Encrypted Token Storage**: User tokens are encrypted at rest using military-grade encryption
- **Anti-Detection Measures**: Human-like delays, rate limiting, and behavior patterns
- **Circuit Breaker Pattern**: Automatic failure handling and recovery
- **Risk Monitoring**: Real-time risk assessment and adaptive behavior
- **Safety Controls**: Multiple layers of safety checks and warnings

## Architecture Overview

```
Frontend (React) → Backend API (FastAPI) → Self-Bot Worker → Discord API
                          ↓
                   Token Manager (Encrypted Storage)
                          ↓
                   Safety Manager → Risk Monitor
```

## Important Considerations

1. **Use Test Accounts Only**: Never use your main Discord account
2. **Monitor Risk Levels**: The system includes risk monitoring - heed the warnings
3. **Respect Rate Limits**: Conservative rate limits are enforced for safety
4. **Regular Breaks**: The system automatically takes breaks to appear human-like
5. **Session Limits**: Maximum 2-hour sessions with mandatory breaks

## Support

For issues and questions:
- GitHub Issues: [Report bugs or request features]
- Security Issues: Please report security vulnerabilities privately

Remember: This tool is for educational purposes only. Always respect Discord's Terms of Service and the privacy of other users.