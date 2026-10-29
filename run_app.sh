#!/bin/bash
# Root launcher for StockHold Web Application
cd "$(dirname "$0")"
exec ./stockhold/run_app.sh "$@"
