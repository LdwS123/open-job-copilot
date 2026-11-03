#!/bin/zsh
# usage: launch.sh <promptname> <TAG>
R="$(cd "$(dirname "$0")" && pwd)"; cd "$R"
claude --chrome --model "${AGENT_MODEL:-sonnet}" -p "$(cat prompt_$1.txt)" --allowedTools "mcp__claude-in-chrome__*" --output-format stream-json --verbose < /dev/null 2>&1 \
  | python3 -I livefilter.py "$R/live.log" "apply_$1_raw.jsonl" "apply_$1_final.out" "[$2]"
