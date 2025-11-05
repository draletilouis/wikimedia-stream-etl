# PostgreSQL Storage Layer

This directory contains the PostgreSQL database configuration for storing aggregated streaming metrics.

## Database Schema

### Tables

1. **user_edit_counts** - Stores edit counts per user per time window
   - `window_start`: Start of the time window
   - `window_end`: End of the time window
   - `user_name`: Wikipedia username
   - `edit_count`: Number of edits in the window
   - Primary key: `(window_start, user_name)`

2. **namespace_edit_counts** - Stores edit counts by namespace (future use)
   - Similar structure for namespace-level aggregations

3. **top_pages** - Most edited pages per time window (future use)
   - Tracks which pages receive the most edits

### Views

- `recent_user_activity`: Last 24 hours of user activity
- `top_contributors_hourly`: Top 50 contributors in the last hour

## Connection Details

- **Host**: localhost (or `postgres` from within Docker network)
- **Port**: 5432
- **Database**: wiki_streaming
- **User**: wiki_user
- **Password**: wiki_password

## Testing Queries

Connect to PostgreSQL:
```bash
docker exec -it postgres psql -U wiki_user -d wiki_streaming
```

View recent data:
```sql
-- See latest aggregations
SELECT * FROM user_edit_counts ORDER BY window_start DESC LIMIT 20;

-- Top contributors in last hour
SELECT * FROM top_contributors_hourly;

-- Total edits per minute over last hour
SELECT
    window_start,
    SUM(edit_count) as total_edits
FROM user_edit_counts
WHERE window_start >= NOW() - INTERVAL '1 hour'
GROUP BY window_start
ORDER BY window_start DESC;
```

## Data Retention

By default, all data is retained. For production, consider adding a retention policy:

```sql
-- Delete data older than 30 days
DELETE FROM user_edit_counts WHERE window_start < NOW() - INTERVAL '30 days';
```
