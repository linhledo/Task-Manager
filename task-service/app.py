from flask import Flask, jsonify, request
import psycopg
import os

app = Flask(__name__)

def get_connection():
    return psycopg.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=int(os.environ.get("DB_PORT", "5432")),
            dbname=os.environ.get("DB_NAME", "postgres"),
            user=os.environ.get("DB_USER", "postgres"),
            password=os.environ["DB_PASSWORD"]
        )

@app.get("/health")
def health():
    return jsonify({"status": "healthy"}), 200

@app.route("/tasks", methods=["GET"])
def get_tasks():
    user_id = request.args.get("user_id", type=int)
    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, description, due_date, priority, status
        FROM tasks 
        WHERE user_id = %s
        ORDER BY priority DESC, due_date ASC NULLS LAST, created_at ASC
    """, (user_id,))

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    tasks = []

    for row in rows:
        tasks.append(
            {
                "id": row[0],
                "description": row[1],
                "due_date": row[2],
                "priority": row[3],
                "status": row[4]
            }
        )

    return jsonify(tasks)

@app.route("/tasks", methods=["POST"])
def add_task():
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    description = data.get("description")
    due_date = data.get("due_date")
    priority = data.get("priority")

    if not user_id or not description:
        return jsonify({"error": "Missing required fields"}), 400

    if priority is None:
        priority = 0

    try:
        user_id = int(user_id)
        priority = int(priority)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user_id or priority"}), 400

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO tasks (user_id, description, due_date, priority)
                VALUES (%s, %s, %s, %s) 
                RETURNING id
            """, (user_id, description, due_date or None, priority))
            row = cursor.fetchone()
            if row is None:
                return jsonify({"error": "Insertion failed"})
            task_id = row[0]

    return jsonify({"id": task_id, "message": "Task created"}), 201

@app.route("/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(task_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE tasks
                SET status = 'COMPLETED'
                WHERE id = %s AND user_id = %s
            """, (task_id, user_id))
            updated = cursor.rowcount
    
    if updated == 0:
        return jsonify({"error": "Task not found"}), 404
    
    return jsonify({"message": "Task completed"})

@app.route("/tasks/clear-completed", methods=["DELETE"])
def clear_completed_tasks():
    user_id = request.args.get("user_id", type=int)

    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM tasks
                WHERE user_id = %s AND status = 'COMPLETED'
            """, (user_id,))

            deleted_count = cursor.rowcount
    return jsonify({"deleted_count": deleted_count})

@app.route("/tasks/<int:task_id>/revert", methods=["POST"])
def revert_task(task_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400
    
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE tasks
                SET status = 'PENDING'
                WHERE id = %s AND user_id = %s
            """, (task_id, user_id))
            updated = cursor.rowcount

    if updated == 0:
        return jsonify({"error": "Task not found"}), 404
            
    return jsonify({"message": "Task reverted"}), 201

@app.route("/tasks/<int:task_id>/edit", methods=["POST"])
def edit_task(task_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    description = data.get("description")
    due_date = data.get("due_date")
    priority = data.get("priority")

    if not user_id or not description:
        return jsonify({"error": "Missing required fields"}), 400

    if priority is None:
        priority = 0

    try:
        user_id = int(user_id)
        priority = int(priority)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user_id or priority"}), 400
    
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE tasks
                SET description = %s, due_date = %s, priority = %s
                WHERE id = %s AND user_id = %s
            """, (description, due_date, priority, task_id, user_id))
            updated = cursor.rowcount

    if updated == 0:
        return jsonify({"error": "Task not found"}), 404
            
    return jsonify({"message": "Task Edited"}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

