#!/bin/bash
# Wrapper script to execute the aranet4 fetch process via uv.
# The WorkingDirectory should be set by the launchd plist.
# The purpose of this is to have it with a proper name in the Launch Items of MacOS

/usr/local/bin/uv run aranet.py fetch
