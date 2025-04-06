# aranet4-graphs

## Quickstart

### Install

- With uv: `pyproject.toml` is ready for [uv](https://docs.astral.sh/uv/) (recommended: no need to handle environments with uv). Nothing to do.
- Without uv: install with `pip install .`

### How to run

**To fetch measurements**

- Setup sensor name and MAC address in `.env`, then other scripts have good defaults.
- Use `fetch.py` to fetch the data from the aranet4 device and update a local sqlite db `~/Documents/aranet4.db`

**To see fetched measurements**

- Use `plot.py` to plot measurements. Defaults to CO2, run with `--help to see all options`
- Use `tail.py` or `head.py` to see latest or oldest measurements.

## How to run as a background job

You probably want to run this periodically to not lose oldest measurements.

On MacOS I prepared a LaunchAgent for MacOS that runs automatically every 3 hours:
- Setup absolute paths in `com.diegobit.aranet4-fetch.plist`
- Copy into LaunchAgents dir: `cp com.diegobit.aranet4-fetch.plist ~Library/LaunchAgents/`
- Run `launchctl load ~/Library/LaunchAgents/com.diegobit.aranet4-fetch.plist`

NOTE: If not using uv, edit `aranet4-fetch.sh` to run python however you prefer.

