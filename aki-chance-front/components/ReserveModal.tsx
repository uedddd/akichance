'use client';

import { useState, useEffect, useRef } from 'react';
import { ReserveFormInput } from '@/types/seat';

type Props = {
  seatName : string | null;
  onConfirm: (input: ReserveFormInput) => void;
  onClose  : () => void;
};

const START_HOUR = 9;
const END_HOUR   = 18;

const START_OPTS: string[] = (() => {
  const opts: string[] = [];
  for (let h = START_HOUR; h < END_HOUR; h++) {
    for (const m of [0, 30]) {
      opts.push(`${h}:${m === 0 ? '00' : m}`);
    }
  }
  return opts;
})();

const END_OPTS: string[] = (() => {
  const opts: string[] = [];
  for (let h = START_HOUR; h <= END_HOUR; h++) {
    for (const m of [0, 30]) {
      if (h === START_HOUR && m === 0) continue;
      if (h === END_HOUR   && m === 30) break;
      opts.push(`${h}:${m === 0 ? '00' : m}`);
    }
  }
  return opts;
})();

export default function ReserveModal({ seatName, onConfirm, onClose }: Props) {
  const [userName,  setUserName ] = useState('');
  const [startTime, setStartTime] = useState('10:00');
  const [endTime,   setEndTime  ] = useState('11:00');
  const [nameError, setNameError] = useState(false);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (seatName) {
      setUserName('');
      setStartTime('10:00');
      setEndTime('11:00');
      setNameError(false);
    }
  }, [seatName]);

  if (!seatName) return null;

  const handleConfirm = () => {
    if (!userName.trim()) {
      setNameError(true);
      nameRef.current?.focus();
      setTimeout(() => setNameError(false), 1500);
      return;
    }
    onConfirm({ seatName, userName: userName.trim(), startTime, endTime });
  };

  const inputBase =
    'w-full py-[9px] px-3 border-[1.5px] rounded-lg text-sm text-[#333] outline-none focus:border-[#2d6a9f]';

  return (
    <div
      className="fixed inset-0 bg-black/40 z-[200] flex justify-center items-center"
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-2xl px-8 py-7 w-[420px] max-w-[95vw]
                      shadow-[0_10px_40px_rgba(0,0,0,0.2)]">

        <div className="text-[17px] font-bold text-[#1a3a5c] mb-5">
          📝 予約フォーム
        </div>

        <div className="mb-3.5">
          <label className="block text-xs font-semibold text-[#666] mb-1">席名</label>
          <input
            type="text"
            readOnly
            value={seatName}
            className={`${inputBase} border-[#dde2ea] bg-[#f8f9fb]`}
          />
        </div>

        <div className="mb-3.5">
          <label className="block text-xs font-semibold text-[#666] mb-1">予約者名</label>
          <input
            ref={nameRef}
            type="text"
            value={userName}
            onChange={e => setUserName(e.target.value)}
            placeholder="例：山田 太郎"
            className={`${inputBase} ${nameError ? 'border-[#e74c3c]' : 'border-[#dde2ea]'}`}
          />
        </div>

        <div className="grid grid-cols-2 gap-3 mb-3.5">
          <div>
            <label className="block text-xs font-semibold text-[#666] mb-1">開始時間</label>
            <select
              value={startTime}
              onChange={e => setStartTime(e.target.value)}
              className={`${inputBase} border-[#dde2ea]`}
            >
              {START_OPTS.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-[#666] mb-1">終了時間</label>
            <select
              value={endTime}
              onChange={e => setEndTime(e.target.value)}
              className={`${inputBase} border-[#dde2ea]`}
            >
              {END_OPTS.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
        </div>

        <div className="flex gap-2.5 mt-[18px]">
          <button
            onClick={handleConfirm}
            className="flex-1 py-[11px] bg-[#2d6a9f] text-white border-none
                       rounded-lg text-sm font-bold cursor-pointer
                       hover:bg-[#1a3a5c] transition-colors"
          >
            予約確定
          </button>
          <button
            onClick={onClose}
            className="flex-1 py-[11px] bg-[#f0f2f5] text-[#555] border-none
                       rounded-lg text-sm font-semibold cursor-pointer
                       hover:bg-[#dde2ea] transition-colors"
          >
            キャンセル
          </button>
        </div>
      </div>
    </div>
  );
}