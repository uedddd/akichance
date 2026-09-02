'use client';

import { Seat, SeatStatus } from '@/types/seat';

type Props = {
  seat     : Seat;
  onReserve: (seatName: string) => void;
};

type StyleDef = {
  borderLeft: string;
  bg        : string;
  dot       : string;
  textColor : string;
  label     : string;
};

const STATUS_STYLE: Record<SeatStatus, StyleDef> = {
  empty   : { borderLeft:'#27ae60', bg:'white',   dot:'#27ae60', textColor:'#27ae60', label:'空き'   },
  in_use  : { borderLeft:'#e74c3c', bg:'#fff8f8', dot:'#e74c3c', textColor:'#e74c3c', label:'使用中' },
  reserved: { borderLeft:'#f39c12', bg:'#fffbf2', dot:'#f39c12', textColor:'#f39c12', label:'予約中' },
};

export default function ConfCard({ seat, onReserve }: Props) {
  const s = STATUS_STYLE[seat.status];

  return (
    <div
      onClick={() => onReserve(seat.seat_name)}
      className="border-2 border-[#b0c4d8] rounded-lg p-2 cursor-pointer
                 transition-transform duration-150
                 hover:-translate-y-0.5 hover:shadow-[0_6px_16px_rgba(0,0,0,0.13)]
                 w-[110px] h-[115px] flex flex-col"
      style={{
        borderLeftColor : s.borderLeft,
        borderLeftWidth : 4,
        backgroundColor : s.bg,
      }}
    >
      <div className="flex flex-col gap-1 flex-1">

        {/* 席名：大きく */}
        <div className="text-[13px] font-bold text-[#1a3a5c] leading-tight truncate">
          {seat.seat_name}
        </div>

        {/* 定員：小さく */}
        <div className="text-[10px] font-semibold text-[#1a3a5c] leading-tight">
          {seat.capacity}名
        </div>

        {/* ステータス */}
        <div className="flex items-center gap-1">
          <span
            className="w-[7px] h-[7px] rounded-full flex-shrink-0"
            style={{ background: s.dot }}
          />
          <span
            className="text-[10px] font-bold"
            style={{ color: s.textColor }}
          >
            {s.label}
          </span>
        </div>
      </div>

      {/* ボタン（下部固定） */}
      <button
        onClick={e => { e.stopPropagation(); onReserve(seat.seat_name); }}
        className="w-full py-[5px] bg-[#2d6a9f] text-white border-none
                   rounded text-[10px] font-semibold cursor-pointer
                   hover:bg-[#1a3a5c] transition-colors flex-shrink-0"
      >
        予約する
      </button>
    </div>
  );
}