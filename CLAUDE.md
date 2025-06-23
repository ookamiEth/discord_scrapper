# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This directory contains the Discord API documentation repository (discord-api-docs), which is the official documentation for Discord's API. Despite the directory name "discord_scrapper", there is currently no Discord scraper implementation present.

## Common Commands

### Documentation Development

```bash
# Install dependencies (requires Node.js >= 20.11.0)
npm install

# Build TypeScript files in tools directory
npm run build

# Lint TypeScript files
npm run lint
npm run lint:fix

# Test documentation
npm run test:links    # Check for broken links in documentation
npm run test:build    # Verify MDX/MD files compile correctly
npm run test:tables   # Check markdown table formatting

# Fix markdown table formatting
npm run fix:tables

# Generate social SDK documentation references
npm run decorate:docs
```

## Repository Structure

- `/discord-api-docs/docs/` - Main documentation content in MDX/Markdown format
- `/discord-api-docs/tools/` - TypeScript utilities for documentation validation
  - `checkBuild.ts` - Validates MDX/MD compilation
  - `checkLinks.ts` - Validates documentation links
- `/discord-api-docs/resources/` - Documentation assets (images, SVGs)
- `/discord-api-docs/static/images/` - Static images for documentation

## Important Notes

1. This is a documentation-only repository for Discord's API
2. To create an actual Discord scraper, you would need to:
   - Create a new Python/JavaScript project
   - Use discord.py or discord.js libraries
   - Follow Discord's Terms of Service and rate limits
   - Implement proper authentication using bot tokens

3. When modifying documentation:
   - Follow the contribution guidelines in CONTRIBUTING.md
   - Ensure all links are valid using `npm run test:links`
   - Format tables properly using `npm run fix:tables`
   - Test MDX compilation with `npm run test:build`