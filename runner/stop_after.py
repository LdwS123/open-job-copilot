#!/usr/bin/env python3 -I
"""Test run: stop everything after N confirmed applications or after MAXSEC seconds, whichever comes first.
usage: python3 -I stop_after.py [N=4] [MAXSEC=300]      (run in the background right after ./run_all.sh)
Then writes stop_after_result.txt and runs the audit on the window."""
import glob, json, os, re, subprocess, sys, time

R = os.path.dirname(os.path.abspath(__file__))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4
MAXSEC = int(sys.argv[2]) if len(sys.argv) > 2 else 300
t0 = time.time()
try:
    OFF = json.load(open(os.path.join(R, 'launch_offsets.json')))
except Exception:
    OFF = {f: os.path.getsize(os.path.join(R, f)) for f in os.listdir(R) if re.fullmatch(r'apply_s\d+_raw\.jsonl', f)}


def count():
    conf, gate = 0, 0
    for f in glob.glob(os.path.join(R, 'apply_s*_raw.jsonl')):
        fh = open(f, 'rb'); fh.seek(OFF.get(os.path.basename(f), 0))   # only bytes written after the launch mark (slot files are reused)
        for line in fh.read().decode('utf-8', 'replace').split('\n'):
            if 'CONFIRMED' not in line and 'GATE OK' not in line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            m = d.get('message')
            c = m.get('content') if isinstance(m, dict) else None
            if isinstance(c, list):
                for b in c:
                    if b.get('type') == 'text':
                        conf += len(re.findall(r'^\s*CONFIRMED ', b.get('text', ''), re.M))
                        gate += len(re.findall(r'^\s*GATE OK \|', b.get('text', ''), re.M))
    return conf, gate


reason = None
while True:
    conf, gate = count()
    if conf >= N:
        reason = '%d confirmées atteintes' % conf; break
    if time.time() - t0 >= MAXSEC:
        reason = 'limite de %d s atteinte' % MAXSEC; break
    time.sleep(8)

open(os.path.join(R, 'STOP'), 'w').write('stop_after')
subprocess.call(['pkill', '-f', '--', '-I supervisor.py'])
subprocess.call(['pkill', '-f', '--', '-I watcher.py'])
# grace: let an agent that already wrote GATE OK finish its submit (max 60 s)
conf, gate = count()
g0 = time.time()
while gate > conf and time.time() - g0 < 60:
    time.sleep(5); conf, gate = count()
subprocess.call(['pkill', '-f', 'claude --chrome --model sonnet -p'])
time.sleep(3)
conf, gate = count()
audit = subprocess.run(['python3', '-I', 'audit.py', str(round((time.time() - t0) / 3600 + 0.02, 3)), 'launch'],
                       cwd=R, capture_output=True, text=True).stdout
open(os.path.join(R, 'stop_after_result.txt'), 'w').write(
    'Arrêt : %s | CONFIRMED=%d GATE OK=%d | durée %d s\n\n%s' % (reason, conf, gate, time.time() - t0, audit))
