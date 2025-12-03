from flask import Blueprint, render_template, current_app # current_appをインポート
import pandas as pd
import os
import numpy as np

# 1. Blueprintを定義 (変更なし)
bp = Blueprint('knowledge_bp', __name__, url_prefix='/knowledge')

# 💡 CSVファイルの相対パス (staticフォルダからの相対パス)
CSV_RELATIVE_PATH = os.path.join('static', 'excel', '豆知識(料理).csv')


# ----------------------------------------------------
# 💡 CSVファイルを読み込む関数
# ----------------------------------------------------
def load_knowledge_data():
    base_dir = os.path.dirname(current_app.root_path) 
    csv_file_path = os.path.join(base_dir, CSV_RELATIVE_PATH)

    if not os.path.exists(csv_file_path):
        print(f"🚨 致命的なエラー: ファイルが見つかりません。確認パス: {csv_file_path}")
        return []

    try:
        # CSV読み込み部分（前回の最終版と同じ）
        try:
            df = pd.read_csv(csv_file_path, encoding='utf-8-sig', header=None)
        except UnicodeDecodeError:
             df = pd.read_csv(csv_file_path, encoding='shift_jis', header=None)

        
        df = df.iloc[1:].copy()
        df.columns = ['category', 'title', 'content'] 

        df.replace('', np.nan, inplace=True)
        # title, content が両方ある行を抽出
        df.dropna(subset=['title', 'content'], inplace=True) 
        
        # 安定した連番IDを割り当て
        df.reset_index(drop=True, inplace=True)
        df['id'] = df.index.astype(str)
        
        df = df[['id', 'category', 'title', 'content']]

        unique_categories = df['category'].dropna().unique().tolist()
                
        knowledge_list = df.to_dict('records')
        
        return knowledge_list, unique_categories
        
    except Exception as e:
        print(f"🚨 CSV処理中にエラーが発生しました。エラー詳細: {e}")
        return [], []


# 2. ルートを定義の修正
@bp.route('/')
def knowledge():
    knowledge_data, categories = load_knowledge_data()
    
    return render_template('knowledge.html', 
                           # 渡すデータ
                           knowledge_list=knowledge_data, 
                           categories=categories,
                           # アクティブページ
                           active_page='knowledge')