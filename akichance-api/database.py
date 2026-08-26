import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# .envから接続情報を取得
SERVER   = os.getenv("SQL_SERVER")
DATABASE = os.getenv("SQL_DATABASE")
USER     = os.getenv("SQL_USER")
PASSWORD = os.getenv("SQL_PASSWORD")

# DB接続文字列を作成
CONNECTION_STRING = (
    f"mssql+pyodbc://{USER}:{PASSWORD}@{SERVER}/{DATABASE}"
    f"?driver=ODBC+Driver+18+for+SQL+Server"
)

# DB接続の設定
engine       = create_engine(CONNECTION_STRING, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base         = declarative_base()

# APIが使うDB接続関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()