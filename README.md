# aranet4-archiver

> [!TIP]
> For the MCP server version, see [aranet4-mcp-server](https://github.com/diegobit/aranet4-mcp-server)

A simple tool to fetch, store, and visualize historical data from an Aranet4 CO2 sensor. Built upon [Aranet4-Python](https://github.com/Anrijs/Aranet4-Python)

## Features:
- Automatically fetch and archive measurements into a local sqlite3 (default to `~/Documents/aranet4.db`)
- Plot full history.
- Quickly print recent measurements.

## Quickstart

> [!TIP]
> If you are new to aranet4 scripting, you probably should have a look first at that repo before this one.

### Install

- **Recommended (with [uv](https://docs.astral.sh/uv/))**: Nothing to do. The provided `pyproject.toml` handles dependencied and virtual environments.
- **Alternative (with pip)**: install with `pip install .`

### Configuration

- `cp .env.example .env`
- Required edits in `.env`:
   - Sensor name
   - MAC address (find it using `aranetctl --scan` from [Aranet4-Python](https://github.com/Anrijs/Aranet4-Python))

### Usage

**Fetch measurements**

- Use `aranet4.py fetch` to fetch the data from the aranet4 device and update a local sqlite db (default is `~/Documents/aranet4.db`)

**Plot measurements**

- Use `aranet4.py plot` to plot measurements. Defaults to CO2 of last 3 days, run with `--help` to see all options.

**Print recent measurements**
- Use `aranet4.py print` to quickly print the 10 most recent measurements. Can print oldest with `--oldest` or more measurements with `--n`

## Automated Data Fetching (MacOS)

You probably want to run this periodically to not lose oldest measurements. You can set automatic fetching every 3 hours: 

1. Configure absolute paths in `com.diegobit.aranet4-fetch.plist`.
2. Install LaunchAgent:
   ```bash
   cp com.diegobit.aranet4-fetch.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.diegobit.aranet4-fetch.plist
   ```

> [!NOTE]
> If not using uv, edit `aranet4-fetch.sh` to invoke Python appropriately.

