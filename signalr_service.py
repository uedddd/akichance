# ============================================================
# signalr_service.py
# Azure SignalR Service へメッセージを送信するモジュール
# ============================================================

# 標準ライブラリ
import base64
import hashlib
import hmac
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# 環境変数
# ---------------------------------------------------------------------------
SIGNALR_CONNECTION_STRING: str = os.getenv("SIGNALR_CONNECTION_STRING", "")


# ---------------------------------------------------------------------------
# 接続文字列パーサー
# ---------------------------------------------------------------------------
def parse_connection_string(connection_string: str) -> tuple[str, str]:
    """
    SignalR の接続文字列をパースして Endpoint と AccessKey を返す

    接続文字列の形式:
        Endpoint=https://xxxx.service.signalr.net;AccessKey=XXXX;Version=1.0;
    """
    parts: dict[str, str] = {}
    for part in connection_string.split(";"):
        if "=" in part:
            key, _, value = part.partition("=")
            parts[key.strip()] = value.strip()

    endpoint   = parts.get("Endpoint", "").rstrip("/")
    access_key = parts.get("AccessKey", "")

    if not endpoint or not access_key:
        raise ValueError(
            f"接続文字列のパースに失敗しました。"
            f"検出されたキー: {list(parts.keys())}"
        )

    return endpoint, access_key


# ---------------------------------------------------------------------------
# JWT 生成（Bearer token）
# ---------------------------------------------------------------------------
def generate_jwt(audience: str, access_key: str, ttl: int = 3600) -> str:
    """
    Azure SignalR Service REST API 用の JWT を生成する

    Parameters
    ----------
    audience   : JWT の audience（REST API の URL と同じ）
    access_key : 接続文字列の AccessKey
    ttl        : トークン有効期間（秒）

    Returns
    -------
    JWT 文字列（署名済み）
    """
    now = int(time.time())

    # --- ヘッダー ---
    header_json = json.dumps(
        {"alg": "HS256", "typ": "JWT"},
        separators=(",", ":"),
    ).encode()
    header_b64 = base64.urlsafe_b64encode(header_json).rstrip(b"=").decode()

    # --- ペイロード ---
    payload_json = json.dumps(
        {"aud": audience, "iat": now, "exp": now + ttl},
        separators=(",", ":"),
    ).encode()
    payload_b64 = base64.urlsafe_b64encode(payload_json).rstrip(b"=").decode()

    # --- 署名 ---
    signing_input = f"{header_b64}.{payload_b64}"
    raw_sig = hmac.new(
        key=access_key.encode("utf-8"),
        msg=signing_input.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(raw_sig).rstrip(b"=").decode()

    return f"{header_b64}.{payload_b64}.{sig_b64}"


# ---------------------------------------------------------------------------
# メッセージ送信
# ---------------------------------------------------------------------------
def send_message(hub: str, target: str, arguments: list) -> bool:
    """
    Azure SignalR Service に接続している全クライアントへ
    メッセージをブロードキャストする

    Parameters
    ----------
    hub       : SignalR のハブ名（例: "seatHub"）
    target    : クライアント側のメソッド名（例: "seatStatusUpdated"）
    arguments : 送信データのリスト（例: [{"seatId": 1, "status": "reserved"}]）

    Returns
    -------
    True  : 送信成功
    False : 送信失敗
    """
    # ------------------------------------------------------------------
    # 1. 接続文字列チェック
    # ------------------------------------------------------------------
    if not SIGNALR_CONNECTION_STRING:
        print("[SignalR] ⚠️  SIGNALR_CONNECTION_STRING が未設定のためスキップします")
        return False

    # ------------------------------------------------------------------
    # 2. 接続文字列パース
    # ------------------------------------------------------------------
    try:
        endpoint, access_key = parse_connection_string(SIGNALR_CONNECTION_STRING)
    except ValueError as e:
        print(f"[SignalR] ❌ 接続文字列パースエラー: {e}")
        return False

    # ------------------------------------------------------------------
    # 3. REST API エンドポイント & JWT 生成
    #    URL 形式: {endpoint}/api/v1/hubs/{hub}
    # ------------------------------------------------------------------
    url   = f"{endpoint}/api/v1/hubs/{hub}"
    token = generate_jwt(audience=url, access_key=access_key)

    # ------------------------------------------------------------------
    # 4. リクエスト送信
    # ------------------------------------------------------------------
    payload = json.dumps(
        {"target": target, "arguments": arguments},
        ensure_ascii=False,
    ).encode("utf-8")

    request = Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",   # ✅ Bearer JWT
            "Content-Type" : "application/json",
        },
        method="POST",
    )

    print(f"[SignalR] 送信開始 → url={url}, target={target}, args={arguments}")

    try:
        with urlopen(request, timeout=10) as res:
            status = res.getcode()
            if status == 202:
                # 202 Accepted が正常レスポンス
                print(f"[SignalR] ✅ 送信成功 (202 Accepted)")
                return True
            else:
                body = res.read().decode("utf-8")
                print(f"[SignalR] ⚠️  予期しないステータス: status={status}, body={body}")
                return False

    except HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        print(f"[SignalR] ❌ HTTPError: status={e.code}, body={body}")
        # よくあるエラーのヒントを表示
        _print_hint(e.code)
        return False

    except URLError as e:
        print(f"[SignalR] ❌ URLError（接続失敗）: {e.reason}")
        return False

    except Exception as e:
        print(f"[SignalR] ❌ 予期しないエラー: {type(e).__name__}: {e}")
        return False


# ---------------------------------------------------------------------------
# デバッグヒント
# ---------------------------------------------------------------------------
def _print_hint(status_code: int) -> None:
    hints = {
        401: "AccessKey が正しくないか、JWT 生成に問題があります",
        404: "ハブ名が存在しないか、Endpoint URL が間違っています",
        400: "リクエストボディの形式が正しくありません",
        500: "SignalR Service 側のエラーです。Azure Portal を確認してください",
    }
    hint = hints.get(status_code, "Azure Portal でサービス状態を確認してください")
    print(f"[SignalR] 💡 ヒント ({status_code}): {hint}")
