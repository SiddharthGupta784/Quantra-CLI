import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
print("top keys:", list(d))
r = d["results"]
print("results keys:", list(r))
print("stats:", json.dumps(r.get("stats")))
rows = r["results"]
print("n rows:", len(rows), "row keys:", list(rows[0]))
x = rows[0]
for k in ("success", "score", "failureReason", "latencyMs", "namedScores"):
    print(f"  {k}:", x.get(k))
print("  provider:", x.get("provider"))
print("  vars:", x.get("vars"))
print("  response keys:", list(x.get("response", {})))
print("  gradingResult:", json.dumps(x.get("gradingResult"))[:500])
print("config keys:", list(d.get("config", {})))
print("evalId:", d.get("evalId"))
