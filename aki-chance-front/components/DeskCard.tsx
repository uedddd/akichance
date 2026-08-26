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

const CAP_WIDTH: Record<number, number> = { 4: 110, 6: 150, 8: 190 };

export default function DeskCard({ seat, onReserve }: Props) {
  const s      = STATUS_STYLE[seat.status];
  const isFree = seat.seat_type === 'free';
  const w      = isFree ? 80 : (CAP_WIDTH[seat.capacity ?? 4] ?? 92);

  return (
    <div
      onClick={() => onReserve(seat.seat_name)}
      className="border-2 border-[#b0c4d8] rounded-lg cursor-pointer flex-shrink-0
                 flex flex-col
                 transition-transform duration-150
                 hover:-translate-y-0.5 hover:shadow-[0_6px_16px_rgba(0,0,0,0.13)]"
      style={{
        width          : w,
        height         : isFree ? 90 : 105,
        padding        : isFree ? '6px 6px 6px 6px' : '8px 10px 8px 10px',
        borderLeftColor: s.borderLeft,
        borderLeftWidth: 4,
        backgroundColor: s.bg,
      }}
    >
      <div className="flex flex-col gap-1 flex-1 min-h-0">

        {/* 席名＋定員を1行にまとめて大きく */}
        {!isFree ? (
          <div className="flex items-baseline gap-1 flex-wrap">
            <span className="text-[13px] font-bold text-[#1a3a5c] leading-tight">
              {seat.seat_name}
            </span>
            <span className="text-[11px] font-semibold text-[#1a3a5c] leading-tight">
              （{seat.capacity}名）
            </span>
            {seat.has_monitor && (
              <span className="inline-flex items-center text-[9px] font-semibold
                               bg-[#e8f0fe] text-[#2d6a9f] rounded px-1 py-px">
                🖥️ モニター有
              </span>
            )}
          </div>
        ) : (
          <div className="text-[13px] font-bold text-[#1a3a5c] leading-tight">
            {seat.seat_name}
          </div>
        )}

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
        className="w-full bg-[#2d6a9f] text-white border-none rounded
                   font-semibold cursor-pointer flex-shrink-0
                   hover:bg-[#1a3a5c] transition-colors"
        style={{
          fontSize  : isFree ? 9 : 10,
          padding   : isFree ? '4px 0' : '6px 0',
          marginTop : 4,
        }}
      >
        {isFree ? '使用する' : '予約する'}
      </button>
    </div>
  );
}