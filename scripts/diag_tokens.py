"""Diagnostic: check what tokens are persisted and what the engine sees."""

import json
import os

p = os.path.expanduser("~/.config/ichnos/oauth_tokens.json")
if os.path.exists(p):
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    tokens = d.get("tokens", {})
    consumers = d.get("consumers", {})
    print("persisted tokens:", len(tokens))
    for t, info in tokens.items():
        consumer = consumers.get(t, "UNKNOWN")
        print(f"  {t[:20]}... | consumer: {consumer} | expires_at: {info.get('expires_at')}")
else:
    print("NO oauth_tokens.json — nothing persisted")

cp = os.path.expanduser("~/.config/ichnos/cce.json")
with open(cp, encoding="utf-8") as f:
    cfg = json.load(f)
print("\nconfig tokens:")
for t, c in cfg.get("tokens", {}).items():
    print(f"  {t[:20]}... | consumer: {c}")
print("config consumers:", sorted(cfg.get("consumers", {}).keys()))
