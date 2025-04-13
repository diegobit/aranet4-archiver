import os
import sqlite3
import logging
import traceback
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import fire
import tzlocal
import aranet4
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='[%(asctime)s] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)


class Aranet4Archiver:
    """Manager for Aranet4 device data operations: fetch, plot, and print."""

    def __init__(self):
        self.sensor_plot_config = {
            "temperature": {"color": "red", "unit": "°C"},
            "humidity": {"color": "blue", "unit": "%"},
            "pressure": {"color": "green", "unit": "hPa"},
            "CO2": {"color": "purple", "unit": "ppm"},
        }
        self.device_name = os.getenv("DEVICE_NAME")
        self.device_mac = os.getenv("DEVICE_MAC")
        try:
            self.local_timezone = tzlocal.get_localzone_name()
        except Exception:
            self.local_timezone = "UTC"

        self.db_path = os.path.expanduser(os.getenv("DB_PATH", "~/Documents/aranet4.db"))
        if not os.path.exists(self.db_path):
            print(f"Error: Database file not found at {self.db_path}")
        self._init_database()

    def _init_database(self):
        """Initialize the database if it doesn't already exist."""
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS measurements(
                    device TEXT,
                    timestamp INTEGER,
                    temperature REAL,
                    humidity INTEGER,
                    pressure REAL,
                    CO2 INTEGER,
                    PRIMARY KEY(device, timestamp)
                )
            """)
            con.commit()
            con.close()
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")


    def fetch(self, num_retries: int = 3):
        """
        Fetch new data from Aranet4 device and store in the database.

        Args:
            num_retries: Number of retry attempts if fetching fails.
        """
        if not self.device_name or self.device_name == "XXX":
            print("device_name not set. Have you configured .env ?")
            return

        if not self.device_mac or self.device_mac == "XXX":
            print("device_mac not set. Have you configured .env ?")
            return

        logging.info(f"Start fetching from {self.device_name} into db at {self.db_path}")

        entry_filter = {}

        con = sqlite3.connect(self.db_path)
        cur = con.cursor()

        res = cur.execute(
            """
            SELECT timestamp
            FROM measurements
            WHERE device = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (self.device_name,),
        )
        row = res.fetchone()
        if row is not None:
            entry_filter["start"] = datetime.fromtimestamp(row[0], tz=timezone.utc).astimezone(
                ZoneInfo(self.local_timezone)
            )

        history = None
        for attempt in range(num_retries):
            entry_filter["end"] = datetime.now(timezone.utc).astimezone(ZoneInfo(self.local_timezone))
            try:
                history = aranet4.client.get_all_records(self.device_mac, entry_filter)
                break
            except Exception as e:
                logging.warning(f"Failed attempt {attempt+1}, retrying. Error: {e}")

        data = []
        if history is not None:
            for entry in history.value:
                if entry.co2 < 0:
                    continue

                data.append((
                    self.device_name,
                    entry.date.timestamp(),
                    entry.temperature,
                    entry.humidity,
                    entry.pressure,
                    entry.co2
                ))

            cur.executemany(
                'INSERT OR IGNORE INTO measurements VALUES(?, ?, ?, ?, ?, ?)', data
            )
            con.commit()

            logging.info(f"Fetched {len(data)} measurements in range: ({entry_filter.get('start', 'beginning').isoformat() if 'start' in entry_filter else 'beginning'}, {entry_filter['end'].isoformat()})")

        else:
            logging.warning('Quitting, failed to fetch measurements.')

        con.close()


    def plot(self,
             sensors: str = "CO2",
             days: int = 3,
             start_date: str = "",
             end_date: str = "",
             max_measures: int = 2000):
        """
        Plots sensor data from the Aranet4 SQLite database.

        Args:
            sensors: Comma-separated list of sensors to plot (e.g., "temperature,CO2"). Valid sensors: temperature, humidity, pressure, CO2.
            days: Plot last n days. Defaults to 3. Overridden by `start_date`.
            start_date: Start date for the data range (YYYY-MM-DD). Overrides `days`.
            end_date: End date for the data range (YYYY-MM-DD). Defaults to now.
            max_measures: limit number of points to plot. Will sparse the data if above this value.
        """
        if start_date:
            print("Passed start_date. `days` argument won't be used.")

        if isinstance(sensors, tuple):
            sensor_list = sensors
        else:
            sensor_list = [sensors]

        # --- 1. Parse and validate sensors ---
        requested_sensors = [s.strip().lower().replace('co2', 'CO2') for s in sensor_list]
        valid_sensors = list(self.sensor_plot_config.keys())
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
                    end_dt_naive = datetime.strptime(end_date, "%Y-%m-%d")
                    # Assume user provides date in local time, convert to UTC for query end
                    end_dt_aware = pd.Timestamp(end_dt_naive).tz_localize(self.local_timezone).tz_convert("UTC")
                    query_end_utc = (end_dt_aware.normalize() + timedelta(days=1)).to_pydatetime()  # End of day
                except ValueError:
                    print(f"Error: Invalid end_date format '{end_date}'. Use YYYY-MM-DD.")
                    return

            if not start_date:
                query_start_utc = query_end_utc - timedelta(days=days + 1)
            else:
                try:
                    # User specified start_date, use start of that day in UTC
                    start_dt_naive = datetime.strptime(start_date, "%Y-%m-%d")
                    # Assume user provides date in local time, convert to UTC for query start
                    start_dt_aware = pd.Timestamp(start_dt_naive).tz_localize(self.local_timezone).tz_convert("UTC")
                    query_start_utc = (start_dt_aware.normalize() + timedelta(days=1)).to_pydatetime()  # Start of day
                except ValueError:
                    print(f"Error: Invalid start_date format '{start_date}'. Use YYYY-MM-DD.")
                    return

            # --- 3. Fetch data ---
            select_cols = ["timestamp"] + selected_sensors
            query = f"""
                SELECT {", ".join(select_cols)}
                FROM measurements
                WHERE timestamp >= ? AND timestamp < ?
                ORDER BY timestamp;
                """
            params = [int(query_start_utc.timestamp()), int(query_end_utc.timestamp())]

            print(
                f"Querying data between {query_start_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC and {query_end_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC..."
            )

            # Read data using pandas, ensuring timestamp parsing
            con = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query, con, params=params, parse_dates=["timestamp"])

            while len(df) > max_measures:
                print(f"Too many measures: {len(df)}. Discarding one every two. --max-measures={max_measures}")
                df = df.iloc[::2]
            print(f"Plotting {len(df)} measures.")

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
        if df["timestamp"].dt.tz is None:
            print("Warning: Timestamp loaded as naive. Assuming UTC from database.")
            df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")

        # Convert timestamp to the desired timezone for plotting
        try:
            df["timestamp"] = df["timestamp"].dt.tz_convert(self.local_timezone)
            display_tz_name = self.local_timezone
        except Exception as tz_error:
            print(f"Warning: Could not convert timezone to '{self.local_timezone}': {tz_error}. Plotting in UTC.")
            display_tz_name = "UTC"  # Keep it in UTC if conversion fails

        # --- 5. Plotting ---
        num_sensors = len(selected_sensors)
        fig, axs = plt.subplots(
            num_sensors, 1, figsize=(12, 4 * num_sensors), sharex=True, squeeze=False
        )  # squeeze=False ensures axs is always 2D

        print(f"Plotting sensors: {', '.join(selected_sensors)}")

        for i, sensor in enumerate(selected_sensors):
            config = self.sensor_plot_config[sensor]
            ax = axs[i, 0]  # Access axis using [row, col]
            ax.plot(
                df["timestamp"],
                df[sensor],
                marker="none",
                linestyle="-",
                color=config["color"],
                markersize=4,
                label=sensor.capitalize(),
                alpha=1,
            )
            ax.set_ylabel(f"{sensor.capitalize()} ({config['unit']})")
            ax.grid(True)
            ax.legend(loc="upper left")

        # Common formatting for the bottom plot
        axs[-1, 0].set_xlabel(f"Timestamp ({display_tz_name})")
        fig.autofmt_xdate()  # Auto-formats the x-axis labels
        axs[-1, 0].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M", tz=df["timestamp"].dt.tz))

        # Overall title
        start_display = df["timestamp"].min().strftime("%Y-%m-%d")
        end_display = df["timestamp"].max().strftime("%Y-%m-%d")
        fig.suptitle(
            f"Sensor Readings from {os.path.basename(self.db_path)}\n({start_display} to {end_display})", fontsize=14
        )

        # Improve layout
        plt.tight_layout(rect=(0, 0.03, 1, 0.96))  # Adjust layout to make room for suptitle

        # Show the plot
        plt.show()


    def print(self, oldest: bool = False, n: int = 10):
        """
        Print the latest (or oldest) records from the database.

        Args:
            oldest: If True, print the oldest records instead of the most recent.
            n: Number of records to print.
        """
        if not self.local_timezone:
            print("local_timezone not set. Have you configured .env ?")
            return

        con = sqlite3.connect(self.db_path)
        cur = con.cursor()
        order = "ASC" if oldest else "DESC"
        _ = cur.execute(
            f"""
            SELECT device, timestamp, temperature, humidity, pressure, CO2
            FROM measurements
            ORDER BY timestamp {order}
            LIMIT {n}
            """
        )

        column_names = [description[0] for description in cur.description]
        print(' | '.join(column_names))
        print('-' * (sum(len(name) for name in column_names) + 3 * (len(column_names) - 1)))

        rows = cur.fetchall()

        for row in rows:
            row = list(row)
            dt = datetime.fromtimestamp(row[1], tz=timezone.utc)
            local_dt = dt.astimezone(ZoneInfo(self.local_timezone))
            row[1] = local_dt.strftime('%Y-%m-%d %H:%M:%S %z')
            print(" | ".join(str(value) for value in row))

        con.close()


if __name__ == "__main__":
    fire.Fire(Aranet4Archiver)
