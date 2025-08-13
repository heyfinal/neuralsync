#!/usr/bin/env bash
set -euo pipefail
# Requires your Claudes wrapper installed and its own env configured.
exec Claudes --model claude-3.5-sonnet --max-tokens 8192 --context-window 200000 --debug
