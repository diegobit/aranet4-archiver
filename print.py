import datetime
import os
import sqlite3
from zoneinfo import ZoneInfo

import fire
from dotenv import load_dotenv

load_dotenv()


def format_time(timestamp, local_timezone):
    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    local_dt = dt.astimezone(ZoneInfo(local_timezone))
    return local_dt.strftime('%Y-%m-%d %H:%M:%S %z')


def main(oldest: bool = False, n: int = 10):
    db_path = os.path.expanduser(os.getenv("DB_PATH", ""))
    local_timezone = os.getenv("LOCAL_TIMEZONE", "")

    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    if not local_timezone:
        print("local_timezone not set. Have you configured .env ?")
        return

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    order = "ASC" if oldest else "DESC"
    _ = cur.execute(
        f"""
        SELECT device, timestamp, temperature, humidity, pressure, CO2 FROM measurements
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
        row[1] = format_time(row[1], local_timezone)
        print(' | '.join(str(value) for value in row))

    con.close()


if __name__ == "__main__":
    fire.Fire(main)

