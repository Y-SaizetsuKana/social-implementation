# app.py
from flask import Flask, request, jsonify
from database import init_db, get_db
from models import User, LossReason, FoodLossRecord
import datetime
import hashlib
import json

app = Flask(__name__)

# アプリケーション起動時にデータベースを初期化
init_db()

@app.route("/")
def home():
    return "Hello, this is the Food Loss App Backend!"

@app.route("/api/register_user", methods=["POST"])
def register_user():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not all([username, email, password]):
        return jsonify({"message": "Username, email, and password are required."}), 400

    db = next(get_db())
    try:
        # パスワードをハッシュ化
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            total_points=0
        )
        
        db.add(new_user)
        db.commit()

        return jsonify({"message": "User registered successfully!", "user_id": new_user.id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500
    finally:
        db.close()

# 廃棄記録を追加するAPI
@app.route("/api/add_loss_record", methods=["POST"])
def add_loss_record():
    data = request.get_json()
    user_id = data.get("user_id")
    item_name = data.get("item_name")
    weight_grams = data.get("weight_grams")
    reason_text = data.get("reason_text")

    if not all([user_id, item_name, weight_grams, reason_text]):
        return jsonify({"message": "All fields are required."}), 400

    db = next(get_db())
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"message": "User not found."}), 404

        reason = db.query(LossReason).filter_by(reason_text=reason_text).first()
        if not reason:
            return jsonify({"message": "Invalid loss reason."}), 400

        new_record = FoodLossRecord(
            user_id=user.id,
            item_name=item_name,
            weight_grams=weight_grams,
            loss_reason_id=reason.id,
            record_date=datetime.datetime.now().isoformat()
        )
        
        db.add(new_record)
        db.commit()

        return jsonify({"message": "Record added successfully!", "record_id": new_record.id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500
    finally:
        db.close()

if __name__ == "__main__":
    app.run(debug=True)