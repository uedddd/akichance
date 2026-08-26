'use client';

export type TabKey = 'map' | 'timeline';

type Props = {
  current : TabKey;
  onChange: (tab: TabKey) => void;
};

const TABS: { key: TabKey; label: string }[] = [
  { key: 'map',      label: '🗺️ フロアマップ' },
  { key: 'timeline', label: '📅 タイムライン' },
];

export default function TabBar({ current, onChange }: Props) {
  return (
    <div className="flex gap-1 mb-5 border-b-2 border-[#dde2ea]">
      {TABS.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key)}
          className={[
            'px-5 py-2.5 text-sm bg-transparent border-none cursor-pointer',
            'border-b-2 -mb-[2px] transition-all duration-200',
            current === key
              ? 'text-[#2d6a9f] border-b-[#2d6a9f] font-semibold'
              : 'text-[#888] border-b-transparent',
          ].join(' ')}
        >
          {label}
        </button>
      ))}
    </div>
  );
}