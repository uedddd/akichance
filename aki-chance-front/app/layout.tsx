import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title      : '空きチャンス',
  description: '打合せ机 予約・使用状況管理システム',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="bg-[#f0f2f5] text-[#333] text-sm min-h-screen">
        <header
          className="sticky top-0 z-[100] h-14 px-6
                     flex items-center gap-3
                     text-white shadow-[0_2px_8px_rgba(0,0,0,0.2)]"
          style={{ background: 'linear-gradient(135deg, #1a3a5c, #2d6a9f)' }}
        >
          <span className="text-2xl">🏢</span>
          <div className="flex items-baseline gap-2">
            <h1 className="text-[17px] font-bold leading-none">
              空きチャンス
            </h1>
            <span className="text-[12px] text-white/70 font-normal">
              打合せ机 予約・使用状況管理システム
            </span>
          </div>
        </header>

        {children}
      </body>
    </html>
  );
}