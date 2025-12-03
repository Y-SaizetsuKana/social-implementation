# app.py 
from flask import Flask, request, jsonify, render_template, make_response, redirect, url_for, session
from database import init_db, get_db
from flask import session
from models import User, LossReason, FoodLossRecord
from statistics import get_total_grams_for_weeks, get_last_two_weeks 
from pydantic import ValidationError # ★ ValidationErrorをインポート
from schemas import LossRecordInput # ★ LossRecordInputをインポート
from services import ( 
    register_new_user, 
    add_new_loss_record, 
    get_user_by_username, # ログイン認証用
    calculate_weekly_points_logic, # ポイント計算ロジック
    get_user_by_id
    # ★ get_user_by_id など、services.pyで定義した関数は必要に応じてインポート
)
from datetime import datetime, timedelta, timezone
from knowledge import bp as knowledge_bp

# --- アプリケーション初期設定 ---
app = Flask(__name__,
            template_folder='../templates',
            static_folder='../static')

app.register_blueprint(knowledge_bp)

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
        
        # --- ★デバッグ用に追加 (ここから)★ ---
        print(f"--- デコレータ実行 ({func.__name__}) ---")
        print(f"現在のセッション: {session}")
        # --- ★デバッグ用に追加 (ここまで)★ ---

        if 'user_id' not in session:
            print("セッションに user_id が見つからないため /login へリダイレクトします") # ★デバッグ用
            return redirect(url_for('login'))
        
        print("セッションOK。ページを表示します。") # ★デバッグ用
        return func(*args, **kwargs)
    
    wrapper.__name__ = func.__name__ 
    return wrapper

@app.route("/")
def index():
    # もしセッションに 'user_id' が存在する場合 (＝ログイン済みの場合)
    if 'user_id' in session:
        # ログインページではなく、入力ページにリダイレクトする
        return redirect(url_for('input'))
    
    # ログインしていない場合のみ、login.html を表示する
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    GET: アカウント作成ページを表示
    POST: アカウント作成処理を実行
    """
    
    # --- POSTリクエスト（フォームが送信された）の場合 ---
    if request.method == 'POST':
        # 1. フォームからデータを取得
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')

        # 2. バリデーション（入力チェック）
        if not all([email, username, password, password_confirm]):
            return render_template('register.html', error="すべての項目を入力してください。")
        
        if password != password_confirm:
            return render_template('register.html', error="パスワードが一致しません。")
        
        # 3. データベース処理
        db = next(get_db())
        try:
            # 4. Services層を呼び出して登録
            register_new_user(db, username, email, password)
            
            # 5. 成功したらログインページにリダイレクト
            # (注: ここで自動的にログインさせることも可能ですが、
            #  まずは登録後に手動でログインする流れにします)
            return redirect(url_for('login'))

        except ValueError as e:
            # 6. サービス層からのエラー（重複など）をキャッチ
            db.rollback()
            return render_template('register.html', error=str(e))
        except Exception as e:
            # その他のDBエラーなど
            print(f"致命的なエラーが発生しました: {e}") # ⬅︎ 追加
            db.rollback()
            return render_template('register.html', error=f"エラーが発生しました: {str(e)}")
        finally:
            db.close()

    # --- GETリクエスト（ページにアクセスした）の場合 ---
    return render_template('register.html')



@app.route("/input")
@login_required
def input():
    today = datetime.today().date()
    return render_template('input.html',
                           today=today,
                           active_page='input'
                           )


@app.route("/log")
@login_required
def log():
    # --- 基準日の取得 ---
    # URLのクエリパラメータから日付を取得しようと試みる
    date_str = request.args.get('date')
    
    target_date = None
    if date_str:
        try:
            # 文字列をdateオブジェクトに変換
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            # フォーマットが不正な場合は今日の日付を使用
            target_date = datetime.today().date()
    else:
        # パラメータがなければ今日の日付を使用
        target_date = datetime.today().date()

    # --- 週の計算 ---
    # 基準日をもとに、その週の日曜日を計算
    start_of_week = target_date - timedelta(days=(target_date.weekday() + 1) % 7)
    end_of_week = start_of_week + timedelta(days=6)

    # --- 1週間分の日付リストを作成 ---
    week_dates = []
    jp_weekdays = ["日", "月", "火", "水", "木", "金", "土"]
    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        week_dates.append({
            "date": current_day,
            "day_num": current_day.day,
            "weekday_jp": jp_weekdays[(current_day.weekday() + 1) % 7]
        })

    # --- 前週と次週の日付を計算 ---
    # 表示している週の日曜から7日前と7日後を計算
    prev_week_date = start_of_week - timedelta(days=7)
    next_week_date = start_of_week + timedelta(days=7)

    # --- 表示用の日付範囲を作成 ---
    week_range_str = f"{start_of_week.month}月{start_of_week.day}日 〜 {end_of_week.month}月{end_of_week.day}日"

    # HTMLテンプレートにデータを渡してレンダリング
    return render_template('log.html',
                           today=datetime.today().date(), # 「今日」をハイライトするために別途渡す
                           week_dates=week_dates,
                           week_range=week_range_str,
                           prev_week=prev_week_date.strftime('%Y-%m-%d'),
                           next_week=next_week_date.strftime('%Y-%m-%d'),
                           active_page='log'
                           )

@app.route("/points")
@login_required
def points():
    return render_template('points.html',
                           active_page='points'
                           )

@app.route("/account")
@login_required 
def account():
    # 1. セッションからユーザーIDを取得
    user_id = session['user_id']
    
    db = next(get_db())
    try:
        # 2. データベースからユーザー情報を取得
        # (services.py の get_user_by_id 関数を使用)
        current_user = get_user_by_id(db, user_id)
        
        if not current_user:
            # 万が一、DBからユーザーが削除されていた場合
            # 強制的にログアウトさせ、ログインページに戻す
            session.pop('user_id', None)
            return redirect(url_for('login'))

        # 3. 取得したユーザー情報を 'user' という名前でHTMLに渡す
        return render_template('account.html',
                               active_page='account',
                               user=current_user  # ★ ユーザーオブジェクトを渡す
                               )
    except Exception as e:
        # DBエラーなどが発生した場合
        return render_template('account.html',
                               active_page='account',
                               error="アカウント情報の取得に失敗しました。")
    finally:
        db.close()

# --- 認証機能 ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    # POSTリクエスト（フォームが送信された）の場合
    if request.method == 'POST':
        db = next(get_db())
        username = request.form.get('username')
        
        # ★ デバッグ用: POSTされたユーザー名を表示してみる ★
        print(f"--- POSTリクエスト受信: ユーザー名 '{username}' ---")

        try:
            user = get_user_by_username(db, username) 
            
            if user: # ログイン成功
                session['user_id'] = user.id
                
                print(f"--- ログイン成功 (user.id: {user.id}) ---")
                print(f"現在のセッション: {session}")
                has_visited = request.cookies.get('first_visit')

                if has_visited:
                    # Cookieがある場合: 2回目以降のアクセス
                    # 通常のメインコンテンツページにリダイレクトする
                    return redirect(url_for('input'))
                else:
                    # Cookieがない場合: 初回アクセス
                    # 初回起動時のみ表示するページ（テンプレート）をレンダリングする
                    response = make_response(render_template('welcome.html'))

                    # 2. Cookieを設定
                    # 'first_visit'というキーで値を保存し、有効期限を長めに設定する（例: 1年後）
                    # max_ageは秒単位 (365日 * 24時間 * 60分 * 60秒)
                    JST = timezone(timedelta(hours=+9))
                    now = datetime.now(JST)
                    tomorrow = now.date() + timedelta(days=1)
                    expiry_time = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=JST)
                    response.set_cookie(
                        'first_visit', 
                        'true', 
                        expires=expiry_time, # 翌日の0時を設定
                        httponly=True
                    )
                    
                    # 3. Cookieを設定したレスポンスを返す
                    return response
                
            else: # ログイン失敗
                print(f"--- ログイン失敗: ユーザー '{username}' が見つかりません ---")
                return render_template('login.html', error="ユーザーが見つかりません。")

        except Exception as e:
            print(f"--- エラー発生: {str(e)} ---")
            return render_template('login.html', error=f"エラーが発生しました: {str(e)}")
        finally:
            db.close()
    
    # GETリクエスト（ページにアクセスした）の場合
    # @login_required からのリダイレクトもここに来る
    print(f"--- GETリクエスト /login ページ表示 ---")
    return render_template('login.html')

@app.route('/logout')
@login_required  # ログインしている人だけがサインアウトできるようにする
def logout():
    """サインアウト処理"""
    
    # 1. セッションから 'user_id' を削除する
    # .pop(キー, デフォルト値) で、キーが存在しなくてもエラーを防ぐ
    session.pop('user_id', None)
    
    response = make_response(redirect(url_for('login')))
    response.delete_cookie('first_visit')
    return response

# --- ここまで画面ルーティング ---


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