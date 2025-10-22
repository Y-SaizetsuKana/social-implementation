# statistics.py
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import FoodLossRecord, LossReason # models.pyからインポート

def get_week_boundaries(today: datetime) -> tuple[datetime, datetime]:
    """
    指定された日付を含む「月曜日から日曜日まで」の一週間の境界を計算する。
    """
    # 0=月曜日, 6=日曜日
    days_to_monday = today.weekday() 
    
    # 週の始まり（月曜日 00:00:00）を計算
    start_of_week = today - timedelta(days=days_to_monday)
    monday = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 週の終わり（日曜日 23:59:59）を計算
    sunday = monday + timedelta(days=6)
    end_of_week = sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return monday, end_of_week

def calculate_weekly_statistics(db: Session, user_id: int) -> Dict[str, Any]:
    """
    直近の「月曜日始まり、日曜日終わり」の一週間について、
    廃棄された料理名リストと日別合計重量を計算する。
    """
    
    today = datetime.now()
    monday, sunday = get_week_boundaries(today)
    
    # データベースのレコード日付は文字列（ISO 8601）として保存されているため、文字列形式に変換
    monday_str = monday.isoformat()
    sunday_str = sunday.isoformat()

    # 1. 週間の全記録を取得 (日付フィルター)
    weekly_records = db.query(FoodLossRecord) \
                       .filter(FoodLossRecord.user_id == user_id) \
                       .filter(FoodLossRecord.record_date >= monday_str) \
                       .filter(FoodLossRecord.record_date <= sunday_str) \
                       .all()

    if not weekly_records:
        return {
            "week_start": monday.strftime('%Y-%m-%d'),
            "week_end": sunday.strftime('%Y-%m-%d'),
            "is_data_present": False,
            "dish_table": [],
            "daily_graph_data": []
        }

    # 2. 廃棄された料理名リスト (表データ) の作成
    # 料理名と廃棄量、理由のリストを作成
    dish_table_data = []
    for record in weekly_records:
        reason_text = db.query(LossReason.reason_text).filter(LossReason.id == record.loss_reason_id).scalar()
        
        dish_table_data.append({
            "id": record.id,
            "dish_name": record.item_name,
            "weight_grams": round(record.weight_grams, 1),
            "reason": reason_text if reason_text else "不明",
            "date": record.record_date[:10] # 日付部分 'YYYY-MM-DD' のみ抽出
        })
    
    # 3. 日別合計重量 (棒グラフデータ) の計算
    
    # SQLで日付ごとに合計重量を集計
    daily_summary = (
        db.query(
            func.substr(FoodLossRecord.record_date, 1, 10).label("date"),
            func.sum(FoodLossRecord.weight_grams).label("total_grams")
        )
        .filter(FoodLossRecord.user_id == user_id)
        .filter(FoodLossRecord.record_date >= monday_str)
        .filter(FoodLossRecord.record_date <= sunday_str)
        .group_by(func.substr(FoodLossRecord.record_date, 1, 10))
        .order_by("date")
        .all()
    )
    
    # 全曜日をカバーし、データがない日は 0 にする
    daily_graph_data = []
    current_date = monday
    for i in range(7):
        date_str = current_date.strftime('%Y-%m-%d')
        grams = 0.0
        
        # 集計結果から該当日のデータを探す
        for row in daily_summary:
            if row.date == date_str:
                grams = round(row.total_grams, 1)
                break
        
        daily_graph_data.append({
            "day": current_date.strftime('%a'), # 曜日名 (例: Mon, Tue)
            "date": date_str,
            "total_grams": grams
        })
        current_date += timedelta(days=1)
        
    return {
        "week_start": monday.strftime('%Y-%m-%d'),
        "week_end": sunday.strftime('%Y-%m-%d'),
        "is_data_present": True,
        "dish_table": dish_table_data,
        "daily_graph_data": daily_graph_data
    }

def get_total_grams_for_weeks(db: Session, user_id: int, weeks_ago: int) -> float:
    """
    過去 N 週間分の合計廃棄重量（グラム）を取得する。
    （weeks_ago=4なら、今週を含まない過去4週間を取得）
    """
    today = datetime.now()
    
    # 過去 N 週間の起点となる日時を計算
    # 例: 4週間前は today - 4週間
    start_point = today - timedelta(weeks=weeks_ago) 
    
    # データベースのレコード日付は文字列（ISO 8601）
    start_str = start_point.isoformat()
    
    total_grams = db.query(func.sum(FoodLossRecord.weight_grams)) \
                      .filter(FoodLossRecord.user_id == user_id) \
                      .filter(FoodLossRecord.record_date >= start_str) \
                      .filter(FoodLossRecord.record_date < today.isoformat()) \
                      .scalar()
                      
    return total_grams or 0.0
