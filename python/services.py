# services.py (冒頭部分の修正案)

from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, FoodLossRecord, LossReason
from schemas import LossRecordInput # schemas.pyで定義したPydanticスキーマをインポート
import hashlib # ★ 追加 (パスワードハッシュ化のため)
from datetime import datetime, timedelta # ★ timedeltaとdatetimeは既に使われているため、インポートを明確にする
from typing import Dict, Any, Tuple


# ★ get_last_two_weeks 関数を services.py の中で直接定義 ★
def get_last_two_weeks(today: datetime) -> Dict[str, Tuple[datetime, datetime]]:
    """
    今週と先週の月曜日と日曜日の日時境界を計算する。（自己完結型）
    """
    # 0=月曜日, 6=日曜日
    days_to_monday = today.weekday() 
    
    # 既存のロジックをそのまま使用
    days_since_monday = today.weekday() 
    this_monday = (today - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
    this_sunday = (this_monday + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
    last_monday = this_monday - timedelta(weeks=1)
    last_sunday = this_sunday - timedelta(weeks=1)

    return {
        "this_week": (this_monday, this_sunday),
        "last_week": (last_monday, last_sunday)
    }

# --- ユーザー関連サービス ---
# ... (他の関数が続く) ...
# --- ユーザー関連サービス ---

def register_new_user(db: Session, username: str, email: str, password: str) -> int:
    """
    新しいユーザーをデータベースに登録する。
    """
    # ユーザー名とメールアドレスの重複チェック
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        raise ValueError("ユーザー名またはメールアドレスは既に登録されています。")
    
    # パスワードをハッシュ化
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    new_user = User(
        username=username,
        email=email,
        password=hashed_password,
        total_points=0
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user.id

def get_user_by_username(db: Session, username: str) -> User | None:
    """
    ユーザー名でユーザーオブジェクトを取得する。
    """
    return db.query(User).filter_by(username=username).first()

def get_user_by_id(db: Session, user_id: int) -> User | None:
    """
    IDでユーザーオブジェクトを取得する。
    """
    return db.query(User).get(user_id)


def add_new_loss_record(db: Session, record_data: Dict[str, Any]) -> int:
    """
    検証済みの廃棄記録データ（辞書形式）をデータベースに挿入する。
    """
    # 🚨 Pydanticによる二重チェックのロジックを完全に削除
    
    # 2. 外部キー（LossReason）の存在チェックとID取得
    # record_data['reason_text'] を使って検索
    reason = db.query(LossReason).filter_by(reason_text=record_data['reason_text']).first()
    
    if not reason:
        # このエラーは app.py 側の Pydantic バリデーションで捕捉されるはずですが、DB側のチェックとして残します。
        raise ValueError(f"無効な廃棄理由: {record_data['reason_text']}")

    # 3. データベースへの挿入
    # 渡された辞書データ（record_data）をそのまま利用
    new_record = FoodLossRecord(
        user_id=record_data['user_id'],
        item_name=record_data['item_name'],
        weight_grams=record_data['weight_grams'],
        loss_reason_id=reason.id, # 外部キーIDを使用
        # notes=record_data.get('notes') # notes があればここに追加
    )
    
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    return new_record.id

def get_total_grams_for_week(db: Session, user_id: int, start_date: datetime, end_date: datetime) -> float:
    """
    指定された「月〜日」の一週間の合計廃棄重量を取得する。（ポイント計算用）
    これは、以前の statistics.py から移動・修正した関数です。
    """
    # データベースのレコード日付は文字列（ISO 8601）として保存されているため、文字列形式に変換
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    
    total_grams = db.query(func.sum(FoodLossRecord.weight_grams)) \
                      .filter(FoodLossRecord.user_id == user_id) \
                      .filter(FoodLossRecord.record_date >= start_str) \
                      .filter(FoodLossRecord.record_date <= end_str) \
                      .scalar()
                      
    return total_grams or 0.0

def get_total_grams_for_weeks(db: Session, user_id: int, weeks_ago: int) -> float:
    """
    ★この関数が statistics.py から移動する関数です★
    過去 N 週間分の合計廃棄重量（グラム）を取得する。
    """
    # ... (ロジックは statistics.py のものと同じものをここに貼り付け) ...
    today = datetime.now()
    start_point = today - timedelta(weeks=weeks_ago) 
    start_str = start_point.isoformat()
    
    total_grams = db.query(func.sum(FoodLossRecord.weight_grams)) \
                      .filter(FoodLossRecord.user_id == user_id) \
                      .filter(FoodLossRecord.record_date >= start_str) \
                      .filter(FoodLossRecord.record_date < today.isoformat()) \
                      .scalar()
                      
    return total_grams or 0.0

def calculate_weekly_points_logic(db: Session, user_id: int) -> Dict[str, Any]:
    """
    ユーザーの週次廃棄量を評価し、ポイントを計算・付与するメインロジック。
    「先週比」と「過去4週間平均比」の低い方の削減率を採用し、10%あたり1ポイント付与する。
    """
    
    today = datetime.now()
    # 既存のヘルパー関数（statistics.pyから移動した関数）を使って週の境界を取得
    # NOTE: get_last_two_weeks がこのファイル内、またはインポート済みである前提
    week_boundaries = get_last_two_weeks(today) 

    # --- 1. 週間の合計廃棄量を取得 ---
    this_week_grams = get_total_grams_for_week(db, user_id, *week_boundaries["this_week"])
    last_week_grams = get_total_grams_for_week(db, user_id, *week_boundaries["last_week"])
    
    # 過去4週間（先々週以前）の合計と平均を取得
    # get_total_grams_for_weeks も利用可能である前提
    past_four_weeks_grams = get_total_grams_for_weeks(db, user_id, 4) 
    
    # ベースライン（過去4週間の平均）を計算
    # (先週の量 + その前3週間の合計) / 4 として計算します
    base_line_grams = (last_week_grams + past_four_weeks_grams) / 4.0

    
    # --- 2. 削減率の計算 ---
    
    points_to_add = 0
    rate_last_week = 0.0 # 先週比削減率 (初期値: 0)
    rate_baseline = 0.0  # 平均比削減率 (初期値: 0)
    
    # a. 先週比の削減率を計算
    if last_week_grams > 0:
        rate_last_week = (last_week_grams - this_week_grams) / last_week_grams
    else:
        # 先週の廃棄がゼロの場合、今週もゼロなら削減率は0（ポイント0）
        # 今週廃棄があれば、rate_last_week は自動で 0 より小さくなる（ペナルティは今回はなし）
        rate_last_week = 0.0 if this_week_grams == 0 else -1.0 


    # b. ベースライン（平均）比の削減率を計算
    if base_line_grams > 0:
        rate_baseline = (base_line_grams - this_week_grams) / base_line_grams
    # ベースラインが0の場合、今週も0なら rate_baseline は 0

    
    # --- 3. 最終的な削減率とポイントの決定 ---
    
    # 2つの削減率のうち、小さい方（ユーザーにとって厳しい方）を採用
    final_reduction_rate = min(rate_last_week, rate_baseline)
    
    # 削減（final_reduction_rate > 0）がある場合のみポイントを計算
    if final_reduction_rate > 0:
        # 削減率 (例: 0.15 = 15%) を整数パーセントに変換
        reduction_percentage = int(final_reduction_rate * 100)
        
        # 削減率10%あたり1ポイントを計算 (例: 15%削減 -> 1ポイント)
        calculated_points = reduction_percentage // 10
        
        # 最大100ポイントの制限を適用
        points_to_add = min(calculated_points, 100)

    # 4. ポイントをデータベースに更新
    user = db.query(User).get(user_id)
    if user:
        user.total_points += points_to_add
        db.commit() # ★ Services層でDBコミットを実行 ★
        
    return {
        "points_added": points_to_add,
        "final_reduction_rate": round(final_reduction_rate * 100, 2),
        "rate_last_week": round(rate_last_week * 100, 2),
        "rate_baseline": round(rate_baseline * 100, 2)
    }
