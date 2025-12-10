# services.py (冒頭部分の修正案)
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, FoodLossRecord, LossReason
from schemas import LossRecordInput
import hashlib 
from datetime import datetime, timedelta , date, time
from typing import Dict, Any, List, Optional, Tuple # Tuple, List, Optional を忘れずにインポート
from statistics import (
    get_week_boundaries,
    get_total_grams_for_week,
    get_total_grams_for_weeks,
    get_last_two_weeks, # ★ この行を追加 ★
    # calculate_weekly_statistics (※統計表示用なのでservicesでは不要)
)

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
    start_of_week = target_date - timedelta(days=(target_date.weekday() + 1) % 7)
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week

def get_start_and_end_of_week(target_date: date) -> Tuple[date, date]:
    """与えられた日付を含む週の日曜と土曜を返す (日曜日を週の始まりとする)。"""
    # target_date.weekday() は月曜(0)から日曜(6)
    start_of_week = target_date - timedelta(days=(target_date.weekday() + 1) % 7)
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week

def get_weekly_stats(db: Session, user_id: int, target_date: date) -> Dict[str, Any]:
    """
    指定された日付を含む週の統計データ（グラフ用、表用）を取得し、JSが期待する形式に整形する。
    """
    # target_dateから週の始まりと終わり（日曜〜土曜）を計算
    date_start_of_week, date_end_of_week = get_start_and_end_of_week(target_date)

    # 1. データベースクエリ用のISO文字列境界を作成
    datetime_start = datetime.combine(date_start_of_week, time.min)
    datetime_end = datetime.combine(date_end_of_week, time.max)
    
    start_str = datetime_start.isoformat()
    end_str = datetime_end.isoformat()
    
    # 2. 週間記録を全て取得
    records = db.query(FoodLossRecord, LossReason.reason_text) \
        .join(LossReason) \
        .filter(
            FoodLossRecord.user_id == user_id,
            # ISO文字列で比較することで、範囲内の全てのタイムスタンプを捕捉
            FoodLossRecord.record_date.between(start_str, end_str) 
        ) \
        .order_by(FoodLossRecord.record_date) \
        .all()
        
    # 2-b. 週間廃棄品目一覧のデータを作成 (テーブル用)
    dish_table_data = [
        {
            # 日付を 'MM/DD' 形式に変換
            "date": datetime.fromisoformat(rec.FoodLossRecord.record_date).strftime('%m/%d'),
            "dish_name": rec.FoodLossRecord.item_name,
            # 小数点以下1桁に丸める
            "weight_grams": round(rec.FoodLossRecord.weight_grams, 1), 
            "reason": rec.reason_text
        }
        for rec in records
    ]
    
    # --- 3. 日別合計グラム数を計算 (Pythonで集計) ---
    # キー: YYYY-MM-DD
    daily_grams_aggregation = {}
    for rec in records:
        # レコードの日付部分を取得
        record_date = datetime.fromisoformat(rec.FoodLossRecord.record_date).date()
        date_str = record_date.strftime('%Y-%m-%d')
        grams = rec.FoodLossRecord.weight_grams
        
        daily_grams_aggregation[date_str] = daily_grams_aggregation.get(date_str, 0.0) + grams
        
    # --- 4. 全曜日をカバーし、グラフデータを作成 (日曜始まりで順序を保証) ---
    daily_graph_data = []
    jp_weekdays = ["日", "月", "火", "水", "木", "金", "土"]
    current_date = date_start_of_week # 日曜日から開始
    for i in range(7):
        date_str = current_date.strftime('%Y-%m-%d')
        # i=0が日曜日、i=6が土曜日
        day_name = jp_weekdays[i]
        
        # 該当日の合計を取得（データがなければ 0.0）
        grams = round(daily_grams_aggregation.get(date_str, 0.0), 1)
        
        daily_graph_data.append({
            "day": day_name, 
            "total_grams": grams
        })
        current_date += timedelta(days=1) # 次の日へ
    
    # 5. 最終的なレスポンス形式に整形
    is_data_present = len(records) > 0

    return {
        "is_data_present": is_data_present,
        "week_start": date_start_of_week.strftime('%Y-%m-%d'),
        "daily_graph_data": daily_graph_data,
        "dish_table": dish_table_data
    }

def add_test_loss_records(db: Session, user_id: int) -> bool:
    """
    ユーザーのフードロス記録がまだ存在しない場合、テストデータを挿入する。
    """
    # 既にレコードが存在するかチェックし、存在する場合は挿入をスキップ
    if db.query(FoodLossRecord).filter_by(user_id=user_id).first():
        print(f"User {user_id} already has records. Skipping test data insertion.")
        return False
    
    # LossReasonのIDを取得
    # NOTE: database.pyのinit_db()で以下の理由が投入されていることを前提とする
    reason_expired = db.query(LossReason).filter_by(reason_text="期限切れ").first()
    reason_eaten = db.query(LossReason).filter_by(reason_text="料理後の廃棄").first()
    
    if not reason_expired or not reason_eaten:
        print("Error: Loss reasons not found. Cannot insert test data.")
        return False
        
    # テストデータを挿入する日付を決定
    today = datetime.now()
    # 記録を過去の任意の日付（例：5日前と3日前）で作成し、今週の統計に反映されるようにする
    a_week_ago = today - timedelta(days=7)

    records = [
        FoodLossRecord(
            user_id=user_id,
            item_name="牛乳 (期限切れ)",
            weight_grams=1000.0,
            loss_reason_id=reason_expired.id,
            # ISOフォーマット文字列に変換して挿入
            record_date=a_week_ago.isoformat()
        ),
        FoodLossRecord(
            user_id=user_id,
            item_name="カレーの食べ残し",
            weight_grams=350.5,
            loss_reason_id=reason_eaten.id,
            record_date=a_week_ago.isoformat()
        ),
        FoodLossRecord(
            user_id=user_id,
            item_name="ご飯 (期限切れ)",
            weight_grams=500.0,
            loss_reason_id=reason_expired.id,
            record_date=today.isoformat()
        )
    ]
    
    db.add_all(records)
    db.commit()
    print(f"Inserted {len(records)} test records for user {user_id}.")
    return True