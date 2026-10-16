from datetime import datetime
from flask import Flask, redirect, url_for, render_template, request, session, flash
from functools import wraps
import os
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError("Please set the SECRET_KEY environment variable.")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE") == "1"
)

TASK_SERVICE_URL = os.environ.get(
    "TASK_SERVICE_URL",
    "http://127.0.0.1:5001"
)

USER_SERVICE_URL = os.environ.get(
    "USER_SERVICE_URL",
    "http://127.0.0.1:5003"
)

def task_service_request(method, path, **kwargs):
    response = requests.request(
        method,
        f"{TASK_SERVICE_URL}{path}",
        timeout=5,
        **kwargs
    )
    response.raise_for_status()
    return response

def user_service_request(method, path, **kwargs):
    response = requests.request(
        method,
        f"{USER_SERVICE_URL}{path}",
        **kwargs
    )
    return response

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapper

@app.get("/health")
def health():
    return {"status": "healthy"}, 200

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

        response = user_service_request(
            "POST",
            "/users/register",
            json={
                "username": username,
                "password": password
            }
        )

        if response.status_code == 409:
            flash("That username is already taken.", "error")
            return redirect(url_for("register"))

        if response.status_code == 400:
            flash("Error creating user.", "error")
            return redirect(url_for("register"))

        response = response.json()

        session.clear()
        session["user_id"] = response["id"]
        session["username"] = response["username"]

        return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please enter a username and password", "error")
            return redirect(url_for("register"))

        response = user_service_request(
            "POST",
            "/users/login",
            json={
                "username": username,
                "password": password
            }
        )

        if response.status_code == 401:
            flash("Invalid username or password", "error")
            return redirect(url_for("login"))

        response = response.json()

        session.clear()
        session["user_id"] = response["id"]
        session["username"] = response["username"]

        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    response = task_service_request(
        "GET",
        "/tasks",
        params={"user_id": session["user_id"]}
    )

    tasks = response.json()
    task = next(
        (task for task in tasks if task["status"] == "PENDING"),
        None
    )

    return render_template("dashboard.html", task=task)

@app.route("/tasks")
@login_required
def show_tasks():

    response = task_service_request(
        "GET",
        "/tasks",
        params={"user_id": session["user_id"]}
    )

    tasks = response.json()

    return render_template("tasks.html", tasks=tasks)

@app.route("/tasks/new", methods=["GET", "POST"])
@login_required
def add_task():
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        due_date = request.form.get("due_date") or None
        priority = request.form.get("priority") or None

        if not description:
            flash("Please enter a description.", "error")
            return redirect(url_for("add_task", method="GET"))

        task_service_request(
            "POST",
            "/tasks",
            json={
                "user_id": session["user_id"],
                "description": description,
                "due_date": due_date,
                "priority": priority
            }
        )

        flash("Task added successfully ✓", "success")
        return redirect(url_for("dashboard"))
    
    return render_template("add_task.html")

@app.route("/tasks/<int:task_id>/complete", methods=["POST"])
def complete_task(task_id):
    task_service_request(
        "POST",
        f"/tasks/{task_id}/complete",
        json={
            "user_id": session["user_id"]
        }
    )
    return redirect(url_for("dashboard"))

@app.route("/tasks/clear-completed", methods=["POST"])
def clear_completed_tasks():
    response = task_service_request(
        "DELETE",
        "/tasks/clear-completed",
        params={"user_id": session["user_id"]}
    )

    deleted_count = response.json().get("deleted_count")

    flash(
        f"Deleted {deleted_count} completed task(s).",
        "success"
    )
    return redirect(url_for("show_tasks"))

@app.route("/tasks/<int:task_id>/revert", methods=["POST"])
def revert_task(task_id):
    task_service_request(
        "POST",
        f"/tasks/{task_id}/revert",
        json={"user_id": session["user_id"]}
    )
    flash(
        f"Reverted task back to Pending ✓",
        "success"
    )
    return redirect(url_for("show_tasks"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)