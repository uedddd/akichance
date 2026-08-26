from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from datetime import datetime
import struct
import time
import hmac
import hashlib
import base64
from typing import Iterator, List, Optional

import pyodbc
from azure.identity import ClientSecretCredential

env_file = Path(__file__).parent / ".env"
if env_file.exists() and load_dotenv is not None:
    load_dotenv(env_file)

from signalr_service import send_message
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# データベース接続設定
# ---------------------------------------------------------------------------

AZURE_SQL_SERVER: str = os.getenv(
    "AZURE_SQL_SERVER", "akichanceserver.database.windows.net"
)
AZURE_SQL_DATABASE: str = os.getenv("AZURE_SQL_DATABASE", "akichanceDB")
AZURE_CLIENT_ID: str = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET: str = os.getenv("AZURE_CLIENT_SECRET", "")
AZURE_TENANT_ID: str = os.getenv("AZURE_TENANT_ID", "")
AZURE_SQL_DRIVER: str = os.getenv(
    "AZURE_SQL_DRIVER", "ODBC Driver 18 for SQL Server"
)

CONNECTION_STRING: str = (
    f"DRIVER={{{AZURE_SQL_DRIVER}}};"
    f"SERVER={AZURE_SQL_SERVER};"
    f"DATABASE={AZURE_SQL_DATABASE};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)


def get_token_struct() -> bytes:
    """Azure SQL へ Service Principal 認証でアクセスするためのトークンを生成する"""
    if not all([AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID]):
        raise RuntimeError(
            "AZURE_CLIENT_ID / AZURE_CLIENT_SECRET / AZURE_TENANT_ID が"
            "設定されていません"
        )
    credential = ClientSecretCredential(
        tenant_id=AZURE_TENANT_ID,
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET,
    )
    token = credential.get_token("https://database.windows.net/.default")
    token_bytes = token.token.encode("utf-16-le")
    return struct.pack(f"<i{len(token_bytes)}s", len(token_bytes), token_bytes)


def open_connection() -> pyodbc.Connection:
    """Azure SQL への認証済みコネクションを返す"""
    return pyodbc.connect(
        CONNECTION_STRING, attrs_before={1256: get_token_struct()}
    )


# ---------------------------------------------------------------------------
# FastAPI 初期化
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Akichance Reservation / Seat Management API",
    description="Reservation and seat management API for Akichance. (Azure SQL)",
    version="3.4.0",
)

# ---------------------------------------------------------------------------
# Pydantic モデル定義（フロア）
# ---------------------------------------------------------------------------

class FloorRead(BaseModel):
    """floors テーブルに対応したレスポンスモデル"""
    floor_id: int
    floor_name: str
    floor_order: int
    is_active: bool

    class Config:
        orm_mode = True


# ---------------------------------------------------------------------------
# Pydantic モデル定義（座席）
# ---------------------------------------------------------------------------

class SeatRead(BaseModel):
    """seats テーブルの全カラムに対応したレスポンスモデル"""
    seat_id: int
    floor_id: int
    seat_name: str
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    seat_type: str
    capacity: Optional[int] = None
    has_monitor: bool

    class Config:
        orm_mode = True


class SeatCreate(BaseModel):
    """座席作成リクエストモデル"""
    floor_id: int = Field(..., description="所属フロアID")
    seat_name: str = Field(..., description="座席名（表示用）")
    status: str = Field("empty", description="座席ステータス")
    is_active: bool = Field(True, description="予約受付フラグ")
    seat_type: str = Field("desk", description="座席種別")
    capacity: Optional[int] = Field(None, description="収容人数")
    has_monitor: bool = Field(False, description="モニター有無")


class SeatUpdate(BaseModel):
    """座席更新リクエストモデル（全フィールド任意）"""
    floor_id: Optional[int] = None
    seat_name: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    seat_type: Optional[str] = None
    capacity: Optional[int] = None
    has_monitor: Optional[bool] = None


# ---------------------------------------------------------------------------
# Pydantic モデル定義（予約）
# ---------------------------------------------------------------------------
# reservations テーブルの status CHECK 制約:
#   reserved / in_use / cancelled / expired / completed

class ReservationRead(BaseModel):
    """reservations テーブルの全カラムに対応したレスポンスモデル"""
    reservation_id: int
    seat_id: int
    user_id: int
    outlook_event_id: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    status: str
    notified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ReservationCreate(BaseModel):
    """予約作成リクエストモデル"""
    user_id: int = Field(..., description="予約者のユーザーID")
    seat_id: int = Field(..., description="予約する座席ID")
    start_datetime: datetime = Field(..., description="予約開始日時")
    end_datetime: datetime = Field(..., description="予約終了日時")
    status: str = Field("reserved", description="予約ステータス")  # reserved / in_use / cancelled / expired / completed
    outlook_event_id: Optional[str] = Field(None, description="OutlookイベントID")


class ReservationUpdate(BaseModel):
    """予約更新リクエストモデル（全フィールド任意）"""
    user_id: Optional[int] = None
    seat_id: Optional[int] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    status: Optional[str] = None
    outlook_event_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Power Automate 連携モデル
# ---------------------------------------------------------------------------

class OutlookReservationSync(BaseModel):
    """Power Automate から Outlook 予約データを受信するモデル"""
    outlook_event_id: str = Field(..., description="Outlook イベント ID")
    user_id: int = Field(..., description="予約者のユーザー ID")
    seat_id: int = Field(..., description="予約する座席 ID")
    start_datetime: datetime = Field(..., description="予約開始日時")
    end_datetime: datetime = Field(..., description="予約終了日時")


class CancelResponse(BaseModel):
    status: str
    reservation_id: int
    message: str


# ---------------------------------------------------------------------------
# DB 接続・ユーティリティ
# ---------------------------------------------------------------------------

def get_connection() -> Iterator[pyodbc.Connection]:
    """FastAPI の依存性注入用コネクションジェネレータ"""
    connection = open_connection()
    connection.autocommit = False
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def row_to_dict(cursor: pyodbc.Cursor, row: pyodbc.Row) -> dict:
    """pyodbc の Row オブジェクトを dict に変換する"""
    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, row))


def init_db() -> None:
    """起動時のDB接続確認"""
    try:
        connection = open_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(1) FROM floors")
        floors_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(1) FROM seats")
        seats_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(1) FROM reservations")
        res_count = cursor.fetchone()[0]
        print(
            f"[DB] 接続成功 / floors: {floors_count}件 "
            f"/ seats: {seats_count}件 / reservations: {res_count}件"
        )
        connection.close()
    except Exception as e:
        print(f"[DB] init_db エラー（起動続行）: {e}")


# ---------------------------------------------------------------------------
# アプリケーションイベント
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup_event() -> None:
    init_db()


# ---------------------------------------------------------------------------
# SignalR ネゴシエーション
# ---------------------------------------------------------------------------

@app.post("/api/negotiate/negotiate")
async def negotiate():
    """SignalR 接続トークンを返す。未設定時は disabled を返す"""
    conn_str = os.getenv("SIGNALR_CONNECTION_STRING", "")
    hub_name = os.getenv("SIGNALR_HUB_NAME", "seatHub")

    if not conn_str:
        print("[SignalR] SIGNALR_CONNECTION_STRING 未設定 → リアルタイム更新無効")
        return {"url": "", "accessToken": "", "disabled": True}

    parts: dict[str, str] = {}
    for part in conn_str.strip().split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            parts[k.strip()] = v.strip()

    endpoint   = parts.get("Endpoint", "").rstrip("/")
    access_key = parts.get("AccessKey", "")

    audience = f"{endpoint}/client/?hub={hub_name}"
    now      = int(time.time())

    header = (
        base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        )
        .rstrip(b"=")
        .decode()
    )
    payload_b64 = (
        base64.urlsafe_b64encode(
            json.dumps({"aud": audience, "exp": now + 3600, "iat": now}).encode()
        )
        .rstrip(b"=")
        .decode()
    )
    signing_input = f"{header}.{payload_b64}"
    raw_sig = hmac.new(
        key=access_key.encode("utf-8"),
        msg=signing_input.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature = base64.urlsafe_b64encode(raw_sig).rstrip(b"=").decode()

    return {"url": audience, "accessToken": f"{header}.{payload_b64}.{signature}"}


# ---------------------------------------------------------------------------
# 静的ファイル
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "index.html")


# ---------------------------------------------------------------------------
# 共通バリデーション
# ---------------------------------------------------------------------------

# reservations.status に許可された値
VALID_RESERVATION_STATUS = {"reserved", "in_use", "cancelled", "expired", "completed"}


def assert_time_range(start: datetime, end: datetime) -> None:
    """終了日時が開始日時より後であることを検証する"""
    if end <= start:
        raise HTTPException(
            status_code=400,
            detail="end_datetime は start_datetime より後にしてください",
        )


def assert_reservation_status(status: str) -> None:
    """予約ステータスが許可された値かを検証する"""
    if status not in VALID_RESERVATION_STATUS:
        raise HTTPException(
            status_code=400,
            detail=f"status は {VALID_RESERVATION_STATUS} のいずれかにしてください",
        )


def is_overlapping(
    conn: pyodbc.Connection,
    seat_id: int,
    start: datetime,
    end: datetime,
    exclude_reservation_id: Optional[int] = None,
) -> bool:
    """指定座席・時間帯に重複する予約が存在するか確認する"""
    query = """
        SELECT COUNT(1)
        FROM reservations
        WHERE seat_id = ?
          AND status NOT IN ('cancelled', 'expired', 'completed')
          AND NOT (end_datetime <= ? OR start_datetime >= ?)
    """
    params: list = [seat_id, start, end]

    if exclude_reservation_id is not None:
        query += " AND reservation_id != ?"
        params.append(exclude_reservation_id)

    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    return cursor.fetchone()[0] > 0


# ---------------------------------------------------------------------------
# フロア API
# ---------------------------------------------------------------------------

@app.get("/api/floors", response_model=List[FloorRead])
def list_floors(
    conn: pyodbc.Connection = Depends(get_connection),
):
    """floors テーブルからフロア一覧を取得する"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT floor_id, floor_name, floor_order, is_active
        FROM floors
        WHERE is_active = 1
        ORDER BY floor_order
        """
    )
    rows = cursor.fetchall()
    return [FloorRead(**row_to_dict(cursor, row)) for row in rows]


# ---------------------------------------------------------------------------
# 座席 API
# ---------------------------------------------------------------------------

@app.get("/api/seats", response_model=List[SeatRead])
def list_seats(
    active_only: bool = Query(False, description="True: 有効な座席のみ取得"),
    floor_id: Optional[int] = Query(None, description="フロアIDで絞り込み"),
    conn: pyodbc.Connection = Depends(get_connection),
):
    """seats テーブルから座席一覧を取得する"""
    query = """
        SELECT seat_id, floor_id, seat_name, status, is_active,
               created_at, updated_at, seat_type, capacity, has_monitor
        FROM seats
        WHERE 1=1
    """
    params: list = []

    if active_only:
        query += " AND is_active = 1"

    if floor_id is not None:
        query += " AND floor_id = ?"
        params.append(floor_id)

    query += " ORDER BY floor_id, seat_id"

    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    return [SeatRead(**row_to_dict(cursor, row)) for row in rows]


@app.get("/api/seats/{seat_id}", response_model=SeatRead)
def get_seat(
    seat_id: int,
    conn: pyodbc.Connection = Depends(get_connection),
):
    """指定 seat_id の座席を取得する"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT seat_id, floor_id, seat_name, status, is_active,
               created_at, updated_at, seat_type, capacity, has_monitor
        FROM seats
        WHERE seat_id = ?
        """,
        (seat_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Seat not found")
    return SeatRead(**row_to_dict(cursor, row))


@app.post("/api/seats", response_model=SeatRead, status_code=201)
def create_seat(
    seat: SeatCreate,
    conn: pyodbc.Connection = Depends(get_connection),
):
    """新規座席を作成する"""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO seats
            (floor_id, seat_name, status, is_active, seat_type,
             capacity, has_monitor, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE());
        SELECT SCOPE_IDENTITY() AS new_id;
        """,
        (
            seat.floor_id,
            seat.seat_name,
            seat.status,
            int(seat.is_active),
            seat.seat_type,
            seat.capacity,
            int(seat.has_monitor),
        ),
    )
    cursor.nextset()
    new_id = int(cursor.fetchone()[0])
    conn.commit()

    cursor.execute(
        """
        SELECT seat_id, floor_id, seat_name, status, is_active,
               created_at, updated_at, seat_type, capacity, has_monitor
        FROM seats WHERE seat_id = ?
        """,
        (new_id,),
    )
    return SeatRead(**row_to_dict(cursor, cursor.fetchone()))


@app.put("/api/seats/{seat_id}", response_model=SeatRead)
def update_seat(
    seat_id: int,
    payload: SeatUpdate,
    conn: pyodbc.Connection = Depends(get_connection),
):
    """指定 seat_id の座席情報を更新する"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT seat_id, floor_id, seat_name, status, is_active,
               created_at, updated_at, seat_type, capacity, has_monitor
        FROM seats WHERE seat_id = ?
        """,
        (seat_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Seat not found")

    current     = row_to_dict(cursor, row)
    update_data = payload.dict(exclude_unset=True)
    current.update(update_data)

    cursor.execute(
        """
        UPDATE seats
        SET floor_id    = ?,
            seat_name   = ?,
            status      = ?,
            is_active   = ?,
            seat_type   = ?,
            capacity    = ?,
            has_monitor = ?,
            updated_at  = GETDATE()
        WHERE seat_id = ?
        """,
        (
            current["floor_id"],
            current["seat_name"],
            current["status"],
            int(current["is_active"]),
            current["seat_type"],
            current["capacity"],
            int(current["has_monitor"]),
            seat_id,
        ),
    )
    conn.commit()

    # SignalR 通知（失敗しても処理続行）
    try:
        send_message(
            hub="seatHub",
            target="seatStatusUpdated",
            arguments=[{"seatId": seat_id, "status": current["status"]}],
        )
    except Exception as e:
        print(f"[SignalR] 通知失敗（処理続行）: {e}")

    cursor.execute(
        """
        SELECT seat_id, floor_id, seat_name, status, is_active,
               created_at, updated_at, seat_type, capacity, has_monitor
        FROM seats WHERE seat_id = ?
        """,
        (seat_id,),
    )
    return SeatRead(**row_to_dict(cursor, cursor.fetchone()))


@app.delete("/api/seats/{seat_id}", status_code=204)
def delete_seat(
    seat_id: int,
    conn: pyodbc.Connection = Depends(get_connection),
):
    """指定 seat_id の座席を削除する（紐づく予約がある場合は拒否）"""
    cursor = conn.cursor()
    cursor.execute("SELECT seat_id FROM seats WHERE seat_id = ?", (seat_id,))
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Seat not found")

    cursor.execute(
        "SELECT COUNT(1) FROM reservations WHERE seat_id = ?", (seat_id,)
    )
    if cursor.fetchone()[0] > 0:
        raise HTTPException(
            status_code=400,
            detail="この座席には予約が存在するため削除できません",
        )

    cursor.execute("DELETE FROM seats WHERE seat_id = ?", (seat_id,))
    conn.commit()
    return None


# ---------------------------------------------------------------------------
# 空き座席検索
# ---------------------------------------------------------------------------

@app.get("/api/availability", response_model=List[SeatRead])
def available_seats(
    start_datetime: datetime = Query(..., description="検索開始日時"),
    end_datetime: datetime   = Query(..., description="検索終了日時"),
    floor_id: Optional[int]  = Query(None, description="フロアIDで絞り込み"),
    conn: pyodbc.Connection  = Depends(get_connection),
):
    """指定した時間帯に予約可能な座席一覧を取得する"""
    assert_time_range(start_datetime, end_datetime)

    query = """
        SELECT seat_id, floor_id, seat_name, status, is_active,
               created_at, updated_at, seat_type, capacity, has_monitor
        FROM seats
        WHERE is_active = 1
          AND seat_id NOT IN (
              SELECT seat_id
              FROM reservations
              WHERE status NOT IN ('cancelled', 'expired', 'completed')
                AND NOT (end_datetime <= ? OR start_datetime >= ?)
          )
    """
    params: list = [start_datetime, end_datetime]

    if floor_id is not None:
        query += " AND floor_id = ?"
        params.append(floor_id)

    query += " ORDER BY floor_id, seat_id"

    cursor = conn.cursor()
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    return [SeatRead(**row_to_dict(cursor, row)) for row in rows]


# ---------------------------------------------------------------------------
# 予約 API
# ---------------------------------------------------------------------------

@app.get("/api/reservations", response_model=List[ReservationRead])
def list_reservations(
    conn: pyodbc.Connection = Depends(get_connection),
):
    """予約一覧を開始日時の昇順で取得する"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT reservation_id, seat_id, user_id, outlook_event_id,
               start_datetime, end_datetime, status, notified_at,
               created_at, updated_at
        FROM reservations
        ORDER BY start_datetime
        """
    )
    rows = cursor.fetchall()
    return [ReservationRead(**row_to_dict(cursor, row)) for row in rows]


@app.get("/api/reservations/{reservation_id}", response_model=ReservationRead)
def get_reservation(
    reservation_id: int,
    conn: pyodbc.Connection = Depends(get_connection),
):
    """指定 reservation_id の予約を取得する"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT reservation_id, seat_id, user_id, outlook_event_id,
               start_datetime, end_datetime, status, notified_at,
               created_at, updated_at
        FROM reservations
        WHERE reservation_id = ?
        """,
        (reservation_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return ReservationRead(**row_to_dict(cursor, row))


@app.post("/api/reservations", response_model=ReservationRead, status_code=201)
def create_reservation(
    payload: ReservationCreate,
    conn: pyodbc.Connection = Depends(get_connection),
):
    """新規予約を作成する"""
    assert_time_range(payload.start_datetime, payload.end_datetime)
    assert_reservation_status(payload.status)

    cursor = conn.cursor()

    # 座席の存在確認
    cursor.execute(
        "SELECT seat_id FROM seats WHERE seat_id = ? AND is_active = 1",
        (payload.seat_id,),
    )
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Seat not found or inactive")

    # 重複チェック
    if is_overlapping(conn, payload.seat_id, payload.start_datetime, payload.end_datetime):
        raise HTTPException(
            status_code=409,
            detail="指定した時間帯はすでに予約済みです",
        )

    try:
        cursor.execute(
            """
            INSERT INTO reservations
                (seat_id, user_id, outlook_event_id,
                 start_datetime, end_datetime, status,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, GETDATE(), GETDATE());
            SELECT SCOPE_IDENTITY() AS new_id;
            """,
            (
                payload.seat_id,
                payload.user_id,
                payload.outlook_event_id,
                payload.start_datetime,
                payload.end_datetime,
                payload.status,
            ),
        )
        cursor.nextset()
        new_id = int(cursor.fetchone()[0])
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    cursor.execute(
        """
        SELECT reservation_id, seat_id, user_id, outlook_event_id,
               start_datetime, end_datetime, status, notified_at,
               created_at, updated_at
        FROM reservations WHERE reservation_id = ?
        """,
        (new_id,),
    )
    return ReservationRead(**row_to_dict(cursor, cursor.fetchone()))


@app.put("/api/reservations/{reservation_id}", response_model=ReservationRead)
def update_reservation(
    reservation_id: int,
    payload: ReservationUpdate,
    conn: pyodbc.Connection = Depends(get_connection),
):
    """指定 reservation_id の予約を更新する"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT reservation_id, seat_id, user_id, outlook_event_id,
               start_datetime, end_datetime, status, notified_at,
               created_at, updated_at
        FROM reservations WHERE reservation_id = ?
        """,
        (reservation_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    current     = row_to_dict(cursor, row)
    update_data = payload.dict(exclude_unset=True)
    current.update(update_data)

    start: datetime = current["start_datetime"]
    end: datetime   = current["end_datetime"]

    assert_time_range(start, end)

    if "status" in update_data:
        assert_reservation_status(current["status"])

    # 座席の存在確認
    cursor.execute(
        "SELECT seat_id FROM seats WHERE seat_id = ? AND is_active = 1",
        (current["seat_id"],),
    )
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Seat not found or inactive")

    # 重複チェック（自分自身を除外）
    if is_overlapping(
        conn,
        current["seat_id"],
        start,
        end,
        exclude_reservation_id=reservation_id,
    ):
        raise HTTPException(
            status_code=409,
            detail="指定した時間帯はすでに予約済みです",
        )

    cursor.execute(
        """
        UPDATE reservations
        SET seat_id          = ?,
            user_id          = ?,
            outlook_event_id = ?,
            start_datetime   = ?,
            end_datetime     = ?,
            status           = ?,
            updated_at       = GETDATE()
        WHERE reservation_id = ?
        """,
        (
            current["seat_id"],
            current["user_id"],
            current["outlook_event_id"],
            start,
            end,
            current["status"],
            reservation_id,
        ),
    )
    conn.commit()

    cursor.execute(
        """
        SELECT reservation_id, seat_id, user_id, outlook_event_id,
               start_datetime, end_datetime, status, notified_at,
               created_at, updated_at
        FROM reservations WHERE reservation_id = ?
        """,
        (reservation_id,),
    )
    return ReservationRead(**row_to_dict(cursor, cursor.fetchone()))


@app.delete("/api/reservations/{reservation_id}", status_code=204)
def delete_reservation(
    reservation_id: int,
    conn: pyodbc.Connection = Depends(get_connection),
):
    """指定 reservation_id の予約を削除する"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT reservation_id FROM reservations WHERE reservation_id = ?",
        (reservation_id,),
    )
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    cursor.execute(
        "DELETE FROM reservations WHERE reservation_id = ?", (reservation_id,)
    )
    conn.commit()
    return None


# ---------------------------------------------------------------------------
# Power Automate 連携
# ---------------------------------------------------------------------------

import requests as http_requests

POWER_AUTOMATE_CANCEL_URL: str = os.getenv("POWER_AUTOMATE_CANCEL_URL", "")


@app.post("/api/reservations/sync", response_model=ReservationRead, status_code=201)
def sync_outlook_reservation(
    payload: OutlookReservationSync,
    conn: pyodbc.Connection = Depends(get_connection),
):
    """Power Automate から Outlook 予約データを受信して保存する"""
    assert_time_range(payload.start_datetime, payload.end_datetime)

    cursor = conn.cursor()

    # 座席の存在確認
    cursor.execute(
        "SELECT seat_id FROM seats WHERE seat_id = ? AND is_active = 1",
        (payload.seat_id,),
    )
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Seat not found or inactive")

    # outlook_event_id で既存予約を検索（更新 or 新規）
    cursor.execute(
        "SELECT reservation_id FROM reservations WHERE outlook_event_id = ?",
        (payload.outlook_event_id,),
    )
    existing = cursor.fetchone()

    if existing is not None:
        # 既存予約を更新
        reservation_id = existing[0]
        cursor.execute(
            """
            UPDATE reservations
            SET seat_id        = ?,
                user_id        = ?,
                start_datetime = ?,
                end_datetime   = ?,
                status         = 'reserved',
                updated_at     = GETDATE()
            WHERE reservation_id = ?
            """,
            (
                payload.seat_id,
                payload.user_id,
                payload.start_datetime,
                payload.end_datetime,
                reservation_id,
            ),
        )
        conn.commit()
    else:
        # 重複チェック（新規作成時のみ）
        if is_overlapping(
            conn, payload.seat_id, payload.start_datetime, payload.end_datetime
        ):
            raise HTTPException(
                status_code=409,
                detail="指定した時間帯はすでに予約済みです",
            )

        cursor.execute(
            """
            INSERT INTO reservations
                (seat_id, user_id, outlook_event_id,
                 start_datetime, end_datetime, status,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'reserved', GETDATE(), GETDATE());
            SELECT SCOPE_IDENTITY() AS new_id;
            """,
            (
                payload.seat_id,
                payload.user_id,
                payload.outlook_event_id,
                payload.start_datetime,
                payload.end_datetime,
            ),
        )
        cursor.nextset()
        reservation_id = int(cursor.fetchone()[0])
        conn.commit()

    cursor.execute(
        """
        SELECT reservation_id, seat_id, user_id, outlook_event_id,
               start_datetime, end_datetime, status, notified_at,
               created_at, updated_at
        FROM reservations WHERE reservation_id = ?
        """,
        (reservation_id,),
    )
    return ReservationRead(**row_to_dict(cursor, cursor.fetchone()))


@app.post("/api/reservations/cancel/{reservation_id}", response_model=CancelResponse)
def cancel_reservation_by_id(
    reservation_id: int,
    conn: pyodbc.Connection = Depends(get_connection),
):
    """予約をキャンセルし、Power Automate 経由で Outlook 予定を削除する"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT reservation_id, seat_id, user_id, outlook_event_id
        FROM reservations WHERE reservation_id = ?
        """,
        (reservation_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    reservation = row_to_dict(cursor, row)

    cursor.execute(
        """
        UPDATE reservations
        SET status     = 'cancelled',
            updated_at = GETDATE()
        WHERE reservation_id = ?
        """,
        (reservation_id,),
    )
    conn.commit()

    # Power Automate へ通知（失敗しても処理続行）
    if POWER_AUTOMATE_CANCEL_URL:
        try:
            http_requests.post(
                POWER_AUTOMATE_CANCEL_URL,
                json={
                    "reservation_id"  : reservation_id,
                    "outlook_event_id": reservation.get("outlook_event_id", ""),
                },
                timeout=30,
            ).raise_for_status()
        except Exception as e:
            print(f"[PowerAutomate] 通知エラー（処理続行）: {e}")

    return CancelResponse(
        status="cancelled",
        reservation_id=reservation_id,
        message="予約をキャンセルしました",
    )


@app.post("/api/reservations/cancel/outlook", status_code=200)
def cancel_reservation_by_outlook(
    payload: dict,
    conn: pyodbc.Connection = Depends(get_connection),
):
    assert_time_range(payload.start_time, payload.end_time)
    cursor = conn.cursor()

    # seat_number から seat_id を取得
    cursor.execute(
        "SELECT seat_id FROM seats WHERE seat_name = ? AND is_active = 1",
        (payload.seat_number,),
    )
    seat = cursor.fetchone()
    if seat is None:
        raise HTTPException(
            status_code=404,
            detail=f"席番号 {payload.seat_number} が見つかりません"
        )
    seat_id = seat[0]

    # outlook_event_id で既存予約を検索
    cursor.execute(
        "SELECT * FROM reservations WHERE outlook_event_id = ?",
        (payload.outlook_event_id,),
    )
    existing = cursor.fetchone()

    if existing is None:
        # 新規作成
        if is_overlapping(conn, seat_id, payload.start_time, payload.end_time):
            raise HTTPException(
                status_code=409,
                detail="この時間帯はすでに予約されています"
            )
        cursor.execute(
            """
            INSERT INTO reservations
                (user_name, email, seat_id, start_time, end_time,
                 status, outlook_event_id)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            SELECT SCOPE_IDENTITY() AS id;
            """,
            (
                payload.user_name,
                payload.email,
                seat_id,
                payload.start_time,
                payload.end_time,
                "confirmed",
                payload.outlook_event_id,
            ),
        )
        cursor.nextset()
        reservation_id = int(cursor.fetchone()[0])
        conn.commit()

        return SyncResponse(
            action="created",
            reservation_id=reservation_id,
            outlook_event_id=payload.outlook_event_id,
        )

    else:
        # 既存予約を更新
        existing_dict = row_to_dict(cursor, existing)
        reservation_id = existing_dict["id"]

        cursor.execute(
            """
            UPDATE reservations
            SET user_name  = ?,
                email      = ?,
                seat_id    = ?,
                start_time = ?,
                end_time   = ?,
                status     = ?
            WHERE outlook_event_id = ?
            """,
            (
                payload.user_name,
                payload.email,
                seat_id,
                payload.start_time,
                payload.end_time,
                "confirmed",
                payload.outlook_event_id,
            ),
        )
        conn.commit()

        return SyncResponse(
            action="updated",
            reservation_id=reservation_id,
            outlook_event_id=payload.outlook_event_id,
        )


@app.delete("/api/reservations/cancel", status_code=200)
def cancel_reservation(
    payload: OutlookCancelPayload,
    conn: pyodbc.Connection = Depends(get_connection),
):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT reservation_id FROM reservations WHERE outlook_event_id = ?",
        (outlook_event_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="該当する予約が見つかりません")

    reservation_id = row[0]
    cursor.execute(
        """
        UPDATE reservations
        SET status     = 'cancelled',
            updated_at = GETDATE()
        WHERE reservation_id = ?
        """,
        (reservation_id,),
    )
    conn.commit()

    return {
        "action"          : "cancelled",
        "reservation_id"  : reservation_id,
        "outlook_event_id": outlook_event_id,
    }