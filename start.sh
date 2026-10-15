#!/usr/bin/env bash
set -eu

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$PROJECT_DIR/config/app.conf"
LOG_FILE="$PROJECT_DIR/logs/app.log"
APP_NAME=""

while IFS='=' read -r key value || [[ -n "$key" ]]; do
    case "$key" in
        APP_NAME) APP_NAME="$value" ;;
    esac
done < "$CONFIG_FILE"

if [[ -z "$APP_NAME" ]]; then
    printf 'Ошибка: укажи APP_NAME в config/app.conf\n' >&2
    exit 1
fi

mkdir -p -- "$PROJECT_DIR/logs"
sleep_pid=""

write_log() {
    printf '%s app=%s pid=%s event=%s\n' \
        "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$APP_NAME" "$$" "$1" >> "$LOG_FILE"
}

cleanup() {
    if [[ -n "$sleep_pid" ]]; then
        kill "$sleep_pid" 2>/dev/null || true
        wait "$sleep_pid" 2>/dev/null || true
    fi
    write_log stopped
}

trap cleanup EXIT
trap 'exit 0' TERM INT

write_log started
while true; do
    write_log heartbeat
    sleep 2 &
    sleep_pid=$!
    wait "$sleep_pid"
    sleep_pid=""
done
