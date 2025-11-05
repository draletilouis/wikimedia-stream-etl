-- Initialize wiki_streaming database

-- Table for storing aggregated edit counts per user per minute
CREATE TABLE IF NOT EXISTS user_edit_counts (
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    user_name VARCHAR(255) NOT NULL,
    edit_count BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (window_start, user_name)
);

-- Create index for time-based queries (dashboard will query by time range)
CREATE INDEX idx_user_edits_window ON user_edit_counts(window_start DESC);
CREATE INDEX idx_user_edits_user ON user_edit_counts(user_name);

-- Table for storing aggregated edit counts by namespace per minute
CREATE TABLE IF NOT EXISTS namespace_edit_counts (
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    namespace BIGINT NOT NULL,
    edit_count BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (window_start, namespace)
);

CREATE INDEX idx_namespace_edits_window ON namespace_edit_counts(window_start DESC);

-- Table for storing top edited pages per window
CREATE TABLE IF NOT EXISTS top_pages (
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    page_title VARCHAR(500) NOT NULL,
    edit_count BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (window_start, page_title)
);

CREATE INDEX idx_top_pages_window ON top_pages(window_start DESC);
CREATE INDEX idx_top_pages_count ON top_pages(edit_count DESC);

-- View for recent activity (last 24 hours)
CREATE OR REPLACE VIEW recent_user_activity AS
SELECT
    window_start,
    user_name,
    edit_count
FROM user_edit_counts
WHERE window_start >= NOW() - INTERVAL '24 hours'
ORDER BY window_start DESC;

-- View for top contributors (last hour)
CREATE OR REPLACE VIEW top_contributors_hourly AS
SELECT
    user_name,
    SUM(edit_count) as total_edits
FROM user_edit_counts
WHERE window_start >= NOW() - INTERVAL '1 hour'
GROUP BY user_name
ORDER BY total_edits DESC
LIMIT 50;

COMMENT ON TABLE user_edit_counts IS 'Aggregated edit counts per user per time window';
COMMENT ON TABLE namespace_edit_counts IS 'Aggregated edit counts per namespace per time window';
COMMENT ON TABLE top_pages IS 'Most edited pages per time window';
