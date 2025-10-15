"""
data_prs.py
データの前処理を行う
"""


  #ライブラリのインポート
import re
import requests
import json

#  データの前処理

  # 文字列が整数に変換可能かチェックし、可能なら整数に変換して返す
def str2int(txt:str)->int:
    if(re.match(r'^[0-9]+$',txt) is not None):
        return int(txt)
    else:
        print('this text includes some characters is not number')
        


  # パスワードがポリシーに適合するかチェック
def password_checker(password:str)->bool:
    if(len(password) <8 or len(password) >16):
        print("パスワードは8文字以上16文字以下で設定してください")
        return False
    if(re.search(r'[#,$,%,&]')!=None):
        print("パスワードに使用できない文字が含まれています")
        return False
    else:
        if(re.search(r'[a-zA-Z]',password)==None):
            pass
        if(re.search(r'[0-9]',password)==None):
            pass
        return True
    


  # パスワードがポリシーに適合するかチェック
def password_checker(password:str)->bool:
    if(len(password) <8 or len(password) >16):
        print("パスワードは8文字以上16文字以下で設定してください")
        return False
    if(re.search(r'[#,$,%,&]')!=None):
        print("パスワードに使用できない文字が含まれています")
        return False
    else:
        if(re.search(r'[a-zA-Z]',password)==None):
            pass
        if(re.search(r'[0-9]',password)==None):
            pass
        return True
    


#  jsonデータの取得、型変換→pickelで保存

  # jsonデータの取得(未完成)
def get_jsondata(url:str):
    response = requests.post(url, json={"key": "value"})
    if response.status_code == 200:
        json_data = response.json()
        print(json_data)
        return json_data
    else:print(response.status_code)
    return None