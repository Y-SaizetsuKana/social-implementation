# app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from models import User, LossReason, FoodLossRecord
from schemas import LossRecordInput # ★ LossRecordInputをインポート
from services import calculate_weekly_points_logic, add_new_loss_record_direct, get_weekly_stats, get_all_loss_reasons
from datetime import datetime
from database import init_db, get_db
from pydantic import ValidationError # ★ ValidationErrorをインポート
from statistics import get_total_grams_for_weeks, get_last_two_weeks 
from user_service import get_user_by_username, register_new_user, get_user_profile
import datetime

# --- アプリケーション初期設定 ---
app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

app.secret_key = 'a_secure_and_complex_secret_key' 
init_db()

#未実装
def login_required(func):
    """ログインしているかチェックするデコレータ"""
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__ # Flaskにルーティングを認識させる
    return wrapper

@app.route("/")
def index():
    # ログイン済みであれば、直接 /input へリダイレクト
    if 'user_id' in session:
        return redirect(url_for('input'))
        
    # ログインしていなければ、login.html を表示
    return render_template('login.html')


# app.py (input 関数のみ修正)

@app.route("/input", methods=['GET', 'POST']) 
@login_required # デコレータを適用
# app.py (input 関数内の POST 処理部分のみ修正)
def input():
    # --- POSTリクエスト（フォーム送信時）の処理 ---
    if request.method == 'POST':
        user_id = session.get('user_id')
        db = next(get_db())

        try:
            # 1. フォームデータ取得と検証
            form_data = request.form.to_dict()
            form_data['user_id'] = user_id
            validated_data = LossRecordInput(**form_data)
            
            # 2. データベース挿入
            record_id = add_new_loss_record_direct(db, validated_data.model_dump())
            
            # ★ 成功時のリダイレクト（ここで関数が終了し、302を返す）★
            return redirect(url_for('input', success_message='記録が完了しました！'))

        except ValidationError as e:
            db.close()
            # 失敗時: render_template で処理を終了
            return render_template('input.html', 
                                   today=datetime.date.today(), 
                                   error_message='入力内容に誤りがあります。',
                                   details=e.errors())
        
        except Exception as e:
            db.rollback()
            db.close()
            # サーバーエラー時: render_template で処理を終了
            return render_template('input.html', 
                                   today=datetime.date.today(), 
                                   error_message=f"サーバーエラーが発生しました: {str(e)}")
        
    # --- GETリクエスト（画面表示時）の処理 ---
    # POST処理がスキップされた場合（GETの場合）のみ、このロジックが実行される
    today = datetime.date.today()
    success_message = request.args.get('success_message')

    return render_template('input.html',
                           today=today,
                           active_page='input',
                           success_message=success_message)


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

@app.route("/points", methods=['GET', 'POST'])
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


@app.route('/login', methods=['POST'])
def login():
    db = next(get_db())
    username = request.form.get('username')
    # パスワードはフォームから取得するが、現時点では使用しない（本番環境化で利用）
    # password = request.form.get('password') 
    
    # 1. ユーザー名が空欄でないかの必須チェック
    # .strip() は、スペースのみの入力も空欄とみなす
    if not username or not username.strip():
        db.close()
        return render_template('login.html', error="ユーザー名を入力してください。")
    
    try:
        # 2. ユーザーの存在チェック
        user = get_user_by_username(db, username)
        
        if user:
            # 【テスト環境用】: パスワードチェックをスキップし、ユーザーの存在のみでログイン成功と見なす
            session['user_id'] = user.id
            return redirect(url_for('input')) # ログイン成功後、入力画面へリダイレクト
        else:
            # ユーザーが存在しないため、ログイン失敗
            return render_template('login.html', error="ユーザー名またはパスワードが間違っています。")

    except Exception as e:
        # データベース接続などの例外処理
        print(f"ログイン中にエラーが発生しました: {str(e)}")
        return render_template('login.html', error=f"サーバーエラー: {str(e)}")
    finally:
        db.close()

# --- API: ユーザー登録 ---
@app.route("/api/register_user", methods=["POST"])
def register_user_api():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all([username, email, password]):
        return jsonify({"message": "すべての情報が必要です。"}), 400

    db = next(get_db())
    try:
        # ★ Services層を呼び出し、DB操作を任せる ★
        user_id = register_new_user(db, username, email, password)

        return jsonify({"message": "登録完了！", "user_id": user_id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"message": f"登録エラー: {str(e)}"}), 500
    finally:
        db.close()
    
@app.route("/api/add_loss_record", methods=["POST"])
def add_loss_record_api():
    # ユーザーIDはセッションから取得する (最優先)
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "認証が必要です。再ログインしてください。"}), 401 

    data = request.get_json()
    data['user_id'] = user_id # Services層に渡すデータに user_id を追加
    
    # 必須項目チェック (手動チェックは削除)
    
    db = next(get_db())
    try:
        # ★ 1. Pydanticでデータの検証と型変換を一度に行う ★
        validated_data = LossRecordInput(**data)
        
        # 2. Services層へ処理を渡す
        record_id = add_new_loss_record_direct(db, validated_data.model_dump())
        # NOTE: validated_data.model_dump() でPydanticオブジェクトをPython辞書に変換して渡す

        return jsonify({"message": "記録完了！", "record_id": record_id}), 201
        
    except ValidationError as e:
        # ★ Pydanticのエラーを捕捉し、422を返す ★
        return jsonify({"message": "入力データが無効です", "details": e.errors()}), 422 # 422 Unprocessable Entity
    except Exception as e:
        db.rollback()
        return jsonify({"message": f"記録エラー: {str(e)}"}), 500
    finally:
        db.close()
        
# --- API: 週次ポイント計算 ---
@app.route("/api/calculate_weekly_points", methods=["POST"])
def calculate_weekly_points_api():
    user_id = session.get('user_id') 
    if not user_id:
        return jsonify({"message": "認証が必要です。"}), 401 
    
    db = next(get_db())
    try:
        today = datetime.now()
        week_boundaries = get_last_two_weeks(today) # 今週と先週の境界

        # --- 1. 週間の合計廃棄量を取得 ---
        this_week_grams = get_total_grams_for_weeks(db, user_id, *week_boundaries["this_week"])
        last_week_grams = get_total_grams_for_weeks(db, user_id, *week_boundaries["last_week"])
        # ★ Services層を呼び出し、ロジックを実行させる ★
        result = calculate_weekly_points_logic(db, user_id)
        
        return jsonify({
            "message": "週次ポイントを計算・付与しました。",
            **result
        }), 200
        
    except Exception as e:
        db.rollback()
        return jsonify({"message": f"ポイント計算中にエラーが発生しました: {str(e)}"}), 500
    finally:
        db.close()

@app.route("/api/loss_reasons", methods=["GET"])
def get_loss_reasons_api():
    """フロントエンドのドロップダウンリスト用の廃棄理由を返すAPI"""
    db = next(get_db())
    try:
        # Services層の関数を呼び出す
        reasons_list = get_all_loss_reasons(db)
        
        return jsonify({"reasons": reasons_list}), 200
    except Exception as e:
        return jsonify({"message": f"理由の取得中にエラーが発生しました: {str(e)}"}), 500
    finally:
        db.close()

@app.route("/api/user/me", methods=["GET"])
def get_user_profile_api():
    """ログイン中のユーザーのプロフィール情報を返すAPI"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"message": "認証が必要です。"}), 401
    
    db = next(get_db())
    try:
        profile_data = get_user_profile(db, user_id)
        
        if not profile_data:
            return jsonify({"message": "ユーザーが見つかりません。"}), 404
        
        return jsonify(profile_data), 200
    except Exception as e:
        return jsonify({"message": f"プロフィールの取得中にエラーが発生しました: {str(e)}"}), 500
    finally:
        db.close()

@app.route("/api/weekly_stats", methods=["GET"])
def get_weekly_stats_api():
    user_id = session.get('user_id') 
    if not user_id:
        return jsonify({"message": "認証が必要です。"}), 401 

    # URLクエリパラメータから基準日を取得
    date_str = request.args.get('date')
    target_date = datetime.date.today()
    if date_str:
        try:
            # log.htmlが渡す 'YYYY-MM-DD' 形式を解析
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass # 不正な場合は今日の日付を使用

    db = next(get_db())
    try:
        # Services層を呼び出し、週次データを取得
        stats_data = get_weekly_stats(db, user_id, target_date)
        
        return jsonify(stats_data), 200
        
    except Exception as e:
        return jsonify({"message": f"統計データの取得中にエラーが発生しました: {str(e)}"}), 500
    finally:
        db.close()

@app.route("/register")
def register_page():
    return render_template('register.html')

# --- サーバー実行 ---
if __name__ == "__main__":
    # Flaskサーバーを起動
    app.run(debug=True)
