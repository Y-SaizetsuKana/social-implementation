from flask import Blueprint, request, jsonify
from openai import OpenAI
import os

chat_bp = Blueprint('chat', __name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@chat_bp.route('/generate_recipe', methods=['POST'])
def generate_recipe():
    data = request.get_json()
    food = data.get('food', '')

    if not food:
        return jsonify({"error": "食材名が空です"}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは家庭の食品ロスを減らすためのアシスタントです。"},
                {"role": "user", "content": f"{food}を使ったアレンジレシピや再利用のアイデアを教えてください。"}
            ],
            max_tokens=400,
            temperature=0.7
        )
        recipe = response.choices[0].message.content
        return jsonify({"recipe": recipe})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
