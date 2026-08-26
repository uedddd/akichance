from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# APIが返すデータの形
class SeatResponse(BaseModel):
    seat_id    : int
    floor_id   : int
    seat_name  : str
    status     : str
    is_active  : bool
    created_at : Optional[datetime]
    updated_at : Optional[datetime]

    class Config:
        from_attributes = True

# ステータス更新APIが受け取るデータの形
class StatusUpdateRequest(BaseModel):
    status : str  # empty / in_use / reserved
