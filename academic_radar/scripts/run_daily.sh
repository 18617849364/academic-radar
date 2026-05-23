#!/bin/zsh
set -u

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

PROJECT_DIR="/Users/zhaomuchuan/Documents/ai使用研究/academic_radar"
RUN_DATE="$(date +%F)"
CRON_LOG="$PROJECT_DIR/output/logs/cron_${RUN_DATE}.log"

mkdir -p "$PROJECT_DIR/output/logs"
{
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] cron wrapper started"
  cd "$PROJECT_DIR" || exit 10
  "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/scripts/run_daily.py"
  status=$?
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] cron wrapper finished with status $status"
  exit $status
} >> "$CRON_LOG" 2>&1
