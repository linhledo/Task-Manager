import os
from flask import Flask, request, jsonify
import psycopg
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

def get_connection():
    return psycopg.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", "5432"),
            dbname=os.environ.get("DB_NAME", "postgres"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ["DB_PASSWORD"]
        )

@app.get("/health")
def health():
    return jsonify({"status": "healthy"}), 200

@app.post("/users/register")
def register():
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({
            "error": "Username and password are required"
        }), 400

    password_hash = generate_password_hash(password)

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users (username, password_hash)
                    VALUES (%s, %s)
                    RETURNING id
                """, (username, password_hash))

                row = cursor.fetchone()

                if row is None:
                    return jsonify({
                            "error": "Error creating user"
                        }), 400

                user_id = row[0]

        return jsonify({
            "id": user_id,
            "username": username
        }), 201
    
    except psycopg.errors.UniqueViolation:
        return jsonify({
            "error": "Username already exists"
        }), 409

@app.post("/users/login")
def login():
    data = request.get_json(silent=True) or {}

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({
            "error": "Username and password are required"
        }), 400

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, password_hash
                FROM users
                WHERE username = %s
            """, (username,))

            user = cursor.fetchone()

            if user is None or not check_password_hash(user[2], password):
                return jsonify({
                    "error": "Invalid username or password"
                }), 401

    return jsonify({
        "id": user[0],
        "username": user[1]
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)


