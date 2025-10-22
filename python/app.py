# app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for
from database import init_db, get_db
from models import User, LossReason, FoodLossRecord
import datetime
import hashlib
import json


app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')
# アプリケーション起動時にデータベースを初期化
init_db()

#ルート定義
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
                           today=today,
                           active_page='input'
                           )

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
                           next_week=next_week_date.strftime('%Y-%m-%d'),
                           active_page='log'
                           )

@app.route("/points")
def points():
    return render_template('points.html',
                           active_page='points'
                           )

@app.route("/knowledge")
def knowledge():
    return render_template('knowledge.html',
                           active_page='knowledge'
                           )

@app.route("/account")
def account():
    return render_template('account.html',
                           active_page='account'
                           )


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
            # たぶん使わない
            # record_date=datetime.datetime.now().isoformat()
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