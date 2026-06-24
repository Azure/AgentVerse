import os, json, base64, time, requests, sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

ENDPOINT = os.getenv("IMAGE_ENDPOINT")
DEPLOY = os.getenv("IMAGE_DEPLOYMENT")
API_VER = "2025-04-01-preview"
import subprocess
KEY = subprocess.check_output(
    ["az","cognitiveservices","account","keys","list",
     "-n","prisa-demo-comic-resource","-g","Demo","--query","key1","-o","tsv"], shell=True
).decode().strip()

url = f"{ENDPOINT}/openai/deployments/{DEPLOY}/images/generations?api-version={API_VER}"
body = {
    "prompt": "yellow banner BERLIN",
    "size": "1024x1024",
    "quality": "low",
    "n": 1,
    "output_format": "png",
}
print("POST", url, "quality=low size=1024x1024")
t0 = time.time()
try:
    r = requests.post(url, headers={"Api-Key": KEY, "Content-Type":"application/json"}, json=body, timeout=600)
    print("status=", r.status_code, "elapsed=", round(time.time()-t0,1))
    print(r.text[:600])
    if r.status_code == 200:
        d = r.json()["data"][0]
        out = Path("app/output/smoke.png")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(base64.b64decode(d["b64_json"]))
        print("Saved", out, out.stat().st_size, "bytes")
except Exception as e:
    print("ERROR after", round(time.time()-t0,1), "s:", e)
