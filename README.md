#serverの起動方法

①AzureportalからakichanceVMを選択し、タブにある開始ボタンが押されていることを確認

②powershellを起動

③以下のコマンドを実行

　ssh -i C:\Users\26h1_p53\ueda\ssh\akichance-key.pem azureuser@20.243.122.235

　source ~/fastapi-app/venv/bin/activate

 cd ~/fastapi-app/app

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

