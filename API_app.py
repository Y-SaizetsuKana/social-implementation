from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
#送信(バックエンド→フロントエンド)
@app.route('/')
def index():
  return render_templete('index.html')

@app.route('/get_data', methods=['POST'])
def get_data():
  data_from_python = {'message': 'Output Data'}
  return jsonify(data_from_python)

if __name__ == '__main__':
  app.run(debug = True)
  
#受信(フロントエンド→バックエンド)
@app.route('/receive_data', methods=['POST'])
def receive_data():
  data_from_js = request.json
  print('Front End', data_from_js)
  return jsonify({'message': 'Input Data'})

if __name__ == '__main__':
  app.run(debug = True)
