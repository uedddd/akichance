# Windows 用 Azure SQL Server セットアップガイド

## 📋 前提条件
- Windows 10 以降
- Python 3.11.x がおすすめ（3.10 以上でも動作可能）
- Azure SQL Server がクラウド上に作成されていること

> 注意: 現在の Python 実装は `pyodbc` を使っているため、Azure SQL へ直接接続するには ODBC Driver 18 for SQL Server が必要です。管理者権限がなくてインストールできない場合は、別の接続方式を検討する必要があります。

---

## ✅ セットアップステップ

### 1️⃣ ODBC Driver 18 for SQL Server をインストール

#### 方法 A: winget を使用（推奨）
PowerShell を管理者モードで開いて実行：
```powershell
winget install Microsoft.ODBCDriver18forSQLServer
```

#### 方法 B: 手動ダウンロード
1. 以下のリンクから ODBC Driver 18 をダウンロード:  
   https://learn.microsoft.com/ja-jp/sql/connect/odbc/download-odbc-driver-for-sql-server

2. ダウンロードしたインストーラー（例：`msodbcsql.msi`）を実行

3. インストーラーのガイドに従って完了させる

#### インストール確認
PowerShell で実行：
```powershell
Get-OdbcDriver | Select-Object Name
```
出力に「ODBC Driver 18 for SQL Server」が表示されていればOK

#### もし管理者権限がなくてインストールできない場合
この構成では ODBC Driver が必須です。代替案としては以下があります。

1. Azure SQL へ接続する別の言語・実行環境を使う
   - 例: Azure Functions, App Service, Azure Container Apps などのサーバー側に接続処理を置く

2. API 経由で接続する
   - 例: REST API を Azure 上で公開し、ローカルアプリはその API でデータにアクセスする

3. Azure Data Studio / SQL Server Management Studio などのクライアントツールで直接操作する
   - これは Python アプリからの接続ではなく、管理用の接続手段です

4. 既存の接続方式を変更する
   - `pyodbc` ではなく、Azure SQL への HTTP ベースの接続や別の SDK を使う構成に変更する

---

### 2️⃣ Python パッケージをインストール

```bash
# プロジェクトディレクトリに移動
cd c:\Users\26h1_p53\ueda\akichance

# 依存パッケージをインストール
pip install -r requirements.txt
```

---

### 3️⃣ 環境変数を設定

#### 方法 A: .env ファイルを使用（開発環境推奨）

1. `.env.example` をコピーして `.env` を作成:
```bash
copy .env.example .env
```

2. `.env` を編集してパスワードを追加:
```
AZURE_SQL_SERVER=akichanceserver.database.windows.net
AZURE_SQL_DATABASE=akichanceDB
AZURE_SQL_USERNAME=g735218@mytecno23.onmicrosoft.com
AZURE_SQL_PASSWORD=!QAZ2wsx
```

3. Python が .env を自動的に読み込むように以下をインストール:
```bash
pip install python-dotenv
```

#### 方法 B: OS の環境変数を設定（本番環境推奨）

**Windows 環境変数の設定手順:**

1. スタートメニューから「環境変数」を検索
2. 「システム環境変数の編集」をクリック
3. 「環境変数」ボタンをクリック
4. 「新規」ボタンで以下を追加:

| 変数名 | 値 |
|--------|-----|
| `AZURE_SQL_SERVER` | `akichanceserver.database.windows.net` |
| `AZURE_SQL_DATABASE` | `akichanceDB` |
| `AZURE_SQL_USERNAME` | `g735218@mytecno23.onmicrosoft.com` |
| `AZURE_SQL_PASSWORD` | `!QAZ2wsx` |

5. 「OK」をクリックして保存

⚠️ **セキュリティ注意:**
- `.env` ファイルは `.gitignore` に追加してバージョン管理から除外してください
- `.env.example` には実際のパスワードを記載しないでください

---

### 4️⃣ 接続テストを実行

```bash
python test_connection.py
```

成功時の出力例：
```
============================================================
Azure SQL Server 接続テスト
============================================================
サーバー: akichanceserver.database.windows.net
データベース: akichanceDB
ユーザー: g735218@mytecno23.onmicrosoft.com
ODBCドライバー: ODBC Driver 18 for SQL Server
============================================================

🔌 接続中...
✅ 接続成功！
📅 サーバー時刻: 2025-07-15 10:30:45
📊 データベース内のテーブル: 3 件
   - seats
   - reservations
   - users
```

---

## 🐛 トラブルシューティング

### エラー: `pyodbc.OperationalError: ('08001', '[08001]`
**原因:** ODBC ドライバーが見つからない

**解決策:**
```powershell
# ODBC ドライバーが正しくインストールされているか確認
Get-OdbcDriver | Select-Object Name | Where-Object {$_ -match "SQL Server"}
```

---

### エラー: `Connection timeout expired`
**原因:** サーバーに接続できない（ファイアウォールルール設定不足）

**解決策:**
1. Azure ポータルにログイン
2. SQL Server リソースを選択
3. 「ファイアウォール設定」から、あなたの IP アドレスを許可ルールに追加
4. または「Azure サービスとリソースにこのサーバーへのアクセスを許可する」をONに設定

---

### エラー: `Login failed for user`
**原因:** ユーザー名またはパスワードが正しくない

**解決策:**
1. Azure ポータルで SQL Server のプロパティを確認
2. ユーザー名とパスワードが正しいか再確認
3. パスワードにスペシャルキャラクターが含まれている場合は、接続文字列内でエスケープしているか確認

---

## 🚀 アプリケーションを実行

接続テストが成功したら、FastAPI アプリケーションを起動できます：

```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

ブラウザで `http://localhost:8000/docs` にアクセスして Swagger UI を確認できます。

---

## 📚 参考リンク

- [Microsoft ODBC Driver for SQL Server](https://learn.microsoft.com/ja-jp/sql/connect/odbc/download-odbc-driver-for-sql-server)
- [pyodbc ドキュメント](https://github.com/mkleehammer/pyodbc/wiki)
- [Azure SQL Database ファイアウォール設定](https://learn.microsoft.com/ja-jp/azure/azure-sql/database/firewall-configure)
- [FastAPI ドキュメント](https://fastapi.tiangolo.com/ja/)
