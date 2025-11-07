"""
Wikimedia Streaming Analytics Dashboard

Real-time visualization of Wikipedia edit activity.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import psycopg2
from sqlalchemy import create_engine
import os
import sys
from pathlib import Path

# Add parent directory to path for config loader
sys.path.insert(0, str(Path(__file__).parent.parent))
from common.config_loader import load_config

# Page configuration
st.set_page_config(
    page_title="Wikipedia Edit Analytics",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load configuration
@st.cache_resource
def get_config():
    """Load application configuration."""
    return load_config()

config = get_config()

# Database connection
@st.cache_resource
def get_db_connection():
    """Create database connection using config."""
    postgres_host = config.get('postgres.host', 'localhost')
    postgres_port = config.get('postgres.port', 5433)
    postgres_db = config.get('postgres.database', 'wiki_streaming')
    postgres_user = config.get('postgres.user', 'wiki_user')
    postgres_password = config.get('postgres.password', 'wiki_password')

    # For dashboard running outside Docker, use localhost:5433
    # For dashboard running inside Docker, use postgres:5432
    if os.getenv('DOCKER_ENV'):
        postgres_host = 'postgres'
        postgres_port = 5432

    connection_string = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'
    return create_engine(connection_string)

engine = get_db_connection()

# Data fetching functions
def fetch_user_edit_counts(minutes=60):
    """Fetch recent user edit counts."""
    query = f"""
    SELECT
        window_start,
        window_end,
        user_name,
        edit_count,
        created_at
    FROM user_edit_counts
    WHERE window_start >= NOW() - INTERVAL '{minutes} minutes'
    ORDER BY window_start DESC, edit_count DESC
    """
    return pd.read_sql(query, engine)

def fetch_top_users(limit=20, minutes=60):
    """Fetch top editors in the last N minutes."""
    query = f"""
    SELECT
        user_name,
        SUM(edit_count) as total_edits
    FROM user_edit_counts
    WHERE window_start >= NOW() - INTERVAL '{minutes} minutes'
    GROUP BY user_name
    ORDER BY total_edits DESC
    LIMIT {limit}
    """
    return pd.read_sql(query, engine)

def fetch_edit_timeline(minutes=60):
    """Fetch edit counts over time."""
    query = f"""
    SELECT
        window_start,
        SUM(edit_count) as total_edits
    FROM user_edit_counts
    WHERE window_start >= NOW() - INTERVAL '{minutes} minutes'
    GROUP BY window_start
    ORDER BY window_start ASC
    """
    return pd.read_sql(query, engine)

def fetch_statistics():
    """Fetch overall statistics."""
    query = """
    SELECT
        COUNT(DISTINCT user_name) as unique_users,
        SUM(edit_count) as total_edits,
        AVG(edit_count) as avg_edits_per_window,
        MAX(edit_count) as max_edits_single_window
    FROM user_edit_counts
    WHERE window_start >= NOW() - INTERVAL '1 hour'
    """
    return pd.read_sql(query, engine)

def fetch_recent_windows():
    """Fetch the most recent time windows with data."""
    query = """
    SELECT DISTINCT window_start, window_end
    FROM user_edit_counts
    ORDER BY window_start DESC
    LIMIT 10
    """
    return pd.read_sql(query, engine)

# Dashboard header
st.title("Wikipedia Edit Analytics Dashboard")
st.markdown("Real-time analysis of Wikipedia edit activity")

# Sidebar controls
st.sidebar.header("Settings")
time_window = st.sidebar.selectbox(
    "Time Window",
    options=[15, 30, 60, 120, 240],
    index=2,
    format_func=lambda x: f"Last {x} minutes"
)

top_n = st.sidebar.slider(
    "Top N Users",
    min_value=5,
    max_value=50,
    value=20,
    step=5
)

auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=True)

if st.sidebar.button("Refresh Now"):
    st.rerun()

# Main dashboard
try:
    # Fetch data
    with st.spinner("Loading data..."):
        stats = fetch_statistics()
        top_users = fetch_top_users(limit=top_n, minutes=time_window)
        timeline = fetch_edit_timeline(minutes=time_window)
        recent_edits = fetch_user_edit_counts(minutes=time_window)
        recent_windows = fetch_recent_windows()

    # Check if we have data
    if stats.empty or stats['total_edits'].iloc[0] is None:
        st.warning("No data available yet. Waiting for the streaming pipeline to process events...")
        st.info("The pipeline needs a few minutes to start collecting data. Please check back shortly.")
        st.stop()

    # Key metrics
    st.header("Key Metrics (Last Hour)")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Edits",
            f"{int(stats['total_edits'].iloc[0]):,}",
            help="Total number of edits in the last hour"
        )

    with col2:
        st.metric(
            "Unique Users",
            f"{int(stats['unique_users'].iloc[0]):,}",
            help="Number of unique editors"
        )

    with col3:
        st.metric(
            "Avg Edits/Window",
            f"{stats['avg_edits_per_window'].iloc[0]:.1f}",
            help="Average edits per 1-minute window"
        )

    with col4:
        st.metric(
            "Peak Edits",
            f"{int(stats['max_edits_single_window'].iloc[0]):,}",
            help="Maximum edits by a single user in one window"
        )

    # Timeline chart
    st.header(f"Edit Activity Timeline (Last {time_window} minutes)")

    if not timeline.empty:
        fig_timeline = px.line(
            timeline,
            x='window_start',
            y='total_edits',
            title='Total Edits Over Time',
            labels={'window_start': 'Time', 'total_edits': 'Number of Edits'}
        )
        fig_timeline.update_traces(line_color='#1f77b4', line_width=3)
        fig_timeline.update_layout(
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.info(f"No data available for the last {time_window} minutes")

    # Top users
    col1, col2 = st.columns(2)

    with col1:
        st.header(f"Top {top_n} Editors")

        if not top_users.empty:
            fig_top = px.bar(
                top_users,
                x='total_edits',
                y='user_name',
                orientation='h',
                title=f'Most Active Users (Last {time_window} min)',
                labels={'total_edits': 'Total Edits', 'user_name': 'User'},
                color='total_edits',
                color_continuous_scale='Blues'
            )
            fig_top.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                height=600,
                showlegend=False
            )
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.info("No user data available")

    with col2:
        st.header("Recent Activity Windows")

        if not recent_windows.empty:
            st.dataframe(
                recent_windows,
                column_config={
                    "window_start": st.column_config.DatetimeColumn(
                        "Window Start",
                        format="DD/MM/YY HH:mm:ss"
                    ),
                    "window_end": st.column_config.DatetimeColumn(
                        "Window End",
                        format="DD/MM/YY HH:mm:ss"
                    )
                },
                hide_index=True,
                use_container_width=True,
                height=250
            )

        st.header("Recent High-Volume Editors")

        if not recent_edits.empty:
            # Show top 10 from recent edits
            top_recent = recent_edits.nlargest(10, 'edit_count')[['user_name', 'edit_count', 'window_start']]
            st.dataframe(
                top_recent,
                column_config={
                    "user_name": "User",
                    "edit_count": st.column_config.NumberColumn(
                        "Edits",
                        format="%d"
                    ),
                    "window_start": st.column_config.DatetimeColumn(
                        "Time",
                        format="HH:mm:ss"
                    )
                },
                hide_index=True,
                use_container_width=True,
                height=350
            )
        else:
            st.info("No recent activity data")

    # Detailed data table
    with st.expander("View Raw Data"):
        st.subheader(f"All Edits (Last {time_window} minutes)")

        if not recent_edits.empty:
            st.dataframe(
                recent_edits,
                column_config={
                    "window_start": st.column_config.DatetimeColumn(
                        "Window Start",
                        format="DD/MM/YY HH:mm:ss"
                    ),
                    "window_end": st.column_config.DatetimeColumn(
                        "Window End",
                        format="DD/MM/YY HH:mm:ss"
                    ),
                    "user_name": "User",
                    "edit_count": st.column_config.NumberColumn(
                        "Edit Count",
                        format="%d"
                    ),
                    "created_at": st.column_config.DatetimeColumn(
                        "Recorded At",
                        format="DD/MM/YY HH:mm:ss"
                    )
                },
                hide_index=True,
                use_container_width=True
            )

            # Download button
            csv = recent_edits.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name=f"wiki_edits_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No data available")

    # Footer with last update time
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Data refreshed every 30 seconds")

except Exception as e:
    st.error(f"Error loading dashboard: {str(e)}")
    st.exception(e)
    st.info("Make sure the streaming pipeline is running and PostgreSQL is accessible.")

# Auto-refresh at the end, after all content is displayed
if auto_refresh:
    time.sleep(30)
    st.rerun()
