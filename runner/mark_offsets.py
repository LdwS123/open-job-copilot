#!/usr/bin/env python3 -I
"""Snapshot the byte size of every apply_s*_raw.jsonl at launch time -> launch_offsets.json.
Slot names are reused and files are appended to, so audit.py / stop_after.py read only bytes written after this mark."""
import glob, json, os
R = os.path.dirname(os.path.abspath(__file__))
off = {os.path.basename(f): os.path.getsize(f) for f in glob.glob(os.path.join(R, 'apply_s*_raw.jsonl'))}
json.dump(off, open(os.path.join(R, 'launch_offsets.json'), 'w'))
print('marked %d files' % len(off))
