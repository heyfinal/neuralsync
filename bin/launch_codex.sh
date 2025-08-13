#!/usr/bin/env bash
set -euo pipefail
# Requires your codes wrapper installed and its own env configured.
exec codes --model gpt-4o-mini --max-tokens 8192 --context-window 128000 --debug
