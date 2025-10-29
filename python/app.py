# app.py (完成版)
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from database import init_db, get_db
from flask import session
from models import User, LossReason, FoodLossRecord
from pydantic import ValidationError # ★ ValidationErrorをインポート
from schemas import LossRecordInput # ★ LossRecordInputをインポート
from user_service import get_user_by_username, register_new_user, get_user_profile
from services import add_new_loss_record, calculate_weekly_points_logic
from services import get_user_profile
import datetime

# --- アプリケーション初期設定 ---
app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

app.secret_key = 'a_secure_and_complex_secret_key' 

init_db()

def login_required(func):
    """ログインしているかチェックするデコレータ"""
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__ # Flaskにルーティングを認識させる
    return wrapper

@app.route("/")
def index():
    return render_template('login.html')

@app.route("/home")
@login_required
def home():
    return render_template('home.html')

@app.route("/input")
@login_required
def input_page():
    return render_template('input.html', today=datetime.date.today())

@app.route("/log")
@login_required
def log_page():
    return render_template('log.html',)

@app.route("/points")
@login_required
def points_page():
    return render_template('points.html')

@app.route('/login', methods=['POST'])
def login():
    db = next(get_db())
    username = request.form.get('username')
    
    try:
        user = get_user_by_username(db, username) # Services層でユーザーを取得
        
        if user:
            # ★【テスト環境用】認証スキップとセッション保存 ★
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="ユーザーが見つかりません。")

    except Exception as e:
        return render_template('login.html', error=f"エラーが発生しました: {str(e)}")
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
        # これが必須項目の欠損、型、ビジネスルール（重量が負ではないか）を全てチェックします。
        validated_data = LossRecordInput(**data)
        
        # 2. Services層へ処理を渡す
        record_id = add_new_loss_record(db, validated_data.model_dump()) 
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

# --- サーバー実行 ---
if __name__ == "__main__":
    # Flaskサーバーを起動
    app.run(debug=True)
