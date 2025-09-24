# models.py
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, REAL
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base 

# データベースモデルの基底クラスを定義します
Base = declarative_base()

# ユーザーテーブルに対応するクラスを定義します
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    total_points = Column(Integer, nullable=False, default=0)

    # このユーザーに関連するフードロス記録を定義します
    records = relationship("FoodLossRecord", back_populates="user")
    
# 廃棄理由テーブルに対応するクラスを定義します
class LossReason(Base):
    __tablename__ = 'loss_reasons'
    
    id = Column(Integer, primary_key=True)
    reason_text = Column(String(255), nullable=False, unique=True)
    
    # この理由に関連するフードロス記録を定義します
    records = relationship("FoodLossRecord", back_populates="reason")

# フードロス記録テーブルに対応するクラスを定義します
class FoodLossRecord(Base):
    __tablename__ = 'food_loss_records'
    
    id = Column(Integer, primary_key=True)
    # 外部キー（FOREIGN KEY）を定義し、Userテーブルのidを参照します
    user_id = Column(Integer, ForeignKey('users.id'))
    item_name = Column(String(255), nullable=False)
    # REAL型は浮動小数点数を扱います
    weight_grams = Column(REAL, nullable=False)
    # 外部キー（FOREIGN KEY）を定義し、LossReasonテーブルのidを参照します
    loss_reason_id = Column(Integer, ForeignKey('loss_reasons.id'))
    # record_dateは日時を記録します
    record_date = Column(String(255), nullable=False, default=datetime.datetime.now)

    # ユーザーと廃棄理由への関係性を定義します
    user = relationship("User", back_populates="records")
    reason = relationship("LossReason", back_populates="records")