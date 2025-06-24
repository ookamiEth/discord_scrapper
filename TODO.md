# Discord Scraper TODO List

This document tracks all TODO items, incomplete implementations, and technical debt in the Discord Scraper project.

## High Priority TODOs

### 1. Job Cancellation Implementation
**File:** `backend/routers/scraping.py:183`
**Issue:** Job cancellation only updates database status but doesn't actually cancel the running RQ worker job
**Solution:** Implement proper RQ job cancellation using `rq.cancel_job()` or similar mechanism

### 2. Discord API Integration for Update Checking
**File:** `backend/routers/scraping.py:209-210`
**Issue:** Currently uses time-based logic (24 hours) instead of checking Discord for actual new messages
**Solution:** 
- Implement Discord API call to fetch latest message ID
- Compare with stored `last_message_id`
- Only mark as needs_update if new messages exist

### 3. Server Data Persistence
**File:** `backend/routers/servers.py:64-65`
**Issue:** Manually added servers stored in temporary JSON file instead of database
**Solution:** 
- Create proper database table for servers
- Migrate existing JSON data to database
- Update CRUD operations

## Medium Priority TODOs

### 4. Dynamic Discord Build Number
**File:** `backend/discord_client.py:228-229`
**Issue:** Discord build number is hard-coded instead of dynamically fetched
**Solution:** 
- Fetch current build number from Discord or GitHub
- Cache with appropriate TTL
- Fall back to known good value if fetch fails

### 5. Progress Tracking Enhancement
**File:** `backend/routers/scraping.py:128`
**Issue:** Progress calculation is time-based estimate instead of actual progress
**Solution:** 
- Parse actual progress from worker updates
- Implement proper progress reporting from worker to API

### 6. Anti-Detection Bot Integration
**File:** `backend/worker.py:24`
**Issue:** Advanced anti-detection bot is commented out
**Solution:** 
- Complete anti-detection bot implementation
- Test thoroughly before enabling
- Add configuration toggle

### 7. Server ID Lookup for Unsynced Channels
**File:** `backend/routers/scraping.py:225`
**Issue:** Server ID set to 0 for unsynced channels
**Solution:** 
- Implement proper server ID lookup from channel ID
- Store channel-to-server mapping

## Low Priority TODOs

### 8. Rate Limiter Enhancement
**File:** `backend/http_client.py:240`
**Issue:** Simple token bucket implementation could be improved
**Solution:** 
- Implement more sophisticated rate limiting
- Add per-endpoint rate limits
- Better error handling and backoff

## Technical Debt

### Database Schema
- Discord IDs stored as integers in database but handled as strings in API
- Consider migration to store as strings or BIGINT

### Error Handling
- Many Discord API errors not specifically handled
- Add specific error types and recovery strategies

### Testing
- Limited test coverage for Discord API interactions
- Add integration tests with Discord API mocks

### Security
- Token storage could be enhanced with encryption
- Add token rotation capabilities

## Feature Enhancements

### Export Formats
- Currently only JSON export is fully implemented
- Add HTML, CSV, and TXT export implementations

### Webhook Support
- Add ability to post updates to webhooks
- Useful for automation and monitoring

### Bulk Operations
- Add bulk channel export
- Server-wide export capabilities

### Search and Filtering
- Add message search within exports
- Filter by user, date range, or content

## Documentation Needs

- API documentation (OpenAPI/Swagger)
- Deployment guide for production
- Configuration reference
- Troubleshooting guide

## Performance Optimizations

- Implement connection pooling for Discord API
- Add caching layer for frequently accessed data
- Optimize database queries with proper indexes
- Consider message batching for large exports

---

*Last Updated: 2025-06-24*
*Note: This list should be kept up to date as TODOs are completed or new ones are discovered.*