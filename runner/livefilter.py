import sys, json, time
out = open(sys.argv[1], 'a', buffering=1); raw = open(sys.argv[2], 'a', buffering=1); final = open(sys.argv[3], 'w')
tag = (sys.argv[4] + ' ') if len(sys.argv) > 4 else ''
def log(s): out.write(time.strftime('%H:%M:%S ') + tag + s + '\n')
log('--- run started ---')
for line in sys.stdin:
    raw.write(line)
    try: e = json.loads(line)
    except Exception: continue
    if e.get('type') == 'assistant':
        for c in e.get('message', {}).get('content', []):
            if c.get('type') == 'text' and c['text'].strip(): log(c['text'].strip()[:400])
            elif c.get('type') == 'tool_use':
                i = c.get('input', {}); log('> ' + c.get('name', '').replace('mcp__claude-in-chrome__', '') + ' ' + str(i.get('url') or i.get('text') or i.get('action') or i.get('query') or '')[:140])
    elif e.get('type') == 'result':
        final.write(e.get('result', '')); final.flush(); log('--- run finished ---')
