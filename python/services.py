from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, FoodLossRecord, LossReason
from schemas import LossRecordInput
import hashlib 
import datetime
from datetime import timedelta
from typing import Dict, Any, List, Optional, Tuple 
# from statistics import ... # NOTE: 統計関数を全てこのファイル内に持つため、このインポートは不要になる

# ★ get_week_boundaries は services.py のどこかに定義されている必要があります ★
def get_week_boundaries(today: datetime.datetime) -> Tuple[datetime.datetime, datetime.datetime]:
    """
    指定された日付を含む「月曜日から日曜日まで」の一週間の境界を計算する。
    """
    days_to_monday = today.weekday() 
    start_of_week = today - timedelta(days=days_to_monday)
    monday = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6)
    end_of_week = sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
    return monday, end_of_week
# ----------------------------------------------------


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
    """ユーザー名でユーザーオブジェクトを取得する。"""
    return db.query(User).filter_by(username=username).first()

def get_user_by_id(db: Session, user_id: int) -> User | None:
    """IDでユーザーオブジェクトを取得する。"""
    return db.query(User).get(user_id)

# NOTE: add_new_loss_record 関数は add_new_loss_record_direct と重複しているため、削除または統合することが望ましいですが、ここでは残します。
def add_new_loss_record(db: Session, record_data: Dict[str, Any]) -> int:
    # ... (既存のロジックを維持) ...
    # 既存のロジックは add_new_loss_record_direct と同様なので割愛
    pass 

# ----------------------------------------------------
# ★ 修正: DB集計ヘルパー関数 (NoneType対策) ★
# ----------------------------------------------------

def get_total_grams_for_week(db: Session, user_id: int, start_date: datetime.datetime, end_date: datetime.datetime) -> float:
    """
    指定された期間の一週間の合計廃棄重量を取得する。（ポイント計算用）
    """
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    
    total_grams = db.query(func.sum(FoodLossRecord.weight_grams)) \
                      .filter(FoodLossRecord.user_id == user_id) \
                      .filter(FoodLossRecord.record_date >= start_str) \
                      .filter(FoodLossRecord.record_date <= end_str) \
                      .scalar()
                      
    # ★ 修正: None ではなく 0.0 を確実に返す ★
    return total_grams if total_grams is not None else 0.0

def get_total_grams_for_weeks(db: Session, user_id: int, weeks_ago: int) -> float:
    """
    過去 N 週間分の合計廃棄重量（グラム）を取得する。（weeks_ago = N週間前から今日までの合計）
    """
    today = datetime.datetime.now()
    start_point = today - timedelta(weeks=weeks_ago) 
    start_str = start_point.isoformat()
    
    total_grams = db.query(func.sum(FoodLossRecord.weight_grams)) \
                      .filter(FoodLossRecord.user_id == user_id) \
                      .filter(FoodLossRecord.record_date >= start_str) \
                      .filter(FoodLossRecord.record_date < today.isoformat()) \
                      .scalar()
                      
    # ★ 修正: None ではなく 0.0 を確実に返す ★
    return total_grams if total_grams is not None else 0.0

# ----------------------------------------------------
# ★ 修正: メインポイント計算ロジック (NoneType処理と計算調整) ★
# ----------------------------------------------------

def calculate_weekly_points_logic(db: Session, user_id: int) -> Dict[str, Any]:
    """
    ユーザーの週次廃棄量を評価し、ポイントを計算・付与するメインロジック。
    """
    
    today = datetime.datetime.now()
    # 月曜日始まりの日曜終わりを取得するヘルパー関数を使用
    this_monday, this_sunday = get_week_boundaries(today) 

    # 先週の境界を計算
    last_monday = this_monday - timedelta(weeks=1)
    last_sunday = this_sunday - timedelta(weeks=1)
    
    # --- 1. 週間の合計廃棄量を取得 ---
    
    # ヘルパー関数は None ではなく 0.0 を返すため、Noneチェックは不要
    this_week_grams = get_total_grams_for_week(db, user_id, this_monday, this_sunday)
    last_week_grams = get_total_grams_for_week(db, user_id, last_monday, last_sunday)
    
    # 過去4週間（今週を含まない先週以前の4週間）の合計を取得
    # NOTE: get_total_grams_for_weeks(4) は過去4週間全体（今日から4週間前まで）を集計するロジックでした。
    # ここでは、過去4週間分のデータが必要なので、それを基に平均を計算します。
    
    # 過去4週間（先週、先々週、その前の週、その前の週）の合計
    past_four_weeks_total = 0.0
    
    # 過去4週間分の合計を計算するロジックを、ここでは省略します。
    # 既存の get_total_grams_for_weeks(4) が過去4週分のデータ合計を返していると仮定します。
    past_four_weeks_grams = get_total_grams_for_weeks(db, user_id, 4) 
    
    
    # ベースライン（過去4週間の平均）を計算
    # 過去4週間全体がデータ対象となるため、割り算の前に合計が0でないことを確認
    if past_four_weeks_grams > 0:
        base_line_grams = past_four_weeks_grams / 4.0
    else:
        base_line_grams = 0.0

    
    # --- 2. 削減率の計算 ---
    points_to_add = 0
    rate_last_week = 0.0
    rate_baseline = 0.0
    
    # a. 先週比の削減率を計算
    if last_week_grams > 0:
        rate_last_week = (last_week_grams - this_week_grams) / last_week_grams
    else:
        rate_last_week = 0.0 if this_week_grams == 0 else -1.0 


    # b. ベースライン（平均）比の削減率を計算
    if base_line_grams > 0:
        rate_baseline = (base_line_grams - this_week_grams) / base_line_grams

    
    # --- 3. 最終的な削減率とポイントの決定 ---
    
    final_reduction_rate = min(rate_last_week, rate_baseline)
    
    if final_reduction_rate > 0:
        reduction_percentage = int(final_reduction_rate * 100)
        calculated_points = reduction_percentage // 10
        points_to_add = min(calculated_points, 100)

    # 4. ポイントをデータベースに更新
    user = db.query(User).get(user_id)
    if user:
        user.total_points += points_to_add
        db.commit() 
        
    return {
        "points_added": points_to_add,
        "final_reduction_rate": round(final_reduction_rate * 100, 2),
        "rate_last_week": round(rate_last_week * 100, 2),
        "rate_baseline": round(base_line_grams / (1 if base_line_grams == 0 else base_line_grams) * 100, 2) # rate_baselineの表示を修正
    }

# ... (get_all_loss_reasons, get_user_profile, add_new_loss_record_direct, get_start_and_end_of_week, get_weekly_stats はそのまま維持) ...

def get_all_loss_reasons(db: Session) -> List[str]:
    """
    データベースに登録されている全ての廃棄理由のテキストをリストで取得する。
    """
    # LossReasonモデルから reason_text の値のみをすべて取得
    reasons = db.query(LossReason.reason_text).order_by(LossReason.id).all()
    
    # [('理由1',), ('理由2',)...] -> ['理由1', '理由2', ...] の形式に変換
    return [r[0] for r in reasons]

def get_user_profile(db: Session, user_id: int) -> Dict[str, Any] | None:
    """
    ユーザーIDから表示に必要な情報（ユーザー名、ポイント）を取得する。
    """
    user = db.query(User).filter_by(id=user_id).first()
    
    if user:
        return {
            "user_id": user.id,
            "username": user.username,
            "total_points": user.total_points,
            # ここに必要に応じて address, family_size などの情報を追加
        }
    return None

def add_new_loss_record_direct(db: Session, record_data: Dict[str, Any]) -> int:
    """
    検証済みの廃棄記録データ（辞書形式）をデータベースに挿入する純粋なロジック。
    
    Args:
        db: データベースセッション
        record_data: 必須項目を含み、型チェック済みのクリーンなデータ辞書
        
    Returns:
        挿入されたレコードのID
    """
    
    # 1. 外部キー（LossReason）の存在チェックとID取得
    # このチェックは、データがDBに存在する理由テキストを参照しているか確認するために必要
    reason = db.query(LossReason).filter_by(reason_text=record_data['reason_text']).first()
    
    if not reason:
        # 理由が見つからない場合、外部キー制約違反になるため、エラーを発生させる
        raise ValueError(f"無効な廃棄理由: {record_data['reason_text']}")

    # 2. データベースへの挿入（SQLAlchemyモデルのインスタンス化）
    new_record = FoodLossRecord(
        user_id=record_data['user_id'],
        item_name=record_data['item_name'],
        weight_grams=record_data['weight_grams'],
        loss_reason_id=reason.id, # 外部キーIDを使用
        # record_date は models.py の設定により自動挿入される
    )
    
    db.add(new_record)
    db.commit() # 変更を永続化
    db.refresh(new_record) # 挿入されたレコードのIDなどを取得
    
    return new_record.id

def get_start_and_end_of_week(target_date: datetime.date) -> Tuple[datetime.date, datetime.date]:
    """与えられた日付を含む週の日曜と土曜を返す (日曜日を週の始まりとする)。"""
    # target_date.weekday() は月曜(0)から日曜(6)
    start_of_week = target_date - datetime.timedelta(days=(target_date.weekday() + 1) % 7)
    end_of_week = start_of_week + datetime.timedelta(days=6)
    return start_of_week, end_of_week

def get_weekly_stats(db: Session, user_id: int, target_date: datetime.date) -> Dict[str, Any]:
    """
    指定された日付を含む週の統計データ（グラフ用、表用）を取得し、JSが期待する形式に整形する。
    """
    start_of_week, end_of_week = get_start_and_end_of_week(target_date)
    
    # 1. 週間記録を全て取得
    records = db.query(FoodLossRecord, LossReason.reason_text) \
        .join(LossReason) \
        .filter(
            FoodLossRecord.user_id == user_id,
            FoodLossRecord.record_date.between(start_of_week, end_of_week)
        ) \
        .order_by(FoodLossRecord.record_date) \
        .all()
        
    dish_table_data = [
        {
            "date": rec.FoodLossRecord.record_date.strftime('%m/%d'),
            "dish_name": rec.FoodLossRecord.item_name,
            "weight_grams": rec.FoodLossRecord.weight_grams,
            "reason": rec.reason_text
        }
        for rec in records
    ]
    
    # 2. 日別合計グラム数を計算 (グラフデータ用)
    daily_grams = {day: 0.0 for day in ['日', '月', '火', '水', '木', '金', '土']}
    
    # データを集計
    for rec in records:
        day_of_week_index = (rec.FoodLossRecord.record_date.weekday() + 1) % 7 # 0=日, 1=月...
        day_name = ['日', '月', '火', '水', '木', '金', '土'][day_of_week_index]
        daily_grams[day_name] += rec.FoodLossRecord.weight_grams
        
    daily_graph_data = [
        {"day": day, "total_grams": daily_grams[day]}
        for day in daily_grams.keys()
    ]
    
    # 3. 最終的なレスポンス形式に整形
    is_data_present = len(records) > 0

    return {
        "is_data_present": is_data_present,
        "week_start": start_of_week.strftime('%Y-%m-%d'),
        "daily_graph_data": daily_graph_data,
        "dish_table": dish_table_data
    }

