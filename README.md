# aranet4-graphs

## Quickstart

To Fetch measurements:

- Setup sensor name and MAC address in `.env`
- Run `uv run fetch.py` to fetch the data from the aranet4 device, then update a local sqlite db `~/Documents/aranet4.db`

To see fetched measurements:

- Run `uv run tail.py` or `head.py` to see latest or first measurements.
- Run `uv run plot.py` to plot measurements.

NOTE: If you don't use uv, install requirements with `pip install .`.

## How to run as a background job

You probably want to run this periodically to not lose oldest measurements.

On MacOS, copy `com.diegobit.aranet4-fetch.plist` into `~Library/LaunchAgents/`.

