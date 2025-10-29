# app.py (完成版)
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from database import init_db, get_db
from flask import session
from models import User, LossReason, FoodLossRecord
from pydantic import ValidationError # ★ ValidationErrorをインポート
from schemas import LossRecordInput # ★ LossRecordInputをインポート
from services import ( 
    register_new_user, 
    add_new_loss_record, 
    get_user_by_username, # ログイン認証用
    calculate_weekly_points_logic, # ポイント計算ロジック
    # ★ get_user_by_id など、services.pyで定義した関数は必要に応じてインポート
)
import datetime

# --- アプリケーション初期設定 ---
app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

# ★ 必須: セッションを使うためのSECRET_KEYを設定する ★
# 本番環境では環境変数から読み込む必要があります
app.secret_key = 'a_secure_and_complex_secret_key' 

# アプリケーション起動時にデータベースを初期化
init_db()

# --- 画面ルーティング ---
# ★ ログイン必須のチェック（セッション確認）を追加 ★
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

# --- 認証機能 ---

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

# --- サーバー実行 ---
if __name__ == "__main__":
    # Flaskサーバーを起動
    app.run(debug=True)