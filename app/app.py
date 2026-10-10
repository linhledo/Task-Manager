from datetime import datetime
from flask import Flask, redirect, url_for, render_template, request, flash
import psycopg

app = Flask(__name__)

app.secret_key = 'temporary-secret-key'

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

@app.route("/tasks/new", methods=["GET", "POST"])
def add_task():
    if request.method == "POST":
        description = request.form["description"]
        due_date = request.form.get("due_date")
        priority = request.form["priority"]

        if due_date:
            due_date = datetime.fromisoformat(due_date)
        else:
            due_date = None

        #TODO: need to change for different users
        with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO tasks (user_id, description, due_date, priority)
                        VALUES (1, %s, %s, %s) 
                    """, (description, due_date, priority))

        flash("Task added successfully ✓", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_task.html")

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

@app.route("/tasks/clear-completed", methods=["POST"])
def clear_completed_tasks():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM tasks
                WHERE status = 'COMPLETED'
            """)

            deleted_count = cursor.rowcount
    flash(
        f"Deleted {deleted_count} completed task(s).",
        "success"
    )
    return redirect(url_for("show_tasks"))

@app.route("/tasks/<int:task_id>/revert", methods=["POST"])
def revert_task(task_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE tasks
                SET status = 'PENDING'
                where id = %s
            """, (task_id,))
    flash(
        f"Reverted task back to Pending ✓",
        "success"
    )
    return redirect(url_for("show_tasks"))