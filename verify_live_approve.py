import subprocess
import sys
import time
import urllib.request

url = "http://127.0.0.1:5000/login"

print("Checking server reachability...")
for attempt in range(10):
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            print("Server status:", resp.status)
            break
    except Exception as exc:
        print(f"Attempt {attempt + 1}/10 failed: {exc}")
        time.sleep(0.5)
else:
    print("Server did not respond on", url)
    sys.exit(1)

print("Running live approval urllib test...")
result = subprocess.run([sys.executable, "-u", "test_live_approve_urllib.py"], capture_output=True, text=True)
print("Return code:", result.returncode)
if result.stdout:
    print("--- STDOUT ---")
    print(result.stdout)
if result.stderr:
    print("--- STDERR ---")
    print(result.stderr)

sys.exit(result.returncode)
