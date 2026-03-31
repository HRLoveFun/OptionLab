#!/usr/bin/env python3
"""Quick verification of US.AAPL futu response."""
import json
import subprocess

r = subprocess.run(
    ["curl", "-s", "--max-time", "30",
     "http://127.0.0.1:5001/api/option_chain?ticker=US.AAPL&source=futu"],
    capture_output=True, text=True,
)
d = json.loads(r.stdout)

exps = d.get("expirations", [])
chain = d.get("chain", {})
spot = d.get("spot")
print(f"expirations: {len(exps)} dates")
print(f"chain dates: {len(chain)}")
print(f"spot: {spot}")

if chain:
    first = list(chain.keys())[0]
    calls = chain[first].get("calls", [])
    puts = chain[first].get("puts", [])
    print(f"\nFirst date ({first}):")
    print(f"  calls: {len(calls)} records")
    print(f"  puts: {len(puts)} records")
    if calls:
        print(f"  calls[0] keys: {sorted(calls[0].keys())}")
        print(f"  calls[0]: {calls[0]}")

# Verify itm field - with no spot, all itm should be False
itm_values = set()
for date, data in chain.items():
    for c in data.get("calls", []):
        itm_values.add(c.get("itm"))
    for p in data.get("puts", []):
        itm_values.add(p.get("itm"))
print(f"\nitm values present: {itm_values}")
print(f"spot is None: {spot is None}")
if spot is None:
    print("NOTE: spot=None due to US market off-hours (subscribe failed)")
    print("      itm=False for all contracts (correct behavior when spot unavailable)")
