import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User

# プロジェクトのルートディレクトリを特定
# os.path.dirname(__file__) は現在のファイルのディレクトリ (例: C:/.../social-implementation/python)
# os.path.dirname(os.path.dirname(__file__)) で一つ上の親ディレクトリ (例: C:/.../social-implementation) に移動
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

# データベースファイルへのパスを定義
DATABASE_PATH = os.path.join(PROJECT_ROOT, 'db', 'food_loss.db')
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# データベースエンジンとセッションを作成
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def add_test_user():
    session = Session()
    try:
        # 新しいユーザーを作成
        new_user = User(
            username="test_user", 
            password="hashed_password", 
            email="test@example.com")

        # セッションに追加
        session.add(new_user)

        # 変更をデータベースにコミット
        session.commit()
        print("Test user added successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error adding user: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    add_test_user()