# ============================================================
# signalr_service.py
# ============================================================
import base64
import hashlib
import hmac
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SIGNALR_CONNECTION_STRING: str = os.getenv("SIGNALR_CONNECTION_STRING", "")


def parse_connection_string(connection_string: str) -> tuple[str, str]:
    parts: dict[str, str] = {}
    for part in connection_string.split(";"):
        if "=" in part:
            key, _, value = part.partition("=")
            parts[key.strip()] = value.strip()
    endpoint   = parts.get("Endpoint", "").rstrip("/")
    access_key = parts.get("AccessKey", "")
    return endpoint, access_key


def generate_jwt(audience: str, access_key: str, ttl: int = 3600) -> str:
    """
    Azure SignalR Service REST API 用 JWT を生成する
    audience は REST APIのURLそのもの
    """
    now = int(time.time())

    # separators=(",", ":") でスペースなし（必須）
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(
            {"alg": "HS256", "typ": "JWT"},
            separators=(",", ":"),
        ).encode()
    ).rstrip(b"=").decode()

    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(
            {"aud": audience, "iat": now, "exp": now + ttl},
            separators=(",", ":"),
        ).encode()
    ).rstrip(b"=").decode()

    signing_input = f"{header_b64}.{payload_b64}"
    raw_sig = hmac.new(
        key=access_key.encode("utf-8"),
        msg=signing_input.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(raw_sig).rstrip(b"=").decode()

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def send_message(hub: str, target: str, arguments: list) -> bool:
    if not SIGNALR_CONNECTION_STRING:
        print("[SignalR] SIGNALR_CONNECTION_STRING が未設定のためスキップ")
        return False

    endpoint, access_key = parse_connection_string(SIGNALR_CONNECTION_STRING)

    if not endpoint or not access_key:
        print("[SignalR] Endpoint または AccessKey のパースに失敗")
        return False

    # REST API の URL
    url = f"{endpoint}/api/v1/hubs/{hub}"

    # ★ audience は REST API の URL と完全一致させる
    token = generate_jwt(audience=url, access_key=access_key)

    body = json.dumps(
        {"target": target, "arguments": arguments},
        ensure_ascii=False,
    ).encode("utf-8")

    req = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type" : "application/json",
        },
        method="POST",
    )

    print(f"[SignalR] 送信開始 url={url} target={target} args={arguments}")

    try:
        with urlopen(req, timeout=10) as res:
            status = res.getcode()
            print(f"[SignalR] 送信成功 status={status}")
            return status in (200, 202)

    except HTTPError as e:
        body_text = e.read().decode("utf-8") if hasattr(e, "read") else ""
        print(f"[SignalR] HTTPError: status={e.code}, body={body_text}")
        return False

    except URLError as e:
        print(f"[SignalR] URLError: {e.reason}")
        return False

    except Exception as e:
        print(f"[SignalR] ERROR: {type(e).__name__}: {e}")
        return False