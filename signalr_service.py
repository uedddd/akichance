# ============================================================
# signalr_service.py
# Azure SignalR Service へメッセージを送信するモジュール
# ============================================================

# 標準ライブラリ
import os
import hmac
import hashlib
import base64
import time
from urllib.parse import quote

# HTTPクライアント
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# .env から接続文字列を取得する
SIGNALR_CONNECTION_STRING: str = os.getenv("SIGNALR_CONNECTION_STRING", "")

def parse_connection_string(connection_string: str) -> tuple[str, str]:
    """
    SignalR の接続文字列をパースして
    Endpoint と AccessKey を返す

    接続文字列の形式:
    Endpoint=https://xxxx.service.signalr.net;AccessKey=XXXX;Version=1.0;
    """
    parts = {}
    for part in connection_string.split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            parts[key] = value

    endpoint = parts.get("Endpoint", "").rstrip("/")
    access_key = parts.get("AccessKey", "")

    return endpoint, access_key


def generate_token(endpoint: str, access_key: str, hub: str) -> str:
    """
    SignalR Service への REST API リクエストに必要な
    アクセストークンを生成して返す
    """
    # トークンの対象URLを生成する
    url = f"{endpoint}/api/v1/hubs/{hub}"

    # トークンの有効期限（現在時刻 + 1時間）
    expiry = int(time.time()) + 3600

    # 署名対象の文字列を生成する
    string_to_sign = f"{quote(url, safe='')}\n{expiry}"

    # HMAC-SHA256で署名を生成する
    signature = hmac.new(
        access_key.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    # Base64エンコードする
    signature_b64 = base64.b64encode(signature).decode("utf-8")

    # SharedAccessSignature形式のトークンを返す
    return (
        f"SharedAccessSignature "
        f"sr={quote(url, safe='')}"
        f"&sig={quote(signature_b64, safe='')}"
        f"&se={expiry}"
    )


def send_message(hub: str, target: str, arguments: list) -> bool:
    """
    Azure SignalR Service に接続している
    全クライアントへメッセージを送信する

    引数:
        hub       : SignalR のハブ名（例: "seatHub"）
        target    : フロントエンドで受け取るメソッド名（例: "seatStatusUpdated"）
        arguments : 送信するデータのリスト（例: [{"seatId": 1, "status": "使用中"}]）

    戻り値:
        True  : 送信成功
        False : 送信失敗
    """
    # 接続文字列が設定されていない場合はスキップする
    if not SIGNALR_CONNECTION_STRING:
        print("WARNING: SIGNALR_CONNECTION_STRING が設定されていません")
        return False

    # 接続文字列をパースする
    endpoint, access_key = parse_connection_string(SIGNALR_CONNECTION_STRING)

    # アクセストークンを生成する
    token = generate_token(endpoint, access_key, hub)

    # SignalR Service の REST API エンドポイント
    url = f"{endpoint}/api/v1/hubs/{hub}"

    # リクエストヘッダー
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    # 送信するメッセージ
    payload = json.dumps({
        "target": target,
        "arguments": arguments,
    }).encode("utf-8")

    request = Request(url, data=payload, headers=headers, method="POST")

    try:
        with urlopen(request, timeout=30) as res:
            status = res.getcode()
            if status == 202:
                print(f"SignalR 送信成功: target={target}")
                return True
            else:
                body = res.read().decode("utf-8")
                print(f"SignalR 送信失敗: status={status}, body={body}")
                return False

    except HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, 'read') else str(e)
        print(f"SignalR 送信失敗: status={e.code}, body={body}")
        return False

    except URLError as e:
        print(f"SignalR 送信エラー: {e.reason}")
        return False

    except Exception as e:
        print(f"SignalR 送信エラー: {e}")
        return False
