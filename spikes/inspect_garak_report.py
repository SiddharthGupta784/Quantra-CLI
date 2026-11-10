import collections
import json
import sys

path = sys.argv[1]
rows = [json.loads(line) for line in open(path, encoding="utf-8")]
print("rows:", len(rows))
print("entry_type counts:", dict(collections.Counter(r.get("entry_type") for r in rows)))
seen = set()
for r in rows:
    t = r.get("entry_type")
    if t in seen:
        continue
    seen.add(t)
    s = json.dumps(r)
    print(f"\n--- first '{t}' keys={list(r)}\n{s[:700]}")
