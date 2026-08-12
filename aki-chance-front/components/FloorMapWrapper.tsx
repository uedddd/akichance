'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  FloorNumber, SummaryCount, FilterState, ReserveFormInput,
} from '@/types/seat';
import { DUMMY_SEATS, DUMMY_TIMELINE } from '@/lib/dummyData';

import SummaryBar    from './SummaryBar';
import TabBar        from './TabBar';
import { TabKey }    from './TabBar';
import FloorMapPanel from './FloorMapPanel';
import TimelinePanel from './TimelinePanel';
import ReserveModal  from './ReserveModal';

const INIT_FILTER: FilterState = { types: [], monitor: false, caps: [] };

export default function FloorMapWrapper() {
  const [currentFloor, setCurrentFloor] = useState<FloorNumber>(4);
  const [currentTab,   setCurrentTab  ] = useState<TabKey>('map');
  const [modalSeat,    setModalSeat   ] = useState<string | null>(null);
  const [toast,        setToast       ] = useState<string | null>(null);
  const [toastVisible, setToastVisible] = useState(false);
  const [filter,       setFilter      ] = useState<FilterState>(INIT_FILTER);

  const seats        = DUMMY_SEATS[currentFloor];
  const timelineRows = DUMMY_TIMELINE[currentFloor];

  const counts: SummaryCount = seats.reduce(
    (acc, s) => {
      acc.total++;
      if      (s.status === 'empty'   ) acc.vacant++;
      else if (s.status === 'in_use'  ) acc.inuse++;
      else if (s.status === 'reserved') acc.reserved++;
      return acc;
    },
    { total: 0, vacant: 0, inuse: 0, reserved: 0 },
  );

  const handleFloorChange = useCallback((floor: FloorNumber) => {
    setCurrentFloor(floor);
    setFilter(INIT_FILTER);
  }, []);

  const handleConfirm = useCallback((input: ReserveFormInput) => {
    setModalSeat(null);
    const msg =
      `✅ 予約完了：${input.seatName}（${input.startTime}〜${input.endTime}）${input.userName} さん`;
    setToast(msg);
  }, []);

  useEffect(() => {
    if (!toast) { setToastVisible(false); return; }
    const show = requestAnimationFrame(() => setToastVisible(true));
    const hide = setTimeout(() => {
      setToastVisible(false);
      setTimeout(() => setToast(null), 350);
    }, 3500);
    return () => { cancelAnimationFrame(show); clearTimeout(hide); };
  }, [toast]);

  return (
    <>
      <SummaryBar counts={counts} currentFloor={currentFloor} />

      <div className="p-5">
        <TabBar current={currentTab} onChange={setCurrentTab} />

        {currentTab === 'map' && (
          <FloorMapPanel
            floor={currentFloor}
            seats={seats}
            onReserve={setModalSeat}
            onFloorChange={handleFloorChange}
          />
        )}

        {currentTab === 'timeline' && (
          <TimelinePanel
            floor={currentFloor}
            rows={timelineRows}
            filter={filter}
            onFilterChange={setFilter}
            onFilterReset={() => setFilter(INIT_FILTER)}
            onFloorChange={handleFloorChange}
          />
        )}
      </div>

      <ReserveModal
        seatName={modalSeat}
        onConfirm={handleConfirm}
        onClose={() => setModalSeat(null)}
      />

      {toast && (
        <div
          className={[
            'fixed bottom-8 left-1/2 -translate-x-1/2',
            'bg-[#1a3a5c] text-white px-7 py-3 rounded-[10px]',
            'text-sm font-semibold shadow-[0_4px_20px_rgba(0,0,0,0.2)]',
            'z-[300] pointer-events-none',
            'transition-all duration-[350ms]',
            toastVisible
              ? 'opacity-100 translate-y-0'
              : 'opacity-0 translate-y-20',
          ].join(' ')}
        >
          {toast}
        </div>
      )}
    </>
  );
}