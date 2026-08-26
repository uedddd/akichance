from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List

from database import get_db
from models import Seat
from schemas import SeatResponse, StatusUpdateRequest

app = FastAPI(title="AkiChance API", version="0.1.0")

# -----------------------------------------------
# ヘルスチェック
# 「APIが動いているか確認する」ためのエンドポイント
# -----------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# -----------------------------------------------
# 全席取得
# floor_id を指定すると絞り込める
# 例：/seats?floor_id=1
# -----------------------------------------------
@app.get("/seats", response_model=List[SeatResponse])
def get_seats(floor_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Seat).filter(Seat.is_active == True)
    if floor_id:
        query = query.filter(Seat.floor_id == floor_id)
    return query.all()

# -----------------------------------------------
# 1席取得
# 例：/seats/2 → seat_id=2の席を返す
# -----------------------------------------------
@app.get("/seats/{seat_id}", response_model=SeatResponse)
def get_seat(seat_id: int, db: Session = Depends(get_db)):
    seat = db.query(Seat).filter(Seat.seat_id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="席が見つかりません")
    return seat

# -----------------------------------------------
# ステータス更新
# 例：/seats/2/status に {"status": "in_use"} を送る
# -----------------------------------------------
@app.patch("/seats/{seat_id}/status")
def update_status(
    seat_id: int,
    body: StatusUpdateRequest,
    db: Session = Depends(get_db)
):
    # empty / in_use / reserved 以外はエラー
    if body.status not in {"empty", "in_use", "reserved"}:
        raise HTTPException(
            status_code=400,
            detail="statusはempty/in_use/reservedのいずれかにしてください"
        )

    seat = db.query(Seat).filter(Seat.seat_id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="席が見つかりません")

    seat.status     = body.status
    seat.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(seat)

    return {
        "seat_id"   : seat.seat_id,
        "seat_name" : seat.seat_name,
        "status"    : seat.status,
        "updated_at": seat.updated_at
    }

# -----------------------------------------------
# トグル（ボタン1つで切替）
# empty → in_use
# in_use → empty
# -----------------------------------------------
@app.patch("/seats/{seat_id}/toggle")
def toggle_status(
    seat_id: int,
    db: Session = Depends(get_db)
):
    seat = db.query(Seat).filter(Seat.seat_id == seat_id).first()
    if not seat:
        raise HTTPException(status_code=404, detail="席が見つかりません")

    # トグルロジック
    if seat.status == "empty":
        seat.status = "in_use"
    else:
        seat.status = "empty"

    seat.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(seat)

    return {
        "seat_id"   : seat.seat_id,
        "seat_name" : seat.seat_name,
        "status"    : seat.status,
        "updated_at": seat.updated_at
    }