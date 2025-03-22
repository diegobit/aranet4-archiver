from datetime import datetime, timezone
import os
import sqlite3
from zoneinfo import ZoneInfo

import aranet4


def main():
    num_retries = 10
    device_name = "camera"
    device_mac = '11A2FFE6-EC4D-D53D-9695-EA19DCE33F63'

    db_path = os.path.join(os.path.expanduser('~'), 'Documents/aranet4.db')
    entry_filter = {}

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS measurements(
            device TEXT,
            timestamp INTEGER,
            temperature REAL,
            humidity INTEGER,
            pressure REAL,
            CO2 INTEGER,
            PRIMARY KEY(device, timestamp)
        )
    '''
    )
    con.commit()

    res = cur.execute('''SELECT timestamp FROM measurements WHERE device = ?
                         ORDER BY timestamp DESC LIMIT 1''', (device_name,))
    row = res.fetchone()
    if row is not None:
        entry_filter['start'] = datetime.fromtimestamp(row[0], tz=timezone.utc).astimezone(ZoneInfo("Europe/Rome"))
    history = None
    for attempt in range(num_retries):
        entry_filter['end'] = datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Rome"))
        try:
            history = aranet4.client.get_all_records(device_mac, entry_filter)
            break
        except Exception as e:
            print(f"Failed attempt {attempt+1}, retrying. Error: {e}")

    data = []
    if history is not None:
        for entry in history.value:
            if entry.co2 < 0:
                continue

            data.append((
                device_name,
                entry.date.timestamp(),
                entry.temperature,
                entry.humidity,
                entry.pressure,
                entry.co2
            ))

        print(f"Fetched {len(data)} measurements in range:")
        print(f"  start: {entry_filter['start'].isoformat()}")
        print(f"  end:   {entry_filter['end'].isoformat()}")
        cur.executemany(
            'INSERT OR IGNORE INTO measurements VALUES(?, ?, ?, ?, ?, ?)', data
        )
        con.commit()
    else:
        print('Quitting, failed to fetch measurements.')

    con.close()


if __name__ == "__main__":
    main()

