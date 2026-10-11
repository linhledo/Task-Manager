from datetime import datetime
from flask import Flask, redirect, url_for, render_template, request, session, flash
from functools import wraps
import os
import psycopg
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError("Please set the SECRET_KEY environment variable.")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE") == "1"
)

def get_connection():
    return psycopg.connect(
            host="localhost",
            port=5432,
            dbname="postgres",
            user="postgres",
            password=os.environ["DB_PASSWORD"]
        )

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapper

    
def get_tasks(user_id) -> list[dict] | None:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * 
        FROM tasks 
        WHERE user_id = %s
        ORDER BY priority DESC
    """, (user_id,))

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

def get_current_task(user_id) -> dict | None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, description, due_date, priority, status
                FROM tasks
                WHERE user_id = %s AND status = 'PENDING'
                ORDER BY priority DESC, due_date ASC NULLS LAST, created_at ASC
                LIMIT 1
            """, (user_id,))

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

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please enter a username and password", "error")
            return redirect(url_for("register"))

        if len(username) > 100 or len(password) < 8:
            flash("Username must be at most 100 characters and password must be at least 8 characters", 
                  "error")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        user_id = ""
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
                        flash("Error registering user", "error")
                        return redirect(url_for("register"))

                    user_id = row[0]

        except psycopg.errors.UniqueViolation:
            flash("That username is already taken.", "error")

        session.clear()
        session["user_id"] = user_id
        session["username"] = username

        return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, password_hash
                    FROM users
                    WHERE username = %s
                """, (username,))

                user = cursor.fetchone()

                if user is None or not check_password_hash(user[2], password):
                    flash("Invalid username or password", "error")
                    return redirect(url_for("login"))

        session.clear()
        session["user_id"] = user[0]
        session["username"] = user[1]

        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    user_id = session["user_id"]
    task = get_current_task(user_id)
    return render_template("dashboard.html", task=task)

@app.route("/tasks")
def show_tasks():
    tasks = get_tasks(session["user_id"])

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
        user_id = session["user_id"]

        if due_date:
            due_date = datetime.fromisoformat(due_date)
        else:
            due_date = None

        with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO tasks (user_id, description, due_date, priority)
                        VALUES (%s, %s, %s, %s) 
                    """, (user_id, description, due_date, priority))

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
                WHERE user_id = %s AND status = 'COMPLETED'
            """, (session["user_id"],))

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