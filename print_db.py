import os
import datetime
import sqlite3
from zoneinfo import ZoneInfo

def format_time(timestamp):
    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    local_dt = dt.astimezone(ZoneInfo("Europe/Rome"))
    return local_dt.strftime('%Y-%m-%d %H:%M:%S %z')


def main():
    db_path = os.path.join(os.path.expanduser('~'), 'Documents/aranet4.db')
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

    for row in rows:
        row = list(row)
        row[1] = format_time(row[1])
        print(' | '.join(str(value) for value in row))

    print(f"Number of measurements: {len(rows)}")

    con.close()


if __name__ == "__main__":
    main()


