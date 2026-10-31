#!/usr/bin/env bash
# Chạy một lệnh của eup_pm trong virtualenv. Dùng trong crontab, VD: deploy/run.sh daily
set -euo pipefail
cd "$(dirname "$0")/.."
exec ./.venv/bin/python -m eup_pm "$@"
