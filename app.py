# Python 3.10以前でも `X | Y` 型ヒント構文を使えるようにする将来互換インポート
from __future__ import annotations

# OSの環境変数を取得するための標準ライブラリ
import os

# 日時データを扱うための標準ライブラリ
from datetime import datetime

# ファイルパスをオブジェクト指向で扱うための標準ライブラリ
from pathlib import Path

# 型ヒント用: ジェネレータ・リスト・Optional型のサポート
from typing import Iterator, List, Optional

# PostgreSQL接続ライブラリ（pip install psycopg2-binary）
import psycopg2

# psycopg2のカーソルをdict形式で返すためのファクトリ
from psycopg2.extras import RealDictCursor

# psycopg2のDB接続型（型ヒント用）
from psycopg2.extensions import connection as Psycopg2Connection

# FastAPI本体・依存性注入・HTTPエラー・クエリパラメータ
from fastapi import Depends, FastAPI, HTTPException, Query

# Pydanticのベースモデル・メール検証・フィールド定義
from pydantic import BaseModel, EmailStr, Field

# ---------------------------------------------------------------------------
# データベース接続設定
# ---------------------------------------------------------------------------

# 環境変数 DATABASE_URL からPostgreSQLの接続URLを取得する
# 未設定の場合はローカル開発用のデフォルト値を使用する
# 形式: postgresql://ユーザー名:パスワード@ホスト:ポート/DB名
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/akichance"
)

# ---------------------------------------------------------------------------
# FastAPIアプリケーションの初期化
# ---------------------------------------------------------------------------

# FastAPIインスタンスを生成し、APIのメタ情報を設定する
# title/description/versionはSwagger UI（/docs）に表示される
app = FastAPI(
    title="Akichance Reservation / Seat Management API",
    description="Reservation and seat management API for Akichance.",
    version="2.0.0",
)

# ---------------------------------------------------------------------------
# Pydanticモデル定義（座席）
# ---------------------------------------------------------------------------

# 座席データの共通フィールドを定義するベースモデル
class SeatBase(BaseModel):
    # 座席番号: 必須項目（...はPydanticで「必須」を意味する）
    seat_number: str = Field(..., description="Unique seat identifier")
    # エリア・ゾーン: 任意項目、未指定時はNone
    zone: Optional[str] = Field(None, description="Area or zone of the seat")
    # 有効フラグ: デフォルトTrue（予約受付中）
    is_active: bool = Field(True, description="Whether the seat is available for reservation")
    # 補足説明: 任意項目
    description: Optional[str] = None


# 座席作成時に使用するモデル（SeatBaseをそのまま継承）
class SeatCreate(SeatBase):
    pass


# 座席読み取り時に使用するモデル（DBのidフィールドを追加）
class SeatRead(SeatBase):
    # DBが自動採番するID
    id: int

    # Pydanticの設定クラス
    class Config:
        # ORMオブジェクトや辞書からの変換を許可する
        orm_mode = True


# 座席更新時に使用するモデル（全フィールドをOptionalにして部分更新に対応）
class SeatUpdate(BaseModel):
    # 更新対象フィールドは全て任意（指定されたフィールドのみ更新される）
    seat_number: Optional[str] = None
    zone: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Pydanticモデル定義（予約）
# ---------------------------------------------------------------------------

# 予約データの共通フィールドを定義するベースモデル
class ReservationBase(BaseModel):
    # 予約者名: 必須項目
    user_name: str = Field(..., description="Name of the user making the reservation")
    # メールアドレス: 必須項目（EmailStrでフォーマット自動バリデーション）
    email: EmailStr = Field(..., description="User email address")
    # 予約する座席のID: 必須項目
    seat_id: int = Field(..., description="Reserved seat ID")
    # 予約開始時刻: 必須項目
    start_time: datetime = Field(..., description="Reservation start time")
    # 予約終了時刻: 必須項目
    end_time: datetime = Field(..., description="Reservation end time")
    # 予約ステータス: デフォルトは"confirmed"（確定済み）
    status: str = Field("confirmed", description="Reservation status")


# 予約作成時に使用するモデル（ReservationBaseをそのまま継承）
class ReservationCreate(ReservationBase):
    pass


# 予約読み取り時に使用するモデル（DBのidフィールドを追加）
class ReservationRead(ReservationBase):
    # DBが自動採番するID
    id: int

    # Pydanticの設定クラス
    class Config:
        # ORMオブジェクトや辞書からの変換を許可する
        orm_mode = True


# 予約更新時に使用するモデル（全フィールドをOptionalにして部分更新に対応）
class ReservationUpdate(BaseModel):
    # 更新対象フィールドは全て任意（指定されたフィールドのみ更新される）
    user_name: Optional[str] = None
    email: Optional[EmailStr] = None
    seat_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None


# ---------------------------------------------------------------------------
# データベース接続・初期化
# ---------------------------------------------------------------------------

def get_connection() -> Iterator[Psycopg2Connection]:
    """
    PostgreSQLへの接続を生成し、FastAPIの依存性注入に提供するジェネレータ関数。
    yieldの前後でリクエストのライフサイクルに合わせた接続管理を行う。
    """
    # DATABASE_URLを使ってPostgreSQLに接続する
    # cursor_factory=RealDictCursorにより、カーソルの結果を辞書形式で取得できる
    connection = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

    try:
        # yieldで接続をエンドポイント関数に渡す（コンテキストマネージャ的な役割）
        yield connection
    finally:
        # リクエスト処理が完了（正常・例外問わず）したら必ず接続を閉じる
        connection.close()


def init_db() -> None:
    """
    アプリケーション起動時にDBテーブルを初期化する関数。
    テーブルが存在しない場合のみ作成する（既存データは保持される）。
    """
    # アプリ起動専用の接続を生成する（get_connectionとは別に直接接続）
    connection = psycopg2.connect(DATABASE_URL)

    # カーソルを生成してSQLを実行できる状態にする
    cursor = connection.cursor()

    # seatsテーブルが存在しない場合のみ作成する
    # PostgreSQLではSERIALで自動採番の整数型主キーを定義する（SQLiteのAUTOINCREMENTに相当）
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS seats (
            id          SERIAL PRIMARY KEY,
            seat_number TEXT NOT NULL UNIQUE,
            zone        TEXT,
            is_active   BOOLEAN NOT NULL DEFAULT TRUE,
            description TEXT
        )
        """
        # PostgreSQLはネイティブでBOOLEAN型をサポートするため、SQLite版の INTEGER(0/1) は不要
    )

    # reservationsテーブルが存在しない場合のみ作成する
    # PostgreSQLではTIMESTAMPWITH TIME ZONEで日時を直接扱える（SQLiteのTEXT保存と異なる）
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations (
            id         SERIAL PRIMARY KEY,
            user_name  TEXT NOT NULL,
            email      TEXT NOT NULL,
            seat_id    INTEGER NOT NULL,
            start_time TIMESTAMPTZ NOT NULL,
            end_time   TIMESTAMPTZ NOT NULL,
            status     TEXT NOT NULL,
            FOREIGN KEY (seat_id) REFERENCES seats(id)
        )
        """
        # TIMESTAMPTZはタイムゾーン情報付きのタイムスタンプ型
        # これによりisoformat()文字列への変換が不要になる
    )

    # 実行したSQLをDBに確定させる
    connection.commit()

    # 初期化専用の接続を閉じる
    connection.close()


# ---------------------------------------------------------------------------
# アプリケーションイベント
# ---------------------------------------------------------------------------

# FastAPIサーバーの起動時に自動で実行されるイベントハンドラ
@app.on_event("startup")
def startup_event() -> None:
    # DBテーブルの初期化処理を呼び出す
    init_db()


# ---------------------------------------------------------------------------
# ユーティリティ関数
# ---------------------------------------------------------------------------

def map_row_to_dict(row: dict) -> dict:
    """
    psycopg2のRealDictRowを通常のdictに変換する関数。
    Pydanticモデルへの渡し前に使用する。
    """
    # RealDictRowはdict互換だが、明示的にdictに変換して扱いやすくする
    return dict(row)


def assert_time_range(start_time: datetime, end_time: datetime) -> None:
    """
    終了時刻が開始時刻より後であることを検証する関数。
    不正な場合はHTTP 400エラーを送出する。
    """
    # 終了時刻が開始時刻以前の場合は不正な入力としてエラーを返す
    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")


def is_overlapping(
    conn: Psycopg2Connection,
    seat_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_id: Optional[int] = None,
) -> bool:
    """
    指定した座席・時間帯に重複する予約が存在するか確認する関数。
    exclude_idを指定すると、そのIDの予約を除外して判定する（更新時に自己除外するため）。
    """
    # 重複判定SQL: 既存予約の終了が新規開始より前 OR 既存開始が新規終了より後 → 重複なし
    # それ以外は重複あり（NOT条件の否定）
    query = """
        SELECT COUNT(1) AS count 
        FROM reservations 
        WHERE seat_id = %s 
          AND NOT (end_time <= %s OR start_time >= %s)
    """
    # SQLiteの?プレースホルダーと異なり、psycopg2では%sを使用する
    params: list = [seat_id, start_time, end_time]

    # 更新時など自分自身の予約を除外する場合はAND id != %sを追加
    if exclude_id is not None:
        query += " AND id != %s"
        params.append(exclude_id)

    # psycopg2ではカーソルを個別に生成してSQLを実行する
    with conn.cursor() as cursor:
        # SQLを実行する（paramsはタプルに変換して渡す）
        cursor.execute(query, tuple(params))
        # 結果を1行取得する
        result = cursor.fetchone()

    # countが1以上であれば重複ありとしてTrueを返す
    return result["count"] > 0


# ---------------------------------------------------------------------------
# 座席APIエンドポイント
# ---------------------------------------------------------------------------

# 座席一覧を取得するGETエンドポイント
@app.get("/api/seats", response_model=List[SeatRead])
def list_seats(
    # クエリパラメータ: ?active_only=true でアクティブな座席のみ取得
    active_only: bool = Query(False, description="Return only active seats"),
    # 依存性注入でPostgreSQL接続を受け取る
    conn: Psycopg2Connection = Depends(get_connection),
):
    # 基本クエリ（全件取得）
    query = "SELECT * FROM seats"

    # active_onlyがTrueの場合はWHERE句を追加してフィルタリングする
    if active_only:
        # PostgreSQLのBOOLEAN型はTRUE/FALSEで直接比較できる（SQLiteの1/0と異なる）
        query += " WHERE is_active = TRUE"

    # カーソルを生成してSQLを実行する
    with conn.cursor() as cursor:
        cursor.execute(query)
        # 全行を取得してリストにする
        rows = cursor.fetchall()

    # 各行をdictに変換してSeatReadモデルのリストとして返す
    return [SeatRead(**map_row_to_dict(row)) for row in rows]


# 新規座席を作成するPOSTエンドポイント（成功時201を返す）
@app.post("/api/seats", response_model=SeatRead, status_code=201)
def create_seat(
    # リクエストボディをSeatCreateモデルとして受け取る
    seat: SeatCreate,
    # 依存性注入でPostgreSQL接続を受け取る
    conn: Psycopg2Connection = Depends(get_connection),
):
    # カーソルを生成してINSERT文を実行する
    with conn.cursor() as cursor:
        # RETURNING idでINSERTした行のIDを取得する（PostgreSQL固有の便利な構文）
        # SQLiteではlastrowidを使う必要があったが、PostgreSQLではRETURNINGで直接取得できる
        cursor.execute(
            """
            INSERT INTO seats (seat_number, zone, is_active, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            # PostgreSQLはBOOLEAN型をそのまま受け取れるためint変換不要
            (seat.seat_number, seat.zone, seat.is_active, seat.description),
        )
        # INSERT直後のIDを取得する
        seat_id = cursor.fetchone()["id"]

    # INSERTした結果をDBに確定させる
    conn.commit()

    # 作成した座席を再取得してレスポンスとして返す
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM seats WHERE id = %s", (seat_id,))
        # 作成した1行を取得する
        row = cursor.fetchone()

    # 取得した行をSeatReadモデルに変換して返す
    return SeatRead(**map_row_to_dict(row))


# 指定IDの座席を取得するGETエンドポイント
@app.get("/api/seats/{seat_id}", response_model=SeatRead)
def get_seat(
    # パスパラメータとして座席IDを受け取る
    seat_id: int,
    # 依存性注入でPostgreSQL接続を受け取る
    conn: Psycopg2Connection = Depends(get_connection),
):
    # 指定IDの座席を検索する
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM seats WHERE id = %s", (seat_id,))
        row = cursor.fetchone()

    # 座席が存在しない場合は404エラーを返す
    if row is None:
        raise HTTPException(status_code=404, detail="Seat not found")

    # 取得した行をSeatReadモデルに変換して返す
    return SeatRead(**map_row_to_dict(row))


# 指定IDの座席を更新するPUTエンドポイント
@app.put("/api/seats/{seat_id}", response_model=SeatRead)
def update_seat(
    # パスパラメータとして座席IDを受け取る
    seat_id: int,
    # リクエストボディをSeatUpdateモデルとして受け取る
    payload: SeatUpdate,
    # 依存性注入でPostgreSQL接続を受け取る
    conn: Psycopg2Connection = Depends(get_connection),
):
    # 更新対象の座席が存在するか確認する
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM seats WHERE id = %s", (seat_id,))
        row = cursor.fetchone()

    # 座席が存在しない場合は404エラーを返す
    if row is None:
        raise HTTPException(status_code=404, detail="Seat not found")

    # 現在のDB値をdictとして取得する
    updated = map_row_to_dict(row)

    # リクエストで指定されたフィールドのみを取得する（未指定フィールドは除外）
    update_data = payload.dict(exclude_unset=True)

    # 現在のDB値に更新データを上書きする（部分更新）
    updated.update(update_data)

    # 更新SQLを実行する
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE seats 
            SET seat_number = %s, 
                zone        = %s, 
                is_active   = %s, 
                description = %s 
            WHERE id = %s
            """,
            # PostgreSQLはBOOLEAN型をそのまま受け取れるためint変換不要
            (
                updated["seat_number"],
                updated["zone"],
                updated["is_active"],
                updated["description"],
                seat_id,
            ),
        )

    # 更新内容をDBに確定させる
    conn.commit()

    # 更新後の座席データを再取得する
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM seats WHERE id = %s", (seat_id,))
        row = cursor.fetchone()

    # 取得した行をSeatReadモデルに変換して返す
    return SeatRead(**map_row_to_dict(row))


# 指定IDの座席を削除するDELETEエンドポイント（成功時204を返す）
@app.delete("/api/seats/{seat_id}", status_code=204)
def delete_seat(
    # パスパラメータとして座席IDを受け取る
    seat_id: int,
    # 依存性注入でPostgreSQL接続を受け取る
    conn: Psycopg2Connection = Depends(get_connection),
):
    # 削除対象の座席が存在するか確認する
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM seats WHERE id = %s", (seat_id,))
        # 座席が存在しない場合は404エラーを返す
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Seat not found")

    # その座席に紐づく予約が存在するか確認する
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(1) AS count FROM reservations WHERE seat_id = %s",
            (seat_id,),
        )
        # 予約が1件以上存在する場合は削除を拒否して400エラーを返す（データ整合性の保護）
        if cursor.fetchone()["count"] > 0:
            raise HTTPException(status_code=400, detail="Seat has existing reservations")

    # 座席を削除する
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM seats WHERE id = %s", (seat_id,))

    # 削除をDBに確定させる
    conn.commit()

    # 204 No Contentのレスポンスを返す（ボディなし）
    return None


# ---------------------------------------------------------------------------
# 空き座席検索エンドポイント
# ---------------------------------------------------------------------------

# 指定した時間帯に予約可能な座席一覧を取得するGETエンドポイント
@app.get("/api/availability", response_model=List[SeatRead])
def available_seats(
    # 検索開始時刻: 必須クエリパラメータ（...は必須を意味する）
    start_time: datetime = Query(...),
    # 検索終了時刻: 必須クエリパラメータ
    end_time: datetime = Query(...),
    # 依存性注入でPostgreSQL接続を受け取る
    conn: Psycopg2Connection = Depends(get_connection),
):
    # 終了時刻が開始時刻より後であることを検証する
    assert_time_range(start_time, end_time)

    # アクティブかつ指定時間帯に重複する予約のない座席を取得する
    # サブクエリで重複する予約のseat_idを取得し、NOT INで除外する
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM seats 
            WHERE is_active = TRUE 
              AND id NOT IN (
                  SELECT seat_id 
                  FROM reservations 
                  WHERE NOT (end_time <= %s OR start_time >= %s)
              )
            """,
            # PostgreSQLはdatetimeオブジェクトを直接渡せる（isoformat()変換不要）
            (start_time, end_time),
        )
        # 条件に合う全座席を取得する
        rows = cursor.fetchall()

    # 各行をSeatReadモデルに変換してリストとして返す
    return [SeatRead(**map_row_to_dict(row)) for row in rows]


# ---------------------------------------------------------------------------
# 予約APIエンドポイント
# ---------------------------------------------------------------------------

# 予約一覧を取得するGETエンドポイント
@app.get("/api/reservations", response_model=List[ReservationRead])
def list_reservations(
    # 依存性注入でPostgreSQL接続を受け取る
    conn: Psycopg2Connection = Depends(get_connection),
):
    # 全予約を開始時刻の昇順で取得する
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM reservations ORDER BY start_time")
        rows = cursor.fetchall()

    # 各行をReservationReadモデルに変換してリストとして返す
    return [ReservationRead(**map_row_to_dict(row)) for row in rows]


# 新規予約を作成するPOSTエンドポイント（成功時201を返す）
@app.post("/api/reservations", response_model=ReservationRead, status_code=201)
def create_reservation(
    # リクエストボディをReservationCreateモデルとして受け取る
    payload: ReservationCreate,
    # 依存性注入でPostgreSQL接続を受け取る
    conn: Psycopg2Connection = Depends(get_connection),
):
    # 終了時刻が開始時刻より後であることを検証する
    assert_time_range(payload.start_time, payload.end_time)

    # 指定された座席が存在し、かつアクティブ（予約受付中）であるか確認する
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM seats WHERE id = %s AND is_active = TRUE",
            (payload.seat_id,),
        )
        seat = cursor.fetchone()

    # 座席が存在しない、またはアクティブでない場合は404エラーを返す
    if seat is None:
        raise HTTPException(status_code=404, detail="Seat not found or inactive")

    # 指定した座席・時間帯に重複する予約が存在しないか確認する
    if is_overlapping(conn, payload.seat_id, payload.start_time, payload.end_time):
        # 重複する予約が存在する場合は409 Conflictエラーを返す
        raise HTTPException(
            status_code=409,
            detail="Seat is already reserved for the selected time range",
        )

    # 予約をDBに登録する
    with conn.cursor() as cursor:
        # RETURNING idでINSERTした行のIDを取得する（PostgreSQL固有の構文）
        cursor.execute(
            """
            INSERT INTO reservations 
                (user_name, email, seat_id, start_time, end_time, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            # PostgreSQLはdatetimeオブジェクトを直接渡せる（isoformat()変換不要）
            (
                payload.user_name,
                payload.email,
                payload.seat_id,
                payload.start_time,
                payload.end_time,
                payload.status,
            ),
        )
        # INSERT直後のIDを取得する
        reservation_id = cursor.fetchone()["id"]

    # 予約をDBに確定させる
    conn.commit()

    # 作成した予約を再取得してレスポンスとして返す
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM reservations WHERE id = %s", (reservation_id,)
        )
        row = cursor.fetchone()

    # 取得した行をReservationReadモデルに変換して返す
    return ReservationRead(**map_row_to_dict(row))


# 指定IDの予約を取得するGETエンドポイント
@app.get("/api/reservations/{reservation_id}", response_model=ReservationRead)
def get_reservation(
    # パスパラメータとして予約IDを受け取る
    reservation_id: int,
    # 依存性注入でPostgreSQL接続を受け取る
    conn: Psycopg2Connection = Depends(get_connection),
):
    # 指定IDの予約を検索する
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM reservations WHERE id = %s", (reservation_id,)
        )
        row = cursor.fetchone()

    # 予約が存在しない場合は404エラーを返す
    if row is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # 取得した行をReservationReadモデルに変換して返す
    return ReservationRead(**map_row_to_dict(row))


# 指定IDの予約を更新するPUTエンドポイント
@app.put("/api/reservations/{reservation_id}", response_model=ReservationRead)
def update_reservation(
    # パスパラメータとして予約IDを受け取る
    reservation_id: int,
    # リクエストボディをReservationUpdateモデルとして受け取る
    payload: ReservationUpdate,
    # 依存性注入でPostgreSQL接続を受け取る
    conn: Psycopg2Connection = Depends(get_connection),
):
    # 更新対象の予約が存在するか確認する
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM reservations WHERE id = %s", (reservation_id,)
        )
        row = cursor.fetchone()

    # 予約が存在しない場合は404エラーを返す
    if row is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # 現在のDB値をdictとして取得する
    reservation = map_row_to_dict(row)

    # リクエストで指定されたフィールドのみを取得する（未指定フィールドは除外）
    update_data = payload.dict(exclude_unset=True)

    # 現在のDB値に更新データを上書きする（部分更新）
    reservation.update(update_data)

    # PostgreSQLのTIMESTAMPTZ型はdatetimeオブジェクトとして返るため
    # SQLite版のようなisoformat()からの変換処理は不要
    # start_time / end_timeが確実にdatetimeオブジェクトであることを確認する
    start_time: datetime = reservation["start_time"]
    end_time: datetime = reservation["end_time"]

    # 終了時刻が開始時刻より後であることを検証する
    assert_time_range(start_time, end_time)

    # 更新後の座席が存在しアクティブであるか確認する
    if reservation.get("seat_id") is not None:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM seats WHERE id = %s AND is_active = TRUE",
                (reservation["seat_id"],),
            )
            seat = cursor.fetchone()
        # 座席が存在しない、またはアクティブでない場合は404エラーを返す
        if seat is None:
            raise HTTPException(status_code=404, detail="Seat not found or inactive")

    # 更新後の時間帯で重複する予約が存在しないか確認する（自身を除外して判定）
    if is_overlapping(
        conn,
        reservation["seat_id"],
        start_time,
        end_time,
        exclude_id=reservation_id,  # 自分自身の予約は重複チェックから除外する
    ):
        # 重複する予約が存在する場合は409 Conflictエラーを返す
        raise HTTPException(
            status_code=409,
            detail="Seat is already reserved for the selected time range",
        )

    # 更新SQLを実行する
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE reservations 
            SET user_name  = %s, 
                email      = %s, 
                seat_id    = %s, 
                start_time = %s, 
                end_time   = %s, 
                status     = %s 
            WHERE id = %s
            """,
            # PostgreSQLはdatetimeオブジェクトを直接渡せる（isoformat()変換不要）
            (
                reservation["user_name"],
                reservation["email"],
                reservation["seat_id"],
                start_time,
                end_time,
                reservation["status"],
                reservation_id,
            ),
        )

    # 更新内容をDBに確定させる
    conn.commit()

    # 更新後の予約データを再取得する
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM reservations WHERE id = %s", (reservation_id,)
        )
        row = cursor.fetchone()

    # 取得した行をReservationReadモデルに変換して返す
    return ReservationRead(**map_row_to_dict(row))


# 指定IDの予約を削除するDELETEエンドポイント（成功時204を返す）
@app.delete("/api/reservations/{reservation_id}", status_code=204)
def delete_reservation(
    # パスパラメータとして予約IDを受け取る
    reservation_id: int,
    # 依存性注入でPostgreSQL接続を受け取る
    conn: Psycopg2Connection = Depends(get_connection),
):
    # 削除対象の予約が存在するか確認する
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM reservations WHERE id = %s", (reservation_id,)
        )
        # 予約が存在しない場合は404エラーを返す
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Reservation not found")

    # 予約を削除する
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM reservations WHERE id = %s", (reservation_id,)
        )

    # 削除をDBに確定させる
    conn.commit()

    # 204 No Contentのレスポンスを返す（ボディなし）
    return None