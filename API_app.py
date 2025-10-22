from flask import Flask, render_template, jsonify, request
import webbrowser # 標準ライブラリなので追加インストールは不要
from threading import Timer
import json # JSONファイルを扱うためにインポート
import os   # ファイルパスを扱うためにインポート
app = Flask(__name__)

# ルート '/' にアクセスされたときに index.html を返す
@app.route('/')
def index():
  return render_template('index.html')

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

# ブラウザを自動で開くための関数
def open_browser():
      webbrowser.open_new('http://127.0.0.1:5000')

# アプリケーションの実行
if __name__ == '__main__':
  # サーバー起動の少し後（1秒後）にブラウザを開く
  Timer(1, open_browser).start()
  app.run(debug=True)
