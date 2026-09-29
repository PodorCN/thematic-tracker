from __future__ import annotations
"""Launch ROUND 2 of the independent frontend code review as a separate
foreground Hermes CLI process. Refuses to relaunch if the r2 review exists."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parents[2]
run = root / "review-artifacts" / "code-2026-09-29-frontend-tenor"
manifest = run / "freeze-manifest.json"
review = run / "pm-review-r2.json"
log = run / "pm-review-run.log"

if review.exists():
    raise SystemExit("round-2 review already exists - do not relaunch")
m = json.loads(manifest.read_text(encoding="utf-8"))
assert m.get("round") == 2, "manifest is not the round-2 freeze"
for entry in m["files"]:
    p = root / entry["path"]
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest == entry["sha256"], f"digest mismatch on {entry['path']}: {digest} vs {entry['sha256']} - working tree changed after freeze; STOP"
print("round-2 freeze manifest digests OK", flush=True)

prompt = (run / "pm-review-r2-prompt.txt").read_text(encoding="utf-8")
hermes = shutil.which("hermes") or r"D:\Mega\Claude\Hermes\installs\9a36a96ac45cf3dd\environments\adbb89a5840142adb7acaeec1958ac2d\venv\Scripts\hermes.exe"
if not Path(hermes).exists() and not shutil.which("hermes"):
    raise SystemExit(f"hermes CLI not found (looked at {hermes})")
argv = [hermes, "--provider", "opencode-go", "--model", "deepseek-v4.1-flash", "-z", prompt]
env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
print(f"launching round-2 independent code review: provider=opencode-go model=deepseek-v4.1-flash; hermes={hermes}", flush=True)
with open(log, "a", encoding="utf-8") as f:
    f.write(f"\n=== r2 attempt start {time.strftime('%Y-%m-%dT%H:%M:%S%z')} ===\n")
    f.flush()
    result = subprocess.run(argv, cwd=root, stdout=f, stderr=subprocess.STDOUT, env=env)
    f.write(f"\n=== r2 attempt end rc={result.returncode} {time.strftime('%Y-%m-%dT%H:%M:%S%z')} ===\n")
    f.flush()
print(f"review process exit_code={result.returncode}", flush=True)
if not review.is_file():
    raise SystemExit("reviewer exited without writing pm-review-r2.json")
print("pm-review-r2.json present.", flush=True)
