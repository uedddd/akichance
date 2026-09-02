# test_signalr.py
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
    print("[.env] 読み込み成功")
except ImportError:
    print("[.env] python-dotenv 未インストール")

import base64
import hashlib
import hmac
import json
import time
import urllib.request
import urllib.error

conn_str = os.getenv("SIGNALR_CONNECTION_STRING", "")
print("\n=== 環境変数確認 ===")
print(f"SIGNALR_CONNECTION_STRING: '{conn_str[:40]}...'" if len(conn_str) > 40 else f"'{conn_str}'")

if not conn_str:
    print("ERROR: SIGNALR_CONNECTION_STRING が空です")
    sys.exit(1)

parts: dict[str, str] = {}
for part in conn_str.split(";"):
    if "=" in part:
        key, _, value = part.partition("=")
        parts[key.strip()] = value.strip()

endpoint   = parts.get("Endpoint", "").rstrip("/")
access_key = parts.get("AccessKey", "")

print("\n=== 接続文字列パース確認 ===")
print(f"Endpoint  : {endpoint}")
print(f"AccessKey : {access_key[:6]}****")

url = f"{endpoint}/api/v1/hubs/seatHub"
now = int(time.time())

header_json  = json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
payload_json = json.dumps({"aud": url, "iat": now, "exp": now + 3600}, separators=(",", ":")).encode()
header_b64   = base64.urlsafe_b64encode(header_json).rstrip(b"=").decode()
payload_b64  = base64.urlsafe_b64encode(payload_json).rstrip(b"=").decode()
signing_input = f"{header_b64}.{payload_b64}"
raw_sig = hmac.new(
    key=access_key.encode("utf-8"),
    msg=signing_input.encode("utf-8"),
    digestmod=hashlib.sha256,
).digest()
sig_b64 = base64.urlsafe_b64encode(raw_sig).rstrip(b"=").decode()
token = f"{header_b64}.{payload_b64}.{sig_b64}"

body = json.dumps({
    "target": "seatStatusUpdated",
    "arguments": [{"seatId": 999, "status": "test"}]
}, ensure_ascii=False).encode("utf-8")

req = urllib.request.Request(
    url,
    data=body,
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    },
    method="POST",
)

print(f"\n=== HTTP送信テスト ===")
print(f"送信先: {url}")

try:
    with urllib.request.urlopen(req, timeout=10) as res:
        status = res.getcode()
        print(f"SUCCESS: HTTPステータス={status}")
        if status == 202:
            print("SignalR送信成功 (202 Accepted)")
        else:
            print(f"予期しないステータス: {status}")

except urllib.error.HTTPError as e:
    body_text = e.read().decode("utf-8") if hasattr(e, "read") else ""
    print(f"HTTPError: status={e.code}")
    print(f"body={body_text}")

except urllib.error.URLError as e:
    print(f"URLError: {e.reason}")

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")