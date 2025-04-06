from datetime import datetime, timezone
import os
from zoneinfo import ZoneInfo
import logging

from dotenv import load_dotenv
import sqlite3
import aranet4
import fire

load_dotenv()

logging.basicConfig(
    format='[%(asctime)s] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main(num_retries: int = 3):
    db_path = os.path.expanduser(os.getenv("DB_PATH", "~/Documents/araner4.db"))
    device_name = os.getenv('DEVICE_NAME')
    device_mac = os.getenv('DEVICE_MAC')

    logging.info(f"Start fetching from {device_name} into db at {db_path}")

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
            logging.warning(f"Failed attempt {attempt+1}, retrying. Error: {e}")

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

        logging.info(f"Fetched {len(data)} measurements in range: ({entry_filter['start'].isoformat()}, {entry_filter['end'].isoformat()})")
        cur.executemany(
            'INSERT OR IGNORE INTO measurements VALUES(?, ?, ?, ?, ?, ?)', data
        )
        con.commit()
    else:
        logging.warning('Quitting, failed to fetch measurements.')

    con.close()


if __name__ == "__main__":
    fire.Fire(main)

