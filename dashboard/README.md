# Wikipedia Edit Analytics Dashboard

Real-time visualization dashboard for Wikipedia edit activity using Streamlit.

## Features

### 📊 Key Metrics
- **Total Edits** - Total number of edits in the last hour
- **Unique Users** - Number of unique editors
- **Average Edits per Window** - Average edits per 1-minute window
- **Peak Edits** - Maximum edits by a single user in one window

### 📈 Visualizations
1. **Edit Activity Timeline** - Line chart showing edit volume over time
2. **Top Editors** - Horizontal bar chart of most active users
3. **Recent Activity Windows** - Table of latest processing windows
4. **High-Volume Editors** - Real-time list of users with most edits

### ⚙️ Interactive Controls
- **Time Window Selection** - View data from last 15, 30, 60, 120, or 240 minutes
- **Top N Users** - Adjust the number of top users displayed (5-50)
- **Auto-refresh** - Dashboard auto-updates every 30 seconds
- **Manual Refresh** - Force refresh at any time
- **CSV Export** - Download raw data for further analysis

## Running the Dashboard

### Option 1: With Docker (Recommended)

The dashboard is included in the main docker-compose setup:

```bash
cd docker
docker-compose up -d dashboard
```

Access the dashboard at: **http://localhost:8501**

### Option 2: Standalone (Local Development)

If you want to run the dashboard locally for development:

1. **Install dependencies:**
   ```bash
   cd dashboard
   pip install -r requirements.txt
   ```

2. **Ensure PostgreSQL is accessible:**
   - If running Docker pipeline: PostgreSQL is on `localhost:5433`
   - Update config if needed

3. **Run Streamlit:**
   ```bash
   streamlit run streamlit_app.py
   ```

4. **Open browser:**
   Navigate to http://localhost:8501

## Configuration

The dashboard uses the centralized configuration system from `config/conf.yaml`:

```yaml
postgres:
  host: "postgres"      # Or "localhost" for local development
  port: 5432            # Or 5433 for external access
  database: "wiki_streaming"
  user: "wiki_user"
  password: "${POSTGRES_PASSWORD}"
```

### Environment Variables

- `POSTGRES_HOST` - PostgreSQL hostname (default: from config)
- `POSTGRES_PORT` - PostgreSQL port (default: from config)
- `POSTGRES_PASSWORD` - Database password
- `DOCKER_ENV` - Set to 'true' when running in Docker

## Dashboard Architecture

```
PostgreSQL (aggregated data)
    ↓
SQLAlchemy Connection
    ↓
Pandas DataFrames
    ↓
Plotly Charts
    ↓
Streamlit UI
    ↓
Web Browser (port 8501)
```

## SQL Queries

The dashboard executes the following main queries:

1. **Overall Statistics:**
   ```sql
   SELECT COUNT(DISTINCT user_name), SUM(edit_count), AVG(edit_count)
   FROM user_edit_counts
   WHERE window_start >= NOW() - INTERVAL '1 hour'
   ```

2. **Top Users:**
   ```sql
   SELECT user_name, SUM(edit_count) as total_edits
   FROM user_edit_counts
   WHERE window_start >= NOW() - INTERVAL 'N minutes'
   GROUP BY user_name
   ORDER BY total_edits DESC
   LIMIT N
   ```

3. **Edit Timeline:**
   ```sql
   SELECT window_start, SUM(edit_count) as total_edits
   FROM user_edit_counts
   WHERE window_start >= NOW() - INTERVAL 'N minutes'
   GROUP BY window_start
   ORDER BY window_start ASC
   ```

## Performance Considerations

- **Auto-refresh**: Set to 30 seconds by default to balance freshness vs. database load
- **Caching**: Database connection is cached using `@st.cache_resource`
- **Query Optimization**: All queries use indexed columns (window_start)
- **Data Limits**: Top users limited to configurable N (default 20)

## Troubleshooting

### Dashboard shows "No data available"
- Ensure the streaming pipeline is running
- Check that Spark is processing events
- Verify PostgreSQL has data: `SELECT COUNT(*) FROM user_edit_counts;`
- Wait 2-3 minutes for initial data processing

### Cannot connect to database
- Check PostgreSQL is running: `docker ps`
- Verify connection settings in config/conf.yaml
- For local development, use port 5433
- For Docker deployment, use internal hostname 'postgres' and port 5432

### Dashboard is slow
- Reduce the time window (e.g., from 240 to 60 minutes)
- Reduce the number of top users displayed
- Check PostgreSQL performance
- Consider adding more indexes

### Port 8501 already in use
```bash
# Stop the conflicting service or change port in docker-compose.yml
ports:
  - "8502:8501"  # Map to different external port
```

## Customization

### Adding New Metrics

Edit `streamlit_app.py` and add new query functions:

```python
def fetch_custom_metric():
    query = """
    SELECT ... FROM user_edit_counts
    WHERE ...
    """
    return pd.read_sql(query, engine)
```

### Changing Refresh Interval

In `streamlit_app.py`, modify:

```python
if auto_refresh:
    time.sleep(30)  # Change to desired seconds
    st.rerun()
```

### Adding New Charts

Use Plotly Express for new visualizations:

```python
import plotly.express as px

fig = px.scatter(df, x='column1', y='column2', title='Custom Chart')
st.plotly_chart(fig, use_container_width=True)
```

## Future Enhancements

- [ ] Namespace-based filtering
- [ ] Bot vs human activity comparison
- [ ] Geographic distribution map
- [ ] Alert notifications for anomalies
- [ ] Historical trend analysis
- [ ] User activity heatmap
- [ ] Edit type breakdown (new/edit/revert)
- [ ] Customizable dashboard layouts
- [ ] Multiple page views
- [ ] User authentication

## Dependencies

- `streamlit` - Web application framework
- `pandas` - Data manipulation
- `plotly` - Interactive charts
- `psycopg2-binary` - PostgreSQL adapter
- `sqlalchemy` - Database ORM
- `python-dotenv` - Environment variable management

## Resources

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Python Documentation](https://plotly.com/python/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
