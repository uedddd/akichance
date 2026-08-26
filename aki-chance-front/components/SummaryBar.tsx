import { SummaryCount, FloorNumber } from '@/types/seat';

type Props = {
  counts      : SummaryCount;
  currentFloor: FloorNumber;
};

export default function SummaryBar({ counts, currentFloor }: Props) {
  const { total, vacant, inuse, reserved } = counts;

  return (
    <div className="bg-white border-b border-[#e0e4ea] px-6 py-2.5
                    flex flex-wrap gap-5 items-center">

      <div className="flex flex-col items-center min-w-[60px]">
        <span className="text-[26px] font-extrabold leading-none text-[#1a3a5c]">
          {total}
        </span>
        <span className="text-[11px] text-[#888] mt-0.5">総席数</span>
      </div>

      <div className="w-px h-[38px] bg-[#e0e4ea]" />

      <div className="flex flex-col items-center min-w-[60px]">
        <span className="text-[26px] font-extrabold leading-none text-[#27ae60]">
          {vacant}
        </span>
        <span className="text-[11px] text-[#888] mt-0.5">空き</span>
      </div>

      <div className="flex flex-col items-center min-w-[60px]">
        <span className="text-[26px] font-extrabold leading-none text-[#e74c3c]">
          {inuse}
        </span>
        <span className="text-[11px] text-[#888] mt-0.5">使用中</span>
      </div>

      <div className="flex flex-col items-center min-w-[60px]">
        <span className="text-[26px] font-extrabold leading-none text-[#f39c12]">
          {reserved}
        </span>
        <span className="text-[11px] text-[#888] mt-0.5">予約中</span>
      </div>

      <div className="w-px h-[38px] bg-[#e0e4ea]" />

      <div className="flex items-center gap-1.5 text-xs text-[#555]">
        <span className="w-2.5 h-2.5 rounded-full bg-[#27ae60] inline-block" />
        空き
      </div>
      <div className="flex items-center gap-1.5 text-xs text-[#555]">
        <span className="w-2.5 h-2.5 rounded-full bg-[#e74c3c] inline-block" />
        使用中
      </div>
      <div className="flex items-center gap-1.5 text-xs text-[#555]">
        <span className="w-2.5 h-2.5 rounded-full bg-[#f39c12] inline-block" />
        予約中
      </div>
      <div className="text-xs text-[#555]">🖥️ モニター有</div>

      <div className="ml-auto bg-[#e8f0fe] text-[#2d6a9f] text-[13px] font-bold
                      rounded-lg px-3.5 py-1 border-[1.5px] border-[#c8d6e5]">
        {currentFloor}階 表示中
      </div>
    </div>
  );
}
