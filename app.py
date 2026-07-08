from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

DB_PATH = Path(os.getenv("AKICHANCE_DB_PATH", Path(__file__).resolve().parent / "akichance.db"))

app = FastAPI(
    title="Akichance Reservation / Seat Management API",
    description="Reservation and seat management API for Akichance.",
    version="1.0.0",
)


class SeatBase(BaseModel):
    seat_number: str = Field(..., description="Unique seat identifier")
    zone: Optional[str] = Field(None, description="Area or zone of the seat")
    is_active: bool = Field(True, description="Whether the seat is available for reservation")
    description: Optional[str] = None


class SeatCreate(SeatBase):
    pass


class SeatRead(SeatBase):
    id: int

    class Config:
        orm_mode = True


class SeatUpdate(BaseModel):
    seat_number: Optional[str] = None
    zone: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class ReservationBase(BaseModel):
    user_name: str = Field(..., description="Name of the user making the reservation")
    email: EmailStr = Field(..., description="User email address")
    seat_id: int = Field(..., description="Reserved seat ID")
    start_time: datetime = Field(..., description="Reservation start time")
    end_time: datetime = Field(..., description="Reservation end time")
    status: str = Field("confirmed", description="Reservation status")


class ReservationCreate(ReservationBase):
    pass


class ReservationRead(ReservationBase):
    id: int

    class Config:
        orm_mode = True


class ReservationUpdate(BaseModel):
    user_name: Optional[str] = None
    email: Optional[EmailStr] = None
    seat_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()


def init_db() -> None:
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seat_number TEXT NOT NULL UNIQUE,
            zone TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            description TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            email TEXT NOT NULL,
            seat_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (seat_id) REFERENCES seats(id)
        )
        """
    )
    connection.commit()
    connection.close()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


def map_row_to_dict(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in row.keys()}


@app.get("/api/seats", response_model=List[SeatRead])
def list_seats(active_only: bool = Query(False, description="Return only active seats"), conn: sqlite3.Connection = Depends(get_connection)):
    query = "SELECT * FROM seats"
    params: tuple = ()
    if active_only:
        query += " WHERE is_active = 1"
    cursor = conn.execute(query, params)
    return [SeatRead(**map_row_to_dict(row)) for row in cursor.fetchall()]


@app.post("/api/seats", response_model=SeatRead, status_code=201)
def create_seat(seat: SeatCreate, conn: sqlite3.Connection = Depends(get_connection)):
    cursor = conn.execute(
        "INSERT INTO seats (seat_number, zone, is_active, description) VALUES (?, ?, ?, ?)",
        (seat.seat_number, seat.zone, int(seat.is_active), seat.description),
    )
    conn.commit()
    seat_id = cursor.lastrowid
    cursor = conn.execute("SELECT * FROM seats WHERE id = ?", (seat_id,))
    return SeatRead(**map_row_to_dict(cursor.fetchone()))


@app.get("/api/seats/{seat_id}", response_model=SeatRead)
def get_seat(seat_id: int, conn: sqlite3.Connection = Depends(get_connection)):
    cursor = conn.execute("SELECT * FROM seats WHERE id = ?", (seat_id,))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Seat not found")
    return SeatRead(**map_row_to_dict(row))


@app.put("/api/seats/{seat_id}", response_model=SeatRead)
def update_seat(seat_id: int, payload: SeatUpdate, conn: sqlite3.Connection = Depends(get_connection)):
    cursor = conn.execute("SELECT * FROM seats WHERE id = ?", (seat_id,))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Seat not found")
    updated = map_row_to_dict(row)
    update_data = payload.dict(exclude_unset=True)
    if "is_active" in update_data:
        update_data["is_active"] = int(update_data["is_active"])
    updated.update(update_data)
    conn.execute(
        "UPDATE seats SET seat_number = ?, zone = ?, is_active = ?, description = ? WHERE id = ?",
        (updated["seat_number"], updated["zone"], updated["is_active"], updated["description"], seat_id),
    )
    conn.commit()
    cursor = conn.execute("SELECT * FROM seats WHERE id = ?", (seat_id,))
    return SeatRead(**map_row_to_dict(cursor.fetchone()))


@app.delete("/api/seats/{seat_id}", status_code=204)
def delete_seat(seat_id: int, conn: sqlite3.Connection = Depends(get_connection)):
    cursor = conn.execute("SELECT * FROM seats WHERE id = ?", (seat_id,))
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Seat not found")
    cursor = conn.execute("SELECT COUNT(1) AS count FROM reservations WHERE seat_id = ?", (seat_id,))
    if cursor.fetchone()["count"] > 0:
        raise HTTPException(status_code=400, detail="Seat has existing reservations")
    conn.execute("DELETE FROM seats WHERE id = ?", (seat_id,))
    conn.commit()
    return None


def assert_time_range(start_time: datetime, end_time: datetime) -> None:
    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")


def is_overlapping(conn: sqlite3.Connection, seat_id: int, start_time: datetime, end_time: datetime, exclude_id: Optional[int] = None) -> bool:
    query = "SELECT COUNT(1) AS count FROM reservations WHERE seat_id = ? AND NOT (end_time <= ? OR start_time >= ?)"
    params = [seat_id, start_time.isoformat(), end_time.isoformat()]
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)
    cursor = conn.execute(query, tuple(params))
    return cursor.fetchone()["count"] > 0


@app.get("/api/availability", response_model=List[SeatRead])
def available_seats(start_time: datetime = Query(...), end_time: datetime = Query(...), conn: sqlite3.Connection = Depends(get_connection)):
    assert_time_range(start_time, end_time)
    cursor = conn.execute(
        "SELECT * FROM seats WHERE is_active = 1 AND id NOT IN (SELECT seat_id FROM reservations WHERE NOT (end_time <= ? OR start_time >= ?))",
        (start_time.isoformat(), end_time.isoformat()),
    )
    return [SeatRead(**map_row_to_dict(row)) for row in cursor.fetchall()]


@app.get("/api/reservations", response_model=List[ReservationRead])
def list_reservations(conn: sqlite3.Connection = Depends(get_connection)):
    cursor = conn.execute("SELECT * FROM reservations ORDER BY start_time")
    return [ReservationRead(**map_row_to_dict(row)) for row in cursor.fetchall()]


@app.post("/api/reservations", response_model=ReservationRead, status_code=201)
def create_reservation(payload: ReservationCreate, conn: sqlite3.Connection = Depends(get_connection)):
    assert_time_range(payload.start_time, payload.end_time)
    seat = conn.execute("SELECT * FROM seats WHERE id = ? AND is_active = 1", (payload.seat_id,)).fetchone()
    if seat is None:
        raise HTTPException(status_code=404, detail="Seat not found or inactive")
    if is_overlapping(conn, payload.seat_id, payload.start_time, payload.end_time):
        raise HTTPException(status_code=409, detail="Seat is already reserved for the selected time range")
    cursor = conn.execute(
        "INSERT INTO reservations (user_name, email, seat_id, start_time, end_time, status) VALUES (?, ?, ?, ?, ?, ?)",
        (
            payload.user_name,
            payload.email,
            payload.seat_id,
            payload.start_time.isoformat(),
            payload.end_time.isoformat(),
            payload.status,
        ),
    )
    conn.commit()
    reservation_id = cursor.lastrowid
    cursor = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,))
    return ReservationRead(**map_row_to_dict(cursor.fetchone()))


@app.get("/api/reservations/{reservation_id}", response_model=ReservationRead)
def get_reservation(reservation_id: int, conn: sqlite3.Connection = Depends(get_connection)):
    cursor = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return ReservationRead(**map_row_to_dict(row))


@app.put("/api/reservations/{reservation_id}", response_model=ReservationRead)
def update_reservation(reservation_id: int, payload: ReservationUpdate, conn: sqlite3.Connection = Depends(get_connection)):
    cursor = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,))
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    reservation = map_row_to_dict(row)
    update_data = payload.dict(exclude_unset=True)
    reservation.update(update_data)
    if reservation.get("start_time"):
        reservation["start_time"] = datetime.fromisoformat(reservation["start_time"]) if isinstance(reservation["start_time"], str) else reservation["start_time"]
    if reservation.get("end_time"):
        reservation["end_time"] = datetime.fromisoformat(reservation["end_time"]) if isinstance(reservation["end_time"], str) else reservation["end_time"]
    assert_time_range(reservation["start_time"], reservation["end_time"])
    if reservation.get("seat_id") is not None:
        seat = conn.execute("SELECT * FROM seats WHERE id = ? AND is_active = 1", (reservation["seat_id"],)).fetchone()
        if seat is None:
            raise HTTPException(status_code=404, detail="Seat not found or inactive")
    if is_overlapping(conn, reservation["seat_id"], reservation["start_time"], reservation["end_time"], exclude_id=reservation_id):
        raise HTTPException(status_code=409, detail="Seat is already reserved for the selected time range")
    conn.execute(
        "UPDATE reservations SET user_name = ?, email = ?, seat_id = ?, start_time = ?, end_time = ?, status = ? WHERE id = ?",
        (
            reservation["user_name"],
            reservation["email"],
            reservation["seat_id"],
            reservation["start_time"].isoformat(),
            reservation["end_time"].isoformat(),
            reservation["status"],
            reservation_id,
        ),
    )
    conn.commit()
    cursor = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,))
    return ReservationRead(**map_row_to_dict(cursor.fetchone()))


@app.delete("/api/reservations/{reservation_id}", status_code=204)
def delete_reservation(reservation_id: int, conn: sqlite3.Connection = Depends(get_connection)):
    cursor = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,))
    if cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    conn.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
    conn.commit()
    return None
