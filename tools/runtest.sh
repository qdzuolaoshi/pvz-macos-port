#!/bin/zsh
# usage: runtest.sh <binary> <resdir> <savedir> <script> <shotdir> <maxseconds> <log>
BIN=$1; RES=$2; SAVE=$3; SCRIPT=$4; SHOTS=$5; MAX=$6; LOG=$7
mkdir -p "$SHOTS" "$SAVE"
PVZP_TEST_SCRIPT="$SCRIPT" PVZP_TEST_SHOTDIR="$SHOTS" "$BIN" -resdir="$RES" -savedir="$SAVE" > "$LOG" 2>&1 &
PID=$!
for i in $(seq 1 $MAX); do
  sleep 1
  kill -0 $PID 2>/dev/null || break
done
kill -9 $PID 2>/dev/null
wait $PID 2>/dev/null
grep -E "PVZP_TEST|FATAL|Fail|rror" "$LOG" | grep -v RegEmu | head -30
