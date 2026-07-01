#!/bin/bash
# Poll for new emails
# Usage: poller.sh [--loop] [--interval N] [--filter "FILTER"]
#        poller.sh --batch [--batch-size N] [--start-offset N] [--batch-delay N]

LOOP=false
BATCH=false
INTERVAL=60
FILTER="UNSEEN"
BATCH_SIZE=50
START_OFFSET=0
BATCH_DELAY=1.0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --loop) LOOP=true; shift ;;
        --batch) BATCH=true; shift ;;
        --interval) INTERVAL="$2"; shift 2 ;;
        --filter) FILTER="$2"; shift 2 ;;
        --batch-size) BATCH_SIZE="$2"; shift 2 ;;
        --start-offset) START_OFFSET="$2"; shift 2 ;;
        --batch-delay) BATCH_DELAY="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Validate conflicting options
if [ "$LOOP" = true ] && [ "$BATCH" = true ]; then
    echo "Error: --loop and --batch cannot be used together"
    exit 1
fi

if [ "$BATCH" = true ]; then
    # One-time batch import
    python -m mailextractor.app.poller.poller --batch \
        --batch-size "$BATCH_SIZE" \
        --start-offset "$START_OFFSET" \
        --batch-delay "$BATCH_DELAY" \
        --filter "$FILTER"
elif [ "$LOOP" = true ]; then
    # Continuous polling loop
    trap 'echo "Stopped"; exit 0' SIGINT
    echo "[$(date '+%H:%M:%S')] Starting poller loop (interval: ${INTERVAL}s, filter: $FILTER)"
    while true; do
        python -m mailextractor.app.poller.poller --filter "$FILTER" || echo "Poll failed"
        sleep "$INTERVAL"
    done
else
    # Single poll
    python -m mailextractor.app.poller.poller --filter "$FILTER"
fi
