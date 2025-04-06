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


def main(n: int = 30):
    db_path = os.path.expanduser(os.getenv("DB_PATH", ""))
    local_timezone = os.getenv("LOCAL_TIMEZONE", "")

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    _ = cur.execute(
        '''
        SELECT device, timestamp, temperature, humidity, pressure, CO2 FROM measurements
        ORDER BY timestamp
        '''
    )

    column_names = [description[0] for description in cur.description]
    print(' | '.join(column_names))
    print('-' * (sum(len(name) for name in column_names) + 3 * (len(column_names) - 1)))

    rows = cur.fetchall()

    def print_row(row):
        row = list(row)
        row[1] = format_time(row[1], local_timezone)
        print(' | '.join(str(value) for value in row))

    for i, row in enumerate(rows):
        if i >= len(rows) - n:
            print_row(row)

    print(f"\nPrinted {n} of {len(rows)} measurements.")

    con.close()


if __name__ == "__main__":
    fire.Fire(main)

