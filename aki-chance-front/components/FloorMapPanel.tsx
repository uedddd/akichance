'use client';

import { Seat, FloorNumber } from '@/types/seat';
import ConfCard from './ConfCard';
import DeskCard from './DeskCard';

type Props = {
  floor        : FloorNumber;
  seats        : Seat[];
  onReserve    : (seatName: string) => void;
  onFloorChange: (floor: FloorNumber) => void;
};

const ARROW_SVG = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%231a3a5c' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`;

export default function FloorMapPanel({
  floor, seats, onReserve, onFloorChange,
}: Props) {

  const confLeft  = seats.filter(s => s.seat_type === 'conf').slice(0, 3);
  const confRight = seats.filter(s => s.seat_type === 'conf').slice(3, 6);
  const desks     = seats.filter(s => s.seat_type === 'desk');
  const deskTop   = desks.slice(0, 6);
  const deskBot   = desks.slice(6, 12);
  const frees     = seats.filter(s => s.seat_type === 'free');
  const freeLeft  = frees.slice(0, 2);
  const freeRight = frees.slice(2);

  return (
    <div className="bg-white rounded-xl p-6 shadow-[0_2px_8px_rgba(0,0,0,0.06)]">

      <div className="flex items-center gap-3.5 mb-5">
        <span className="text-base font-bold text-[#1a3a5c] whitespace-nowrap">
          🗺️ フロアマップ —
        </span>
        <select
          value={floor}
          onChange={e => onFloorChange(Number(e.target.value) as FloorNumber)}
          className="appearance-none bg-white border-[1.5px] border-[#c8d6e5]
                     rounded-lg text-[#1a3a5c] text-sm font-bold
                     py-[5px] pl-3 pr-8 cursor-pointer outline-none
                     shadow-[0_1px_4px_rgba(0,0,0,0.08)] min-w-[90px]
                     hover:border-[#2d6a9f]
                     focus:border-[#2d6a9f]
                     focus:shadow-[0_0_0_3px_rgba(45,106,159,0.15)]"
          style={{
            backgroundImage   : ARROW_SVG,
            backgroundRepeat  : 'no-repeat',
            backgroundPosition: 'right 10px center',
          }}
        >
          {([4, 5, 6] as FloorNumber[]).map(f => (
            <option key={f} value={f}>{f}階</option>
          ))}
        </select>
      </div>

      <div className="bg-[#f4f7fb] border-2 border-[#c8d6e5] rounded-2xl p-5 overflow-x-auto">
        <div
          className="grid gap-3 items-start min-w-[700px]"
          style={{ gridTemplateColumns: '100px 1fr 100px' }}
        >
          <div className="flex flex-col gap-2">
            {confLeft.map(seat => (
              <ConfCard key={seat.id} seat={seat} onReserve={onReserve} />
            ))}
          </div>

          <div className="flex flex-col">
            <div className="flex gap-2.5 flex-nowrap items-end py-1.5 justify-center">
              {deskTop.map(seat => (
                <DeskCard key={seat.id} seat={seat} onReserve={onReserve} />
              ))}
            </div>

            <div className="h-[250px]" />

            <div className="flex gap-2.5 flex-nowrap items-end py-1.5 justify-center">
              {deskBot.map(seat => (
                <DeskCard key={seat.id} seat={seat} onReserve={onReserve} />
              ))}
            </div>

            <div className="flex gap-2.5 py-1.5 items-start">
              {freeLeft.map(seat => (
                <DeskCard key={seat.id} seat={seat} onReserve={onReserve} />
              ))}
              <div className="flex-1" />
              {freeRight.map(seat => (
                <DeskCard key={seat.id} seat={seat} onReserve={onReserve} />
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-2">
            {confRight.map(seat => (
              <ConfCard key={seat.id} seat={seat} onReserve={onReserve} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}