import { TimelineRow as TimelineRowData } from '@/types/seat';

type Props = {
  row: TimelineRowData;
};

const BLOCK_BG: Record<'in_use' | 'reserved', string> = {
  in_use  : '#e74c3c',
  reserved: '#f39c12',
};

export default function TimelineRow({ row }: Props) {
  return (
    <div className="flex items-center mb-2 min-h-[34px]">
      <div className="w-[160px] text-xs text-[#444] flex-shrink-0
                      pr-2.5 whitespace-nowrap">
        {row.seat_name}
      </div>

      <div className="tl-track flex-1 h-[22px] bg-[#f0f2f5] rounded
                      relative min-w-[522px]">
        {row.blocks.map((block, i) => (
          <div
            key={i}
            className="absolute h-full rounded flex items-center px-1.5
                       text-[10px] font-semibold text-white
                       whitespace-nowrap overflow-hidden"
            style={{
              left           : `${block.left}%`,
              width          : `${block.width}%`,
              backgroundColor: BLOCK_BG[block.status],
            }}
          >
            {block.label}
          </div>
        ))}
      </div>
    </div>
  );
}