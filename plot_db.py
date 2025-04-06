import traceback
import fire
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sqlite3
import os
from datetime import datetime, timedelta, timezone


SENSOR_PLOT_CONFIG = {
    'temperature': {'color': 'red', 'unit': '°C'},
    'humidity': {'color': 'blue', 'unit': '%'},
    'pressure': {'color': 'green', 'unit': 'hPa'},
    'CO2': {'color': 'purple', 'unit': 'ppm'} # Use lowercase key consistent with parsing
}


def main(
    db_path: str = "~/Documents/aranet4.db",
    start_date: str = "",
    end_date: str = "",
    sensors: str = "CO2",
    plot_timezone: str = 'Europe/Rome'
):
    """
    Plots sensor data from an Aranet4 SQLite database.

    Args:
        db_path: Path to the SQLite database file.
        start_date: Start date for the data range (YYYY-MM-DD). Defaults to 7 days before the latest record.
        end_date: End date for the data range (YYYY-MM-DD). Defaults to the latest record.
        sensors: Comma-separated list of sensors to plot (e.g., "temperature,CO2").
                 Valid sensors: temperature, humidity, pressure, co2. Defaults to "CO2".
        plot_timezone: Timezone for displaying the timestamps on the plot (e.g., 'Europe/Rome', 'UTC').
    """
    db_path = os.path.expanduser(db_path)
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    # --- 1. Parse and validate sensors ---
    requested_sensors = [s.strip().lower().replace('co2', 'CO2') for s in sensors]
    valid_sensors = list(SENSOR_PLOT_CONFIG.keys())
    selected_sensors = []
    for sensor in requested_sensors:
        if sensor in valid_sensors:
            selected_sensors.append(sensor)
        else:
            print(f"Warning: Ignoring invalid sensor '{sensor}'. Valid options are: {', '.join(valid_sensors)}")

    if not selected_sensors:
        print(f"Error: No valid sensors selected. Please choose from: {', '.join(valid_sensors)}")
        return

    try:
        # --- 2. Date Range ---
        # Determine date range for query
        query_start_utc = None
        query_end_utc = None

        if not end_date:
            # Set the query end time to the end of the current day (start of the next day UTC)
            now_utc = datetime.now(timezone.utc)
            start_of_today_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            query_end_utc = start_of_today_utc + timedelta(days=1)
        else:
            try:
                end_dt_naive = datetime.strptime(end_date, '%Y-%m-%d')
                # Assume user provides date in local time, convert to UTC for query end
                end_dt_aware = pd.Timestamp(end_dt_naive).tz_localize(plot_timezone).tz_convert('UTC')
                query_end_utc = (end_dt_aware.normalize() + timedelta(days=1)).to_pydatetime() # End of day
            except ValueError:
                print(f"Error: Invalid end_date format '{end_date}'. Use YYYY-MM-DD.")
                return

        if not start_date:
             query_start_utc = (query_end_utc - timedelta(days=7+1)) # Start of day 30 days prior
        else:
            try:
               # User specified start_date, use start of that day in UTC
               start_dt_naive = datetime.strptime(start_date, '%Y-%m-%d')
               # Assume user provides date in local time, convert to UTC for query start
               start_dt_aware = pd.Timestamp(start_dt_naive).tz_localize(plot_timezone).tz_convert('UTC')
               query_start_utc = (start_dt_aware.normalize() + timedelta(days=1)).to_pydatetime() # Start of day
            except ValueError:
               print(f"Error: Invalid start_date format '{start_date}'. Use YYYY-MM-DD.")
               return

        # --- 3. Fetch data ---
        select_cols = ['timestamp'] + selected_sensors
        query = f"""
        SELECT {', '.join(select_cols)}
        FROM measurements
        WHERE timestamp >= ? AND timestamp < ?
        ORDER BY timestamp;
        """
        params = (int(query_start_utc.timestamp()), int(query_end_utc.timestamp()))

        print(f"Querying data between {query_start_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC and {query_end_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC...")

        # Read data using pandas, ensuring timestamp parsing
        con = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, con, params=params, parse_dates=['timestamp'])
        con.close()

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        print(traceback.format_exc())
        return
    except Exception as e:
        print(f"An error occurred during data loading: {e}")
        print(traceback.format_exc())
        return

    # --- 4. Data Processing ---
    if df.empty:
        print(f"No data found in the specified date range ({start_date or 'default'} to {end_date or 'default'}).")
        return

    # Ensure timestamp column is timezone-aware (pandas might make it naive from SQLite)
    if df['timestamp'].dt.tz is None:
        print("Warning: Timestamp loaded as naive. Assuming UTC from database.")
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')

    # Convert timestamp to the desired timezone for plotting
    try:
        df['timestamp'] = df['timestamp'].dt.tz_convert(plot_timezone)
        display_tz_name = plot_timezone
    except Exception as tz_error:
        print(f"Warning: Could not convert timezone to '{plot_timezone}': {tz_error}. Plotting in UTC.")
        display_tz_name = 'UTC' # Keep it in UTC if conversion fails

    # --- 5. Plotting ---
    num_sensors = len(selected_sensors)
    fig, axs = plt.subplots(num_sensors, 1, figsize=(12, 4 * num_sensors), sharex=True, squeeze=False) # squeeze=False ensures axs is always 2D

    print(f"Plotting sensors: {', '.join(selected_sensors)}")

    # Determine overall min/max timestamps for consistent x-axis limits if needed
    # plot_start_time = df['timestamp'].min()
    # plot_end_time = df['timestamp'].max()

    for i, sensor in enumerate(selected_sensors):
        config = SENSOR_PLOT_CONFIG[sensor]
        ax = axs[i, 0] # Access axis using [row, col]
        # Plot the line with full opacity
        # ax.plot(df['timestamp'], df[sensor], linestyle='-', color=config['color'], linewidth=1, label='_nolegend_')
        # Plot the markers with partial opacity
        ax.plot(df['timestamp'], df[sensor], marker='none', linestyle='-', color=config['color'], markersize=4, label=sensor.capitalize(), alpha=1)
        ax.set_ylabel(f"{sensor.capitalize()} ({config['unit']})")
        ax.grid(True)
        ax.legend(loc='upper left')
        # ax.set_xlim(plot_start_time, plot_end_time) # Optional: Uncomment for fixed x-limits across plots

    # Common formatting for the bottom plot
    axs[-1, 0].set_xlabel(f'Timestamp ({display_tz_name})')
    fig.autofmt_xdate() # Auto-formats the x-axis labels
    axs[-1, 0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M', tz=df['timestamp'].dt.tz))

    # Overall title
    start_display = df['timestamp'].min().strftime('%Y-%m-%d')
    end_display = df['timestamp'].max().strftime('%Y-%m-%d')
    fig.suptitle(f'Sensor Readings from {os.path.basename(db_path)}\n({start_display} to {end_display})', fontsize=14)

    # Improve layout
    plt.tight_layout(rect=[0, 0.03, 1, 0.96]) # Adjust layout to make room for suptitle

    # Show the plot
    plt.show()


if __name__ == '__main__':
    fire.Fire(main)
