# aranet4-archiver

I built this to have the full history of measurements from an aranet4 CO2 sensor and be able to quickly plot them.

Features:
- Automatically fetch measurements with a LaunchAgent and store into a local sqlite3 db by running `fetch.py`
- Plot history with `plot.db`
- Quickly print measurements with `print.py`

This has been built upon [Aranet4-Python](https://github.com/Anrijs/Aranet4-Python). If you are new to aranet4 scripting, first have a look at that repo before using this one.

## Quickstart

### Install

- With uv: `pyproject.toml` is ready for [uv](https://docs.astral.sh/uv/) (recommended: no need to handle environments with uv). Nothing to do.
- Without uv: install with `pip install .`

### How to run

**To fetch measurements**

- Setup sensor name and MAC address in `.env` - other scripts should have good defaults.
    - Note: you can find the MAC address with `aranetctl --scan` from [Aranet4-Python](https://github.com/Anrijs/Aranet4-Python)
- Use `fetch.py` to fetch the data from the aranet4 device and update a local sqlite db (default is `~/Documents/aranet4.db`)

**To see fetched measurements**

- Use `plot.py` to plot measurements. Defaults to CO2 of last 3 days, run with `--help` to see all options.
- Use `print.py` to quickly print the 10 most recent measurements. Can print oldest with `--oldest` or more measurements with `--n`

## How to run as a background job

You probably want to run this periodically to not lose oldest measurements.

On MacOS I prepared a LaunchAgent for MacOS that runs automatically every 3 hours:
- Setup absolute paths in `com.diegobit.aranet4-fetch.plist`
- Copy into LaunchAgents dir: `cp com.diegobit.aranet4-fetch.plist ~Library/LaunchAgents/`
- Run `launchctl load ~/Library/LaunchAgents/com.diegobit.aranet4-fetch.plist`

NOTE: If not using uv, edit `aranet4-fetch.sh` to run python however you prefer.

