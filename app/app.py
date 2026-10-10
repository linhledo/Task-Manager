from flask import Flask, redirect, url_for, render_template
import psycopg

app = Flask(__name__)

def get_connection():
    return psycopg.connect(
            host="localhost",
            port=5432,
            dbname="postgres",
            user="postgres",
            password="2006"
        )

    
def get_tasks() -> list[dict] | None:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * 
        FROM tasks 
        ORDER BY priority DESC
    """)

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    if rows is None:
        return None

    tasks = []
    for row in rows:
        tasks.append(
            {
                "id": row[0],
                "description": row[6],
                "due_date": row[2],
                "priority": row[3],
                "status": row[4]
            }
        )

    return tasks

def get_current_task() -> dict | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, description, due_date, priority, status
                FROM tasks
                WHERE status = 'PENDING'
                ORDER BY priority DESC, due_date ASC NULLS LAST
                LIMIT 1
            """)

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row[0],
                "description": row[1],
                "due_date": row[2],
                "priority": row[3],
                "status": row[4]
            }

@app.route("/")
def dashboard():
    task = get_current_task()
    return render_template("dashboard.html", task=task)

@app.route("/tasks")
def show_tasks():
    tasks = get_tasks()

    return render_template(
        "tasks.html",
        tasks=tasks
    )

@app.route("/tasks/new")
def add_task():
    return "We'll build the add-task page next!"

@app.route("/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(task_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE tasks
                SET status = 'COMPLETED'
                where id = %s
            """, (task_id,))
    return redirect(url_for("dashboard"))