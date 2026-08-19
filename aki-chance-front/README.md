<<<<<<< HEAD
This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
=======
#serverの起動方法

①AzureportalからakichanceVMを選択し、タブにある開始ボタンが押されていることを確認

②powershellを起動

③以下のコマンドを実行

　ssh -i C:\Users\26h1_p53\ueda\ssh\akichance-key.pem azureuser@20.243.122.235

　source ~/fastapi-app/venv/bin/activate

　uvicorn app:app --host 0.0.0.0 --port 8000 --reload



------------------------------------------------------------------------------
#接続先URL
　http://20.243.122.235:8000/

------------------------------------------------------------------------------
#Gitにある内容をサーバーに適用するコマンド

　cd ~/akichance

　git pull origin main

 ----------------------------------------------------------------------------
 #DBにテーブル作成

 ①AzurePortalでakichanceDBを選択

 ②左メニューから「クエリエディター（プレビュー）」を選択

 ③「新しいクエリ」を選択してSQLを入力・実行

>>>>>>> f4238cde142afe29e9a1554260ce064ea4d4efc5
