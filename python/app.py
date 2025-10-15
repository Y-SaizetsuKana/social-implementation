# app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for
from database import init_db, get_db
from flask import session
from models import User, LossReason, FoodLossRecord
from statistics import get_total_grams_for_week, get_last_two_weeks 
import datetime
import hashlib


app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')
# アプリケーション起動時にデータベースを初期化
init_db()

@app.route("/")
def index():
    return render_template('login.html')

@app.route("/home")
def home():
    return render_template('home.html')


@app.route("/input")
def input():
    today = datetime.date.today()
    return render_template('input.html',
                           today=today)

@app.route("/log")
def log():
    # --- 基準日の取得 ---
    # URLのクエリパラメータから日付を取得しようと試みる
    date_str = request.args.get('date')
    
    target_date = None
    if date_str:
        try:
            # 文字列をdateオブジェクトに変換
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            # フォーマットが不正な場合は今日の日付を使用
            target_date = datetime.date.today()
    else:
        # パラメータがなければ今日の日付を使用
        target_date = datetime.date.today()

    # --- 週の計算 ---
    # 基準日をもとに、その週の日曜日を計算
    start_of_week = target_date - datetime.timedelta(days=(target_date.weekday() + 1) % 7)
    end_of_week = start_of_week + datetime.timedelta(days=6)

    # --- 1週間分の日付リストを作成 ---
    week_dates = []
    jp_weekdays = ["日", "月", "火", "水", "木", "金", "土"]
    for i in range(7):
        current_day = start_of_week + datetime.timedelta(days=i)
        week_dates.append({
            "date": current_day,
            "day_num": current_day.day,
            "weekday_jp": jp_weekdays[(current_day.weekday() + 1) % 7]
        })

    # --- 前週と次週の日付を計算 ---
    # 表示している週の日曜から7日前と7日後を計算
    prev_week_date = start_of_week - datetime.timedelta(days=7)
    next_week_date = start_of_week + datetime.timedelta(days=7)

    # --- 表示用の日付範囲を作成 ---
    week_range_str = f"{start_of_week.month}月{start_of_week.day}日 〜 {end_of_week.month}月{end_of_week.day}日"

    # HTMLテンプレートにデータを渡してレンダリング
    return render_template('log.html',
                           today=datetime.date.today(), # 「今日」をハイライトするために別途渡す
                           week_dates=week_dates,
                           week_range=week_range_str,
                           prev_week=prev_week_date.strftime('%Y-%m-%d'),
                           next_week=next_week_date.strftime('%Y-%m-%d'))

@app.route("/points")
def points():
    return render_template('points.html')

@app.route("/knowledge")
def knowledge():
    return render_template('knowledge.html')

@app.route("/account")
def account():
    return render_template('account.html')


@app.route("/api/register_user", methods=["POST"])
def register_user():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all([username, email, password]):
        return jsonify({"message": "Username, email, and password are required."}), 400

    db = next(get_db())
    try:
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

        return jsonify({"message": "User registered successfully!", "user_id": new_user.id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500
    finally:
        db.close()

    
# 廃棄記録を追加するAPI
@app.route("/api/add_loss_record", methods=["POST"])
def add_loss_record():
    data = request.get_json()
    user_id = data.get("user_id")
    item_name = data.get("item_name")
    weight_grams = data.get("weight_grams")
    reason_text = data.get("reason_text")

    if not all([user_id, item_name, weight_grams, reason_text]):
        return jsonify({"message": "All fields are required."}), 400

    db = next(get_db())
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"message": "User not found."}), 404

        reason = db.query(LossReason).filter_by(reason_text=reason_text).first()
        if not reason:
            return jsonify({"message": "Invalid loss reason."}), 400

        new_record = FoodLossRecord(
            user_id=user.id,
            item_name=item_name,
            weight_grams=weight_grams,
            loss_reason_id=reason.id,
        )
        
        db.add(new_record)
        db.commit()

        return jsonify({"message": "Record added successfully!", "record_id": new_record.id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500
    finally:
        db.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # ここでユーザー名とパスワードのチェックを行う（今回は省略）
        username = request.form.get('username')
        
        if username: # ログイン成功とみなす 
            return redirect(url_for('log'))
        else:
            # ログイン失敗
            return "ログインに失敗しました"
            
    return render_template('account.html')

if __name__ == "__main__":
    app.run(debug=True)


@app.route("/api/calculate_weekly_points", methods=["POST"])
def calculate_weekly_points():
    """「先週比」と「過去4週間平均比」の低い方の削減率に基づいてポイントを付与するAPI。"""
    user_id = session.get('user_id') 
    if not user_id:
        return jsonify({"message": "認証が必要です。"}), 401 
    
    db = next(get_db())
    try:
        today = datetime.now()
        week_boundaries = get_last_two_weeks(today) # 今週と先週の境界

        # --- 1. 週間の合計廃棄量を取得 ---
        this_week_grams = get_total_grams_for_week(db, user_id, *week_boundaries["this_week"])
        last_week_grams = get_total_grams_for_week(db, user_id, *week_boundaries["last_week"])
        
        # 過去4週間（先々週以前）の合計と平均を取得
        # 過去4週間の合計 (今週を含まない過去4週間、つまり last_week_grams を含めない)
        past_four_weeks_grams = get_total_grams_for_weeks(db, user_id, 4) 
        
        # 過去4週間の平均を計算 (last_week_grams + その前の3週間の平均)
        # ここではシンプルに「先週＋その前3週」の合計 / 4として計算する
        # ★ ベースラインの定義: 過去4週間（先週＋その前3週）の平均値
        base_line_grams = (last_week_grams + get_total_grams_for_weeks(db, user_id, 4)) / 4.0

        
        # --- 2. 削減率の計算 ---
        
        # 初期値
        rate_last_week = -1.0 # 先週比削減率（デフォルトは増加扱い）
        rate_baseline = -1.0  # 平均比削減率（デフォルトは増加扱い）
        
        # a. 先週比の削減率を計算
        if last_week_grams > 0:
            rate_last_week = (last_week_grams - this_week_grams) / last_week_grams
        
        # b. ベースライン（平均）比の削減率を計算
        if base_line_grams > 0:
            rate_baseline = (base_line_grams - this_week_grams) / base_line_grams

        
        # --- 3. 最終的な削減率とポイントの決定 ---
        
        points_to_add = 0
        
        # 2つの削減率のうち、小さい方（低い方、ユーザーにとって厳しい方）を採用
        final_reduction_rate = min(rate_last_week, rate_baseline)
        
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
            db.commit()
            
        return jsonify({
            "message": "週次ポイントを計算・付与しました。",
            "points_added": points_to_add,
            "final_reduction_rate": round(final_reduction_rate * 100, 2),
            "rate_last_week": round(rate_last_week * 100, 2),
            "rate_baseline": round(rate_baseline * 100, 2)
        }), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({"message": f"ポイント計算中にエラーが発生しました: {str(e)}"}), 500
    finally:
        db.close()