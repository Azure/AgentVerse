import os, json, base64, time, requests, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

ENDPOINT = os.getenv("IMAGE_ENDPOINT")
DEPLOY = os.getenv("IMAGE_DEPLOYMENT")
API_VER = os.getenv("IMAGE_API_VERSION", "2025-04-01-preview")
KEY = os.getenv("IMAGE_API_KEY")

if not KEY:
    # Pull from Azure CLI
    import subprocess
    KEY = subprocess.check_output(
        ["az", "cognitiveservices", "account", "keys", "list",
         "-n", "prisa-demo-comic-resource", "-g", "Demo",
         "--query", "key1", "-o", "tsv"], shell=True
    ).decode().strip()
    print(f"Pulled key from CLI, len={len(KEY)}")

url = f"{ENDPOINT}/openai/deployments/{DEPLOY}/images/generations?api-version={API_VER}"
print(f"POST {url}")
body = {
    "prompt": "A horizontal banner promoting a flight to Berlin, yellow and white, modern minimal style, text 'BERLIN €89'",
    "size": "1536x1024",
    "n": 1,
}
t0 = time.time()
r = requests.post(url, headers={"api-key": KEY, "Content-Type": "application/json"}, json=body, timeout=180)
print(f"status={r.status_code} elapsed={time.time()-t0:.1f}s")
if r.status_code != 200:
    print(r.text[:1000])
    sys.exit(1)
j = r.json()
d = j["data"][0]
out = Path(__file__).parent.parent / "output" / "smoke.png"
out.parent.mkdir(parents=True, exist_ok=True)
if "b64_json" in d:
    out.write_bytes(base64.b64decode(d["b64_json"]))
    print(f"Wrote {out} ({out.stat().st_size} bytes)")
elif "url" in d:
    img = requests.get(d["url"], timeout=60)
    out.write_bytes(img.content)
    print(f"Downloaded from URL to {out}")
else:
    print("Unknown shape:", list(d.keys()))
