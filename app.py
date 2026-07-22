# ============================================================
# Windows 用セットアップ手順
# ============================================================
# 
# 1. ODBC Driver 18 for SQL Server のインストール (Windows)
#    - https://learn.microsoft.com/ja-jp/sql/connect/odbc/download-odbc-driver-for-sql-server
#    から ODBC Driver 18 for SQL Server をダウンロードしてインストール
#    または以下のコマンドで winget を使用してインストール:
#    winget install Microsoft.ODBCDriver18forSQLServer
#
# 2. Python ライブラリのインストール
#    pip install -r requirements.txt
#
# 3. 環境変数の設定（.env ファイル作成または OS の環境変数に設定）
#    AZURE_SQL_SERVER=akichanceserver.database.windows.net
#    AZURE_SQL_DATABASE=akichanceDB
#    AZURE_SQL_USERNAME=g735218@mytecno23.onmicrosoft.com
#    AZURE_SQL_PASSWORD=your-actual-password
#
# ============================================================
# Python 3.10以前でも `X | Y` 型ヒント構文を使えるようにする将来互換インポート
from __future__ import annotations

# OSの環境変数を取得するための標準ライブラリ
import os
from pathlib import Path

# .env ファイルを読み込むためのライブラリ
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# 日時データを扱うための標準ライブラリ
from datetime import datetime

# 文字列をバイナリへ変換して Azure SQL の Entra トークンを送るための標準ライブラリ
import struct

# 型ヒント用: ジェネレータ・リスト・Optional型のサポート
from typing import Iterator, List, Optional

# SQL Server / Azure SQL への接続ライブラリ（pip install pyodbc）
import pyodbc

# Azure Entra ID 認証（サービスプリンシパル）
from azure.identity import ClientSecretCredential

# .env ファイルを読み込む
env_file = Path(__file__).parent / ".env"
if env_file.exists() and load_dotenv is not None:
    load_dotenv(env_file)

# FastAPI本体・依存性注入・HTTPエラー・クエリパラメータ
from fastapi import Depends, FastAPI, HTTPException, Query

# Pydanticのベースモデル・メール検証・フィールド定義
from pydantic import BaseModel, EmailStr, Field

# ---------------------------------------------------------------------------
# データベース接続設定
# ---------------------------------------------------------------------------

# Azure SQL Serverのホスト名を環境変数から取得する
# 形式: <サーバー名>.database.windows.net
AZURE_SQL_SERVER: str = os.getenv("AZURE_SQL_SERVER", "akichanceserver.database.windows.net")

# 接続先のデータベース名を環境変数から取得する
AZURE_SQL_DATABASE: str = os.getenv("AZURE_SQL_DATABASE", "akichanceDB")  

# Azure SQL のサービスプリンシパル認証設定
AZURE_CLIENT_ID: str = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET: str = os.getenv("AZURE_CLIENT_SECRET", "")
AZURE_TENANT_ID: str = os.getenv("AZURE_TENANT_ID", "")

# 使用するODBCドライバー名を環境変数から取得する
# Azure環境では "ODBC Driver 18 for SQL Server" が推奨される
AZURE_SQL_DRIVER: str = os.getenv("AZURE_SQL_DRIVER", "ODBC Driver 18 for SQL Server")

# 接続文字列の共通部分を生成する
CONNECTION_STRING: str = (
    f"DRIVER={{{AZURE_SQL_DRIVER}}};"
    f"SERVER={AZURE_SQL_SERVER};"
    f"DATABASE={AZURE_SQL_DATABASE};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)


def get_token_struct() -> bytes:
    """
    Azure SQL へ Service Principal 認証で接続するためのアクセストークンを
    pyodbc の attrs_before 形式に変換して返す。
    """
    if not all([AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID]):
        raise RuntimeError(
            "AZURE_CLIENT_ID / AZURE_CLIENT_SECRET / AZURE_TENANT_ID が設定されていません"
        )

    credential = ClientSecretCredential(
        tenant_id=AZURE_TENANT_ID,
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET,
    )

    token = credential.get_token("https://database.windows.net/.default")
    token_bytes = token.token.encode("utf-16-le")
    return struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)


def open_connection() -> pyodbc.Connection:
    """
    Azure SQL へ接続する pyodbc コネクションを生成する。
    """
    return pyodbc.connect(CONNECTION_STRING, attrs_before={1256: get_token_struct()})

# ---------------------------------------------------------------------------
# FastAPIアプリケーションの初期化
# ---------------------------------------------------------------------------

# FastAPIインスタンスを生成し、APIのメタ情報を設定する
# title/description/versionはSwagger UI（/docs）に表示される
app = FastAPI(
    title="Akichance Reservation / Seat Management API",
    description="Reservation and seat management API for Akichance. (Azure SQL)",
    version="3.0.0",
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

def get_connection() -> Iterator[pyodbc.Connection]:
    """
    Azure SQLへの接続を生成し、FastAPIの依存性注入に提供するジェネレータ関数。
    yieldの前後でリクエストのライフサイクルに合わせた接続管理を行う。
    """
    # Entra 認証済みトークンをつけて Azure SQL に接続する
    connection = open_connection()

    # pyodbc はデフォルトで自動コミットが無効のため明示的に無効化を宣言する
    # これによりcommit()/rollback()で手動トランザクション管理が可能になる
    connection.autocommit = False

    try:
        # yieldで接続をエンドポイント関数に渡す（コンテキストマネージャ的な役割）
        yield connection
    except Exception:
        # 例外が発生した場合はロールバックしてDBの整合性を保つ
        connection.rollback()
        # 例外を再送出して FastAPI のエラーハンドラに処理を委譲する
        raise
    finally:
        # リクエスト処理が完了（正常・例外問わず）したら必ず接続を閉じる
        connection.close()


def row_to_dict(cursor: pyodbc.Cursor, row: pyodbc.Row) -> dict:
    """
    pyodbcのRowオブジェクトをdictに変換するユーティリティ関数。
    pyodbcはRealDictCursorのような自動dict変換機能を持たないため、
    カーソルのdescriptionからカラム名を取得して辞書を生成する。
    """
    # cursor.descriptionは[(カラム名, 型, ...), ...]の形式で返る
    # index 0 がカラム名なので、それをキーとしてrowの値と対応させる
    columns = [column[0] for column in cursor.description]

    # カラム名と値をzipで対応させてdictを生成する
    return dict(zip(columns, row))


def init_db() -> None:
    """
    アプリケーション起動時にDBテーブルを初期化する関数。
    テーブルが存在しない場合のみ作成する（既存データは保持される）。
    ただし、サービスプリンシパルにCREATE TABLE権限がない場合は
    起動時エラーにせず警告のみで続行する。
    """
    # アプリ起動専用の接続を生成する（get_connectionとは別に直接接続）
    connection = open_connection()

    # DDL文は自動コミットモードで実行する必要がある
    # Azure SQL ではCREATE TABLEなどのDDLはトランザクション外で実行することが推奨される
    connection.autocommit = True

    # カーソルを生成してSQLを実行できる状態にする
    cursor = connection.cursor()

    try:
        # seatsテーブルが存在しない場合のみ作成する
        # Azure SQL(T-SQL)ではIF NOT EXISTS構文がないため
        # INFORMATION_SCHEMA.TABLESを使ってテーブルの存在確認を行う
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'seats'
            )
            BEGIN
                CREATE TABLE seats (
                    id          INT IDENTITY(1,1) PRIMARY KEY,
                    seat_number NVARCHAR(100) NOT NULL UNIQUE,
                    zone        NVARCHAR(100),
                    is_active   BIT NOT NULL DEFAULT 1,
                    description NVARCHAR(MAX)
                )
            END
            """
            # IDENTITY(1,1)  : 1から始まり1ずつ増加する自動採番（PostgreSQLのSERIALに相当）
            # NVARCHAR       : Unicodeに対応した可変長文字列型（日本語対応）
            # BIT            : 0/1の2値型（PostgreSQLのBOOLEAN、SQLiteのINTEGERに相当）
            # NVARCHAR(MAX)  : 最大2GBまで格納できる大容量文字列型
        )

        # reservationsテーブルが存在しない場合のみ作成する
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1 FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'reservations'
            )
            BEGIN
                CREATE TABLE reservations (
                    id         INT IDENTITY(1,1) PRIMARY KEY,
                    user_name  NVARCHAR(200) NOT NULL,
                    email      NVARCHAR(254) NOT NULL,
                    seat_id    INT NOT NULL,
                    start_time DATETIME2 NOT NULL,
                    end_time   DATETIME2 NOT NULL,
                    status     NVARCHAR(50) NOT NULL,
                    FOREIGN KEY (seat_id) REFERENCES seats(id)
                )
            END
            """
            # DATETIME2: T-SQLの高精度日時型（タイムゾーンなし、精度は最大100ナノ秒）
            # タイムゾーン付きで保存する場合はDATETIMEOFFSETを使用する
            # email用のNVARCHAR(254)はRFC 5321のメールアドレス最大長に準拠
        )
    except pyodbc.ProgrammingError as exc:
        message = str(exc)
        if "CREATE TABLE permission denied" in message or "permission denied in database" in message:
            print(
                "WARNING: Azure SQL user does not have CREATE TABLE permission. "
                "Skipping schema initialization."
            )
        else:
            raise
    finally:
        # DDL自動コミットモードのため明示的なcommitは不要だが、接続を閉じる
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

def assert_time_range(start_time: datetime, end_time: datetime) -> None:
    """
    終了時刻が開始時刻より後であることを検証する関数。
    不正な場合はHTTP 400エラーを送出する。
    """
    # 終了時刻が開始時刻以前の場合は不正な入力としてエラーを返す
    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")


def is_overlapping(
    conn: pyodbc.Connection,
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
    # pyodbcのプレースホルダーは ? を使用する（psycopg2の%sと異なる）
    query = """
        SELECT COUNT(1) AS cnt
        FROM reservations
        WHERE seat_id = ?
          AND NOT (end_time <= ? OR start_time >= ?)
    """
    # プレースホルダーに対応するパラメータリストを作成する
    params: list = [seat_id, start_time, end_time]

    # 更新時など自分自身の予約を除外する場合はAND id != ?を追加する
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)

    # カーソルを生成してSQLを実行する
    cursor = conn.cursor()
    cursor.execute(query, tuple(params))

    # 結果を1行取得する
    row = cursor.fetchone()

    # T-SQLではCOUNT結果のカラム名エイリアスがrow_to_dictなしでも
    # インデックスでアクセス可能なため、ここではインデックス0で取得する
    return row[0] > 0


# ---------------------------------------------------------------------------
# 座席APIエンドポイント
# ---------------------------------------------------------------------------

# 座席一覧を取得するGETエンドポイント
@app.get("/api/seats", response_model=List[SeatRead])
def list_seats(
    # クエリパラメータ: ?active_only=true でアクティブな座席のみ取得
    active_only: bool = Query(False, description="Return only active seats"),
    # 依存性注入でAzure SQL接続を受け取る
    conn: pyodbc.Connection = Depends(get_connection),
):
    # 基本クエリ（全件取得）
    query = "SELECT * FROM seats"

    # active_onlyがTrueの場合はWHERE句を追加してフィルタリングする
    if active_only:
        # Azure SQL(T-SQL)のBIT型は1/0で比較する（PostgreSQLのTRUE/FALSEと異なる）
        query += " WHERE is_active = 1"

    # カーソルを生成してSQLを実行する
    cursor = conn.cursor()
    cursor.execute(query)

    # 全行を取得してdictのリストに変換する
    rows = cursor.fetchall()

    # 各行をrow_to_dictでdict化してSeatReadモデルに変換し、リストとして返す
    return [SeatRead(**row_to_dict(cursor, row)) for row in rows]


# 新規座席を作成するPOSTエンドポイント（成功時201を返す）
@app.post("/api/seats", response_model=SeatRead, status_code=201)
def create_seat(
    # リクエストボディをSeatCreateモデルとして受け取る
    seat: SeatCreate,
    # 依存性注入でAzure SQL接続を受け取る
    conn: pyodbc.Connection = Depends(get_connection),
):
    # カーソルを生成する
    cursor = conn.cursor()

    # INSERT文を実行する
    # T-SQLではRETURNING構文が使えないため、SCOPE_IDENTITY()でINSERT後のIDを取得する
    # SCOPE_IDENTITY()は現在のスコープで最後にINSERTされたIDENTITY値を返す
    cursor.execute(
        """
        INSERT INTO seats (seat_number, zone, is_active, description)
        VALUES (?, ?, ?, ?);
        SELECT SCOPE_IDENTITY() AS id;
        """,
        # BIT型のis_activeはPythonのboolをintに変換して渡す（True→1, False→0）
        (seat.seat_number, seat.zone, int(seat.is_active), seat.description),
    )

    # 複数のSQL文を実行した場合、nextset()で次の結果セットに移動する
    # ここではSELECT SCOPE_IDENTITY()の結果セットに移動する
    cursor.nextset()

    # SCOPE_IDENTITY()の結果からINSERTしたIDを取得する
    seat_id = int(cursor.fetchone()[0])

    # INSERTした結果をDBに確定させる
    conn.commit()

    # 作成した座席を再取得する
    cursor.execute("SELECT * FROM seats WHERE id = ?", (seat_id,))
    row = cursor.fetchone()

    # 取得した行をSeatReadモデルに変換して返す
    return SeatRead(**row_to_dict(cursor, row))


# 指定IDの座席を取得するGETエンドポイント
@app.get("/api/seats/{seat_id}", response_model=SeatRead)
def get_seat(
    # パスパラメータとして座席IDを受け取る
    seat_id: int,
    # 依存性注入でAzure SQL接続を受け取る
    conn: pyodbc.Connection = Depends(get_connection),
):
    # 指定IDの座席を検索する
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM seats WHERE id = ?", (seat_id,))
    row = cursor.fetchone()

    # 座席が存在しない場合は404エラーを返す
    if row is None:
        raise HTTPException(status_code=404, detail="Seat not found")

    # 取得した行をSeatReadモデルに変換して返す
    return SeatRead(**row_to_dict(cursor, row))


# 指定IDの座席を更新するPUTエンドポイント
@app.put("/api/seats/{seat_id}", response_model=SeatRead)
def update_seat(
    # パスパラメータとして座席IDを受け取る
    seat_id: int,
    # リクエストボディをSeatUpdateモデルとして受け取る
    payload: SeatUpdate,
    # 依存性注入でAzure SQL接続を受け取る
    conn: pyodbc.Connection = Depends(get_connection),
):
    # 更新対象の座席が存在するか確認する
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM seats WHERE id = ?", (seat_id,))
    row = cursor.fetchone()

    # 座席が存在しない場合は404エラーを返す
    if row is None:
        raise HTTPException(status_code=404, detail="Seat not found")

    # 現在のDB値をdictとして取得する
    updated = row_to_dict(cursor, row)

    # リクエストで指定されたフィールドのみを取得する（未指定フィールドは除外）
    update_data = payload.dict(exclude_unset=True)

    # 現在のDB値に更新データを上書きする（部分更新）
    updated.update(update_data)

    # 更新SQLを実行する
    cursor.execute(
        """
        UPDATE seats 
        SET seat_number = ?, 
            zone        = ?, 
            is_active   = ?, 
            description = ? 
        WHERE id = ?
        """,
        # BIT型のis_activeはintに変換して渡す（True→1, False→0）
        (
            updated["seat_number"],
            updated["zone"],
            int(updated["is_active"]),
            updated["description"],
            seat_id,
        ),
    )

    # 更新内容をDBに確定させる
    conn.commit()

    # 更新後の座席データを再取得する
    cursor.execute("SELECT * FROM seats WHERE id = ?", (seat_id,))
    row = cursor.fetchone()

    # 取得した行をSeatReadモデルに変換して返す
    return SeatRead(**row_to_dict(cursor, row))


# 指定IDの座席を削除するDELETEエンドポイント（成功時204を返す）
@app.delete("/api/seats/{seat_id}", status_code=204)
def delete_seat(
    # パスパラメータとして座席IDを受け取る
    seat_id: int,
    # 依存性注入でAzure SQL接続を受け取る
    conn: pyodbc.Connection = Depends(get_connection),
):
    # 削除対象の座席が存在するか確認する
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM seats WHERE id = ?", (seat_id,))

    # 座席が存在しない場合は404エラーを返す
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Seat not found")

    # その座席に紐づく予約が存在するか確認する
    cursor.execute(
        "SELECT COUNT(1) AS cnt FROM reservations WHERE seat_id = ?",
        (seat_id,),
    )
    # 予約が1件以上存在する場合は削除を拒否して400エラーを返す（データ整合性の保護）
    if cursor.fetchone()[0] > 0:
        raise HTTPException(status_code=400, detail="Seat has existing reservations")

    # 座席を削除する
    cursor.execute("DELETE FROM seats WHERE id = ?", (seat_id,))

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
    # 依存性注入でAzure SQL接続を受け取る
    conn: pyodbc.Connection = Depends(get_connection),
):
    # 終了時刻が開始時刻より後であることを検証する
    assert_time_range(start_time, end_time)

    # アクティブかつ指定時間帯に重複する予約のない座席を取得する
    # サブクエリで重複する予約のseat_idを取得し、NOT INで除外する
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM seats
        WHERE is_active = 1
          AND id NOT IN (
              SELECT seat_id
              FROM reservations
              WHERE NOT (end_time <= ? OR start_time >= ?)
          )
        """,
        # pyodbcはdatetimeオブジェクトを直接渡せる（isoformat()変換不要）
        (start_time, end_time),
    )

    # 条件に合う全座席を取得する
    rows = cursor.fetchall()

    # 各行をSeatReadモデルに変換してリストとして返す
    return [SeatRead(**row_to_dict(cursor, row)) for row in rows]


# ---------------------------------------------------------------------------
# 予約APIエンドポイント
# ---------------------------------------------------------------------------

# 予約一覧を取得するGETエンドポイント
@app.get("/api/reservations", response_model=List[ReservationRead])
def list_reservations(
    # 依存性注入でAzure SQL接続を受け取る
    conn: pyodbc.Connection = Depends(get_connection),
):
    # 全予約を開始時刻の昇順で取得する
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reservations ORDER BY start_time")
    rows = cursor.fetchall()

    # 各行をReservationReadモデルに変換してリストとして返す
    return [ReservationRead(**row_to_dict(cursor, row)) for row in rows]


# 新規予約を作成するPOSTエンドポイント（成功時201を返す）
@app.post("/api/reservations", response_model=ReservationRead, status_code=201)
def create_reservation(
    # リクエストボディをReservationCreateモデルとして受け取る
    payload: ReservationCreate,
    # 依存性注入でAzure SQL接続を受け取る
    conn: pyodbc.Connection = Depends(get_connection),
):
    # 終了時刻が開始時刻より後であることを検証する
    assert_time_range(payload.start_time, payload.end_time)

    # 指定された座席が存在し、かつアクティブ（予約受付中）であるか確認する
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM seats WHERE id = ? AND is_active = 1",
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
    # T-SQLではRETURNING構文が使えないためSCOPE_IDENTITY()でIDを取得する
    cursor.execute(
        """
        INSERT INTO reservations 
            (user_name, email, seat_id, start_time, end_time, status)
        VALUES (?, ?, ?, ?, ?, ?);
        SELECT SCOPE_IDENTITY() AS id;
        """,
        # pyodbcはdatetimeオブジェクトを直接渡せる（isoformat()変換不要）
        (
            payload.user_name,
            payload.email,
            payload.seat_id,
            payload.start_time,
            payload.end_time,
            payload.status,
        ),
    )

    # 次の結果セット（SCOPE_IDENTITY()の結果）に移動する
    cursor.nextset()

    # SCOPE_IDENTITY()の結果からINSERTしたIDを取得する
    reservation_id = int(cursor.fetchone()[0])

    # 予約をDBに確定させる
    conn.commit()

    # 作成した予約を再取得してレスポンスとして返す
    cursor.execute(
        "SELECT * FROM reservations WHERE id = ?", (reservation_id,)
    )
    row = cursor.fetchone()

    # 取得した行をReservationReadモデルに変換して返す
    return ReservationRead(**row_to_dict(cursor, row))


# 指定IDの予約を取得するGETエンドポイント
@app.get("/api/reservations/{reservation_id}", response_model=ReservationRead)
def get_reservation(
    # パスパラメータとして予約IDを受け取る
    reservation_id: int,
    # 依存性注入でAzure SQL接続を受け取る
    conn: pyodbc.Connection = Depends(get_connection),
):
    # 指定IDの予約を検索する
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM reservations WHERE id = ?", (reservation_id,)
    )
    row = cursor.fetchone()

    # 予約が存在しない場合は404エラーを返す
    if row is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # 取得した行をReservationReadモデルに変換して返す
    return ReservationRead(**row_to_dict(cursor, row))


# 指定IDの予約を更新するPUTエンドポイント
@app.put("/api/reservations/{reservation_id}", response_model=ReservationRead)
def update_reservation(
    # パスパラメータとして予約IDを受け取る
    reservation_id: int,
    # リクエストボディをReservationUpdateモデルとして受け取る
    payload: ReservationUpdate,
    # 依存性注入でAzure SQL接続を受け取る
    conn: pyodbc.Connection = Depends(get_connection),
):
    # 更新対象の予約が存在するか確認する
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM reservations WHERE id = ?", (reservation_id,)
    )
    row = cursor.fetchone()

    # 予約が存在しない場合は404エラーを返す
    if row is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # 現在のDB値をdictとして取得する
    reservation = row_to_dict(cursor, row)

    # リクエストで指定されたフィールドのみを取得する（未指定フィールドは除外）
    update_data = payload.dict(exclude_unset=True)

    # 現在のDB値に更新データを上書きする（部分更新）
    reservation.update(update_data)

    # DATETIME2型はdatetimeオブジェクトとして返るが、
    # 文字列として返る場合に備えてdatetimeへの変換を行う
    start_time: datetime = (
        datetime.fromisoformat(str(reservation["start_time"]))
        if not isinstance(reservation["start_time"], datetime)
        else reservation["start_time"]
    )
    end_time: datetime = (
        datetime.fromisoformat(str(reservation["end_time"]))
        if not isinstance(reservation["end_time"], datetime)
        else reservation["end_time"]
    )

    # 終了時刻が開始時刻より後であることを検証する
    assert_time_range(start_time, end_time)

    # 更新後の座席が存在しアクティブであるか確認する
    if reservation.get("seat_id") is not None:
        cursor.execute(
            "SELECT * FROM seats WHERE id = ? AND is_active = 1",
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
    cursor.execute(
        """
        UPDATE reservations
        SET user_name  = ?,
            email      = ?,
            seat_id    = ?,
            start_time = ?,
            end_time   = ?,
            status     = ?
        WHERE id = ?
        """,
        # pyodbcはdatetimeオブジェクトを直接渡せる（isoformat()変換不要）
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
    cursor.execute(
        "SELECT * FROM reservations WHERE id = ?", (reservation_id,)
    )
    row = cursor.fetchone()

    # 取得した行をReservationReadモデルに変換して返す
    return ReservationRead(**row_to_dict(cursor, row))


# 指定IDの予約を削除するDELETEエンドポイント（成功時204を返す）
@app.delete("/api/reservations/{reservation_id}", status_code=204)
def delete_reservation(
    # パスパラメータとして予約IDを受け取る
    reservation_id: int,
    # 依存性注入でAzure SQL接続を受け取る
    conn: pyodbc.Connection = Depends(get_connection),
):
    # 削除対象の予約が存在するか確認する
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM reservations WHERE id = ?", (reservation_id,)
    )
    # 予約が存在しない場合は404エラーを返す
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # 予約を削除する
    cursor.execute(
        "DELETE FROM reservations WHERE id = ?", (reservation_id,)
    )

    # 削除をDBに確定させる
    conn.commit()

    # 204 No Contentのレスポンスを返す（ボディなし）
    return None