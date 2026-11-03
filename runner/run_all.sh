#!/bin/zsh
# ./run_all.sh [start_index]  -> watcher + supervisor + caffeinate. Keep this folder OUTSIDE /tmp (macOS wipes /tmp on reboot).
R="$(cd "$(dirname "$0")" && pwd)"; cd "$R"
pkill -f "python3 -I supervisor.py"; pkill -f "python3 -I watcher.py"; sleep 1; rm -f STOP
nohup python3 -I watcher.py > watcher.out 2>&1 &
nohup python3 -I supervisor.py ${1:-0} > supervisor.out 2>&1 &
nohup caffeinate -dimsu -w $! > /dev/null 2>&1 &
echo started
# Closed-lid operation needs:  sudo pmset -a disablesleep 1   (undo with 0)
