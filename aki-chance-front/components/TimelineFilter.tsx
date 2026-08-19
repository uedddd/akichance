'use client';

import { FilterState, SeatCapacity, SeatType } from '@/types/seat';

type Props = {
  filter  : FilterState;
  onChange: (next: FilterState) => void;
  onReset : () => void;
};

const TYPE_OPTIONS: { value: SeatType; label: string }[] = [
  { value: 'desk', label: '打合せ机' },
  { value: 'conf', label: '会議室'   },
  { value: 'free', label: 'フリー'   },
];

const CAP_OPTIONS: { value: SeatCapacity; label: string }[] = [
  { value: 4, label: '4名' },
  { value: 6, label: '6名' },
  { value: 8, label: '8名' },
];

export default function TimelineFilter({ filter, onChange, onReset }: Props) {
  const isActive =
    filter.types.length > 0 || filter.monitor || filter.caps.length > 0;

  const toggleType = (t: SeatType) => {
    const next = filter.types.includes(t)
      ? filter.types.filter(x => x !== t)
      : [...filter.types, t];
    onChange({ ...filter, types: next });
  };

  const toggleCap = (c: SeatCapacity) => {
    if (c === null) return;
    const next = filter.caps.includes(c)
      ? filter.caps.filter(x => x !== c)
      : [...filter.caps, c];
    onChange({ ...filter, caps: next });
  };

  return (
    <div className="bg-[#f8f9fb] border-[1.5px] border-[#e0e4ea] rounded-[10px]
                    px-4 py-2.5 flex items-center gap-4 flex-wrap mb-5">

      <span className="text-xs font-bold text-[#5a7a9a] whitespace-nowrap">
        🔍 絞り込み
      </span>

      <div className="w-px h-6 bg-[#dde2ea] flex-shrink-0" />

      <div className="flex items-center gap-2.5 flex-wrap">
        <span className="text-[13px] font-semibold text-[#1a3a5c] whitespace-nowrap">
          種別：
        </span>
        {TYPE_OPTIONS.map(({ value, label }) => (
          <label
            key={value}
            className="flex items-center gap-[7px] cursor-pointer select-none"
          >
            <input
              type="checkbox"
              checked={filter.types.includes(value)}
              onChange={() => toggleType(value)}
              className="w-4 h-4 accent-[#2d6a9f] cursor-pointer"
            />
            <span className="text-[13px] font-semibold text-[#1a3a5c]">{label}</span>
          </label>
        ))}
      </div>

      <div className="w-px h-6 bg-[#dde2ea] flex-shrink-0" />

      <label className="flex items-center gap-[7px] cursor-pointer select-none">
        <input
          type="checkbox"
          checked={filter.monitor}
          onChange={e => onChange({ ...filter, monitor: e.target.checked })}
          className="w-4 h-4 accent-[#2d6a9f] cursor-pointer"
        />
        <span className="text-[13px] font-semibold text-[#1a3a5c]">
          🖥️ モニターあり
        </span>
      </label>

      <div className="w-px h-6 bg-[#dde2ea] flex-shrink-0" />

      <div className="flex items-center gap-2.5 flex-wrap">
        <span className="text-[13px] font-semibold text-[#1a3a5c] whitespace-nowrap">
          👥 人数：
        </span>
        {CAP_OPTIONS.map(({ value, label }) => (
          <label
            key={String(value)}
            className="flex items-center gap-[7px] cursor-pointer select-none"
          >
            <input
              type="checkbox"
              checked={filter.caps.includes(value)}
              onChange={() => toggleCap(value)}
              className="w-4 h-4 accent-[#2d6a9f] cursor-pointer"
            />
            <span className="text-[13px] font-semibold text-[#1a3a5c]">{label}</span>
          </label>
        ))}
      </div>

      <div className="w-px h-6 bg-[#dde2ea] flex-shrink-0" />

      {isActive && (
        <span className="text-[11px] font-bold bg-[#2d6a9f] text-white
                         rounded-[10px] px-2.5 py-0.5">
          フィルター適用中
        </span>
      )}

      {isActive && (
        <button
          onClick={onReset}
          className="text-xs font-semibold text-[#888] bg-transparent
                     border-[1.5px] border-[#dde2ea] rounded-md px-3 py-1
                     cursor-pointer hover:bg-[#f0f2f5] hover:text-[#555]
                     transition-all duration-200"
        >
          ✕ リセット
        </button>
      )}
    </div>
  );
}