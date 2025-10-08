from flask import Flask, render_template, jsonify, request
app = Flask(__name__)

# ルート '/' にアクセスされたときに index.html を返す
@app.route('/')
def index():
  # 'render_templete' から 'render_template' へタイポを修正
  return render_template('index.html')
# '/get_data' へのPOSTリクエストでJSONデータを返す (バックエンド→フロントエンド)
@app.route('/get_data', methods=['POST'])
def get_data():
  data_from_python = {'message': 'Output Data'}
  return jsonify(data_from_python)


# '/receive_data' へのPOSTリクエストでデータを受信する (フロントエンド→バックエンド)
@app.route('/receive_data', methods=['POST'])
def receive_data():
  data_from_js = request.json
  received_message = data_from_js.get('message', 'メッセージがありません')
  print(f"フロントエンドから受信: '{received_message}'")
  # 受信成功のレスポンスを返す
  return jsonify({'status': 'success', 'reply': f"「{received_message}」を受け取りました！"})
# アプリケーションの実行
if __name__ == '__main__':
  app.run(debug = True)
