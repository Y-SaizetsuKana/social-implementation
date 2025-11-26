from flask import Flask
from werkzeug.security import generate_password_hash, check_password_hash
import re
import time
import datetime
import sqlite3
import json
from flask import jsonify
import requests
import os


app = Flask(__name__)

class User():
    def __init__(self):
        self.id:int = 0
        self.username:str = None
        self.password:str = None
        self.email:str = None
        self.total_points:int =0

  # 文字列が整数に変換可能かチェックし、可能なら整数に変換して返す
def str2int(txt:str)->int:
    if(re.match(r'^[0-9]+$',txt) is not None):
        return int(txt)
    else:
        print('this text includes some characters is not number')
        return None

  # 整数をチェック
def integer_checker(data):
    if(re.match(r'^[0-9]+$',str(data)) is not None):
        if(type(data)==int):
            return data
        else:
            return int(data)
    else:
        print('this text includes some characters is not number')

def read_user(file_path:str)->User:
    try:
        user =User()
        # ファイルを開いて読み込む
        with open(file_path, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        # 各属性（キー）を指定して値を取得
        user.id = user_data['id']
        user.username = user_data['username']
        user.password = user_data['password']
        user.email = user_data['email']
        user.total_points = user_data['total_point']

        # 結果の表示
        print("データの取得に成功しました:")
        print(f"ID: {user.id}")
        print(f"Username: {user.username}")
        print(f"Password: {user.password}")
        print(f"Email: {user.email}")
        print(f"Total Point: {user.total_points}")

        return user

    except FileNotFoundError:
        print(f"エラー: '{file_path}' が見つかりません。")
    except KeyError as e:
        print(f"エラー: 指定されたキー {e} がJSON内に存在しません。")
    except json.JSONDecodeError:
        print("エラー: JSONファイルの形式が正しくありません。")
    
    
@app.route('/processing/login',methods=['GET'])
def logindata_prs():
    user =User()
    user =read_user('login-test.json')
    #ここから編集処理
    #check int
    user.id = integer_checker(user.id)
    user.total_points = integer_checker(user.total_points)
    #check str
    user.username = str(user.username)
    user.password = str(user.password)
    user.email = str(user.email)
    
    dict_user={
        "id":user.id,
        "username":user.username,
        "password":user.password,
        "email":user.email,
        "total_points":user.total_points
    }
    return jsonify(dict_user)

    
    
    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001,debug=True)
    
    