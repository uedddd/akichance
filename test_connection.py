

"""
Azure SQL Server への接続テストスクリプト
このスクリプトで接続情報が正しいか確認できます
"""

import os
import sys
import struct
from pathlib import Path

# .env ファイルが存在する場合は読み込む
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

try:
    import pyodbc
except ImportError:
    print("エラー: pyodbc がインストールされていません")
    print("以下のコマンドを実行してください:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

try:
    from azure.identity import ClientSecretCredential
except ImportError:
    print("エラー: azure-identity がインストールされていません")
    print("以下のコマンドを実行してください:")
    print("  pip install azure-identity")
    sys.exit(1)


def test_connection():
    """Azure SQL への接続をテストする"""
    
    # 接続情報を環境変数から取得
    server        = os.getenv("AZURE_SQL_SERVER",   "akichanceserver.database.windows.net")
    database      = os.getenv("AZURE_SQL_DATABASE", "akichanceDB")
    driver        = os.getenv("AZURE_SQL_DRIVER",   "ODBC Driver 18 for SQL Server")
    client_id     = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    tenant_id     = os.getenv("AZURE_TENANT_ID")
    
    print("=" * 60)
    print("Azure SQL Server 接続テスト")
    print("=" * 60)
    print(f"サーバー:       {server}")
    print(f"データベース:   {database}")
    print(f"ODBCドライバー: {driver}")
    print(f"クライアントID: {client_id}")
    print(f"テナントID:     {tenant_id}")
    print("=" * 60)
    
    # サービスプリンシパルの設定確認
    if not client_id or not client_secret or not tenant_id:
        print("⚠️  警告: サービスプリンシパルの設定が不足しています")
        print("以下を .env ファイルに設定してください:")
        print("  AZURE_CLIENT_ID")
        print("  AZURE_CLIENT_SECRET")
        print("  AZURE_TENANT_ID")
        return False
    
    try:
        print("\n🔑 トークン取得中...")

        # サービスプリンシパルでトークン取得
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )

        # アクセストークン取得
        token = credential.get_token("https://database.windows.net/.default")
        token_bytes = token.token.encode("utf-16-le")
        token_struct = struct.pack(
            f"<I{len(token_bytes)}s",
            len(token_bytes),
            token_bytes
        )
        print("✅ トークン取得成功！")

        # 接続文字列を生成（UID/PWD不要）
        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )

        print("\n🔌 接続中...")
        connection = pyodbc.connect(
            connection_string,
            attrs_before={1256: token_struct}  # トークン認証
        )
        print("✅ 接続成功！")
        
        # 簡単なクエリを実行してDBが動作しているか確認
        cursor = connection.cursor()
        cursor.execute("SELECT GETDATE() as CurrentDateTime")
        row = cursor.fetchone()
        
        if row:
            print(f"📅 サーバー時刻: {row[0]}")
        
        # テーブル一覧を取得
        cursor.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE='BASE TABLE'"
        )
        tables = cursor.fetchall()
        
        print(f"\n📊 データベース内のテーブル: {len(tables)} 件")
        for table in tables:
            print(f"   - {table[0]}")
        
        connection.close()
        print("\n✅ すべてのテストが完了しました")
        return True
        
    except pyodbc.OperationalError as e:
        print(f"\n❌ 接続エラー:")
        print(f"   {e}")
        print("\n💡 トラブルシューティング:")
        print("   1. サーバー名とデータベース名が正しいか確認してください")
        print("   2. クライアントID・シークレット・テナントIDを確認してください")
        print("   3. Azure SQLにサービスプリンシパルユーザーを追加してください")
        print("   4. Azure ポータルでファイアウォール設定を確認してください")
        return False
        
    except pyodbc.ProgrammingError as e:
        print(f"\n❌ SQL エラー:")
        print(f"   {e}")
        return False
        
    except Exception as e:
        print(f"\n❌ 予期しないエラー:")
        print(f"   {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)


AZURE_SQL_SERVER=akichanceserver.database.windows.net
AZURE_SQL_DATABASE=akichanceDB
AZURE_SQL_DRIVER=ODBC Driver 18 for SQL Server
AZURE_CLIENT_ID=取得したクライアントID
AZURE_CLIENT_SECRET=取得したシークレット
AZURE_TENANT_ID=取得したテナントID


## ✅ Azure SQLにユーザーを追加

Azureポータルの **Query Editor** で実行


CREATE USER [akichance-app] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [akichance-app];
ALTER ROLE db_datawriter ADD MEMBER [akichance-app];
