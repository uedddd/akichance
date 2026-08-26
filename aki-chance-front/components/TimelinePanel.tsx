'use client';

import { useEffect, useRef, useCallback } from 'react';
import { TimelineRow as TimelineRowData, FilterState, FloorNumber, SeatType } from '@/types/seat';
import TimelineFilter from './TimelineFilter';
import TimelineRow    from './TimelineRow';

type Props = {
  floor         : FloorNumber;
  rows          : TimelineRowData[];
  filter        : FilterState;
  onFilterChange: (next: FilterState) => void;
  onFilterReset : () => void;
  onFloorChange : (floor: FloorNumber) => void;
};

const START_HOUR = 9;
const END_HOUR   = 18;
const HOURS      = Array.from(
  { length: END_HOUR - START_HOUR + 1 },
  (_, i) => i + START_HOUR,
);

const SECTION_LABELS: Record<SeatType, string> = {
  desk: '📋 打合せ机',
  conf: '🚪 会議室',
  free: '🪑 フリー',
};
const SECTION_ORDER: SeatType[] = ['desk', 'conf', 'free'];

const ARROW_SVG = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%231a3a5c' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`;

export default function TimelinePanel({
  floor, rows, filter, onFilterChange, onFilterReset, onFloorChange,
}: Props) {
  const nowLineRef = useRef<HTMLDivElement>(null);
  const tbodyRef   = useRef<HTMLDivElement>(null);

  const updateNowLine = useCallback(() => {
    const line  = nowLineRef.current;
    const tbody = tbodyRef.current;
    if (!line || !tbody) return;

    const now   = new Date();
    const hours = now.getHours() + now.getMinutes() / 60;

    if (hours < START_HOUR || hours > END_HOUR) {
      line.style.display = 'none';
      return;
    }

    const track = tbody.querySelector<HTMLElement>('.tl-track');
    if (!track) { line.style.display = 'none'; return; }

    const pct       = ((hours - START_HOUR) / (END_HOUR - START_HOUR)) * 100;
    const tbRect    = tbody.getBoundingClientRect();
    const trackRect = track.getBoundingClientRect();

    line.style.display = 'block';
    line.style.left    =
      `${(trackRect.left - tbRect.left) + (pct / 100) * trackRect.width}px`;
  }, []);

  useEffect(() => {
    updateNowLine();
    const id = setInterval(updateNowLine, 60_000);
    window.addEventListener('resize', updateNowLine);
    return () => {
      clearInterval(id);
      window.removeEventListener('resize', updateNowLine);
    };
  }, [updateNowLine]);

  const isVisible = (row: TimelineRowData): boolean => {
    const passType    = filter.types.length === 0 || filter.types.includes(row.seat_type);
    const passMonitor = !filter.monitor || row.seat_type !== 'desk' || row.has_monitor;
    const passCap     =
      filter.caps.length === 0 ||
      row.seat_type !== 'desk'  ||
      (row.capacity !== null && filter.caps.includes(row.capacity));
    return passType && passMonitor && passCap;
  };

  const isSectionVisible = (type: SeatType): boolean =>
    filter.types.length === 0 || filter.types.includes(type);

  return (
    <div className="bg-white rounded-xl p-6 shadow-[0_2px_8px_rgba(0,0,0,0.06)] overflow-x-auto">

      <div className="flex items-center gap-3.5 mb-5">
        <span className="text-base font-bold text-[#1a3a5c] whitespace-nowrap">
          📅 タイムライン（9:00〜18:00）—
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

      <TimelineFilter
        filter={filter}
        onChange={onFilterChange}
        onReset={onFilterReset}
      />

      <div className="flex mb-2 ml-[160px] min-w-[580px]">
        {HOURS.map(h => (
          <div key={h} className="flex-1 text-[11px] text-[#aaa] text-left min-w-[58px]">
            {h}:00
          </div>
        ))}
      </div>

      <div ref={tbodyRef} className="relative min-w-[740px]">

        <div
          ref={nowLineRef}
          className="absolute top-0 bottom-0 w-[2px] bg-[#e74c3c]
                     z-10 pointer-events-none"
          style={{ display: 'none' }}
        >
          <div className="absolute -top-[5px] left-1/2 -translate-x-1/2
                          w-2 h-2 bg-[#e74c3c] rounded-full" />
        </div>

        {SECTION_ORDER.map(type => {
          const sectionRows = rows.filter(r => r.seat_type === type);
          if (sectionRows.length === 0) return null;

          return (
            <div key={type}>
              {isSectionVisible(type) && (
                <div className="mt-2.5 mb-1">
                  <div className="text-xs font-bold text-[#5a7a9a]
                                  py-1.5 pb-1 border-b border-[#e0e4ea]
                                  flex items-center gap-1.5 w-full">
                    {SECTION_LABELS[type]}
                  </div>
                </div>
              )}

              {sectionRows.map(row =>
                isVisible(row) && (
                  <TimelineRow key={row.seat_code} row={row} />
                )
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}