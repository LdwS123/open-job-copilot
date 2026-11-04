#!/bin/zsh
# ./run_all.sh [start_index]  -> watcher + supervisor + caffeinate. Keep this folder OUTSIDE /tmp (macOS wipes /tmp on reboot).
R="$(cd "$(dirname "$0")" && pwd)"; cd "$R"
[ -f ../profile.json ] || python3 setup.py   # first run: asks who you are and what you are looking for
[ -f mark_offsets.py ] && python3 -I mark_offsets.py >/dev/null 2>&1   # so audit.py / stop_after.py only look at THIS launch
pkill -f "python3 -I supervisor.py";pkill -f "python3 -I watcher.py"; sleep 1; rm -f STOP
nohup python3 -I watcher.py > watcher.out 2>&1 &
nohup python3 -I supervisor.py ${1:-0} > supervisor.out 2>&1 &
nohup caffeinate -dimsu -w $! > /dev/null 2>&1 &
echo started
# Closed-lid operation needs:  sudo pmset -a disablesleep 1   (undo with 0)
