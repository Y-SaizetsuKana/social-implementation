from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import webbrowser # 標準ライブラリなので追加インストールは不要
from threading import Timer
import json # JSONファイルを扱うためにインポート
import os   # ファイルパスを扱うためにインポート
from datetime import date, timedelta # home.htmlで日付を扱うためにインポート

app = Flask(__name__)
# セッション管理のために秘密鍵を設定します。これは安全なランダムな文字列に変更してください。
app.secret_key = 'your-very-secret-key'

# ルート '/' にアクセスされたときに login.html を返す
@app.route('/')
def root():
  return render_template('login.html')

# ログイン処理
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # ここでは簡単化のため、emailとpasswordが入力されていればログイン成功とします。
        # 実際にはデータベースでユーザー情報を検証してください。
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username') # usernameもフォームから取得

        if email and password:
            # ログイン情報を辞書にまとめる
            login_data = {
                'email': email,
                'username': username,
                'password': password # 注意: パスワードを平文で保存するのは非推奨です
            }

            # ログイン情報をJSONファイルに保存する処理
            output_dir = os.path.dirname(os.path.abspath(__file__))
            filepath = os.path.join(output_dir, 'login_data.json')
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(login_data, f, ensure_ascii=False, indent=4)
                print(f"ログイン情報を {os.path.abspath(filepath)} に保存しました。")
            except Exception as e:
                print(f"ログイン情報のファイル保存中にエラーが発生しました: {e}")
                # ここではエラーが発生しても処理を続行しますが、必要に応じてエラーページを表示するなどの対応が考えられます。

            session['user_id'] = email  # セッションにユーザー情報を保存

            return redirect(url_for('input')) # /input (input.html) へリダイレクト
        else:
            # ログイン失敗時の処理（例：エラーメッセージを表示）
            return render_template('login.html', error="メールアドレスまたはパスワードが正しくありません。")

    # GETリクエストの場合はログインページを表示
    return render_template('login.html')

# ログイン後のホームページ
@app.route('/home')
def home():
    # ログインしていない場合はログインページにリダイレクト
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # home.htmlに必要なデータを渡してレンダリング（前回の提案通り）
    return render_template('home.html')

# 新規登録ページ
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # ここに実際のユーザー登録処理を実装します（例：データベースへの保存）
        return redirect(url_for('login')) # 登録後はログインページへ
    return render_template('register.html')

# 食事入力ページ
@app.route('/input', methods=['GET', 'POST'])
def input():
    if request.method == 'POST':
        # フォームからデータを取得
        food_data = {
            'dish': request.form.get('dish1'),
            'waste': request.form.get('waste1'),
            'amount': request.form.get('amount1'),
            'reason': request.form.get('reason1'),
            'date': date.today().isoformat() # 入力日も記録
        }

        # データをJSONファイルに保存
        output_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(output_dir, 'received_data.json')

        try:
            # ここでは単純に上書き保存しますが、追記するなどの実装も可能です
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(food_data, f, ensure_ascii=False, indent=4)
            
            print(f"食事データを {os.path.abspath(filepath)} に保存しました。")
        except Exception as e:
            print(f"ファイル保存中にエラーが発生しました: {e}")
            # エラーが発生した場合の処理をここに記述

        # データ保存後、記録ページにリダイレクト
        return redirect(url_for('log'))
    today_str = date.today().strftime('%Y-%m-%d')
    return render_template('input.html', today=today_str, active_page='input')

# 記録ページ
@app.route('/log')
def log():
    return render_template('log.html', active_page='log')

# 豆知識ページ
@app.route('/knowledge')
def knowledge():
    return render_template('knowledge.html', active_page='knowledge')

# ポイントページ
@app.route('/points')
def points():
    return render_template('points.html', active_page='points')

# アカウントページ
@app.route('/account')
def account():
    return render_template('account.html', active_page='account')

# '/get_data' へのGETリクエストでJSONデータを返す (バックエンド→フロントエンド)
@app.route('/get_data', methods=['GET'])
def get_data():
  # JavaScript側で表示したいメッセージに修正
  data_from_python = {'message': 'サーバーからの初期データです！'}
  return jsonify(data_from_python)

# '/receive_data' へのPOSTリクエストでデータを受信する (フロントエンド→バックエンド)
@app.route('/receive_data', methods=['POST'])
def receive_data():
  data_from_js = request.json
  received_message = data_from_js.get('message', 'メッセージがありません')
  print(f"フロントエンドから受信: '{received_message}'")

  # 受信したデータをJSONファイルに保存
  # 保存先をこのスクリプト(API_app.py)があるディレクトリに設定
  output_dir = os.path.dirname(os.path.abspath(__file__))
  filename = 'received_data.json' # ファイル名
  filepath = os.path.join(output_dir, filename) # 保存するファイルのフルパス

  try:
    # 保存先ディレクトリがなければ作成する
    os.makedirs(output_dir, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
      json.dump(data_from_js, f, ensure_ascii=False, indent=4)
    
    absolute_path = os.path.abspath(filepath)
    print(f"データを {absolute_path} に保存しました。")
    # 受信成功のレスポンスを返す
    return jsonify({'reply': f"「{received_message}」を受け取り、JSONファイルに保存しました！\n保存場所: {absolute_path}"})
  except Exception as e:
    print(f"ファイル保存中にエラーが発生しました: {e}")
    return jsonify({'reply': f"「{received_message}」を受け取りましたが、ファイル保存に失敗しました。"}), 500

# APIテスト用のindex.htmlを表示するルート
@app.route('/api_test')
def api_test():
    return render_template('index.html')

# ブラウザを自動で開くための関数
def open_browser():
      webbrowser.open_new('http://127.0.0.1:5000/')

# アプリケーションの実行
if __name__ == '__main__':
  # サーバー起動の少し後（1秒後）にブラウザを開く。
  # use_reloader=False を指定しないと、デバッグモードではコードが2回実行され、ブラウザが2回開かれることがある。
  if not os.environ.get("WERKZEUG_RUN_MAIN"):
    Timer(1, open_browser).start()
  app.run(debug=True, use_reloader=True)
