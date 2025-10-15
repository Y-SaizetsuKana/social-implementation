from flask import Flask, render_template, jsonify, request
import webbrowser # 標準ライブラリなので追加インストールは不要
from threading import Timer
app = Flask(__name__)

# ルート '/' にアクセスされたときに index.html を返す
@app.route('/')
def index():
  return render_template('index.html')

# '/get_data' へのPOSTリクエストでJSONデータを返す (バックエンド→フロントエンド)
@app.route('/get_data', methods=['POST'])
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
  # 受信成功のレスポンスを返す
  return jsonify({'reply': f"「{received_message}」を受け取りました！"})

# ブラウザを自動で開くための関数
def open_browser():
      webbrowser.open_new('http://127.0.0.1:5000')

# アプリケーションの実行
if __name__ == '__main__':
  # サーバー起動の少し後（1秒後）にブラウザを開く
  Timer(1, open_browser).start()
  app.run(debug=True)
