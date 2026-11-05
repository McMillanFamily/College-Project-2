"""
StudyPilot - web layer (Flask)
==============================
Receives requests from the browser, calls the logic layer, and picks the page
to show. No rules live here: every check is in logic.py.

Run with:  flask --app app run
"""

import os
import secrets
import threading
from datetime import date

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)

import logic
from storage import load_data, save_data

app = Flask(__name__)
# Set STUDYPILOT_SECRET_KEY in the environment for a fixed key. Without it a
# random key is made each run (fine for development; sessions reset on restart).
app.secret_key = os.environ.get("STUDYPILOT_SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # SESSION_COOKIE_SECURE=True,  # turn on once the site is served over HTTPS
)

LOCK = threading.Lock()  # stops two requests writing the data file at once


# ---------- Security: CSRF token on every POST ----------

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


@app.before_request
def check_csrf():
    if request.method == "POST":
        sent = request.form.get("csrf", "")
        if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
            abort(400)


# ---------- Security: everything needs a login except these pages ----------

PUBLIC_ENDPOINTS = {"login", "register", "static"}


@app.before_request
def require_login():
    """Protect every page by default, so a new route can't be left open by accident."""
    if request.endpoint is None or request.endpoint in PUBLIC_ENDPOINTS:
        return None  # (no endpoint = unknown URL, the 404 page handles it)
    user = logic.get_user(load_data(), session.get("user_id"))
    if user is None:
        session.clear()
        return redirect(url_for("login"))
    g.user = user
    return None


def current_store():
    """The logged-in user's own tasks, notes and timetable."""
    return logic.user_store(load_data(), g.user["id"])


# ---------- Helpers shared by the templates ----------

def fmt_date(iso):
    return date.fromisoformat(iso).strftime(logic.DATE_FORMAT)


STATUS_TEXT = {"done": "Done", "overdue": "Overdue", "today": "Due today",
               "soon": "Due soon", "ok": "To do"}


@app.context_processor
def template_helpers():
    return {
        "csrf_token": csrf_token,
        "fmt_date": fmt_date,
        "PRIORITIES": logic.PRIORITIES,
        "DAYS": logic.DAYS,
        "SOON_DAYS": logic.SOON_DAYS,
        "status_of": logic.task_status,
        "STATUS_TEXT": STATUS_TEXT,
        "today_iso": date.today().isoformat(),
        "current_user": g.get("user"),
    }


def date_from_form(value):
    """Browsers send YYYY-MM-DD from a date picker; the logic expects DD/MM/YYYY."""
    value = (value or "").strip()
    parts = value.split("-")
    if len(parts) == 3 and len(parts[0]) == 4:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return value  # typed by hand or blank: the logic will check it


def change(action, message, endpoint):
    """Load -> run a logic function on THIS USER'S store -> save -> flash -> redirect."""
    with LOCK:
        root = load_data()
        try:
            result = action(logic.user_store(root, g.user["id"]))
            save_data(root)
            flash(message(result), "success")
        except logic.ValidationError as err:
            flash(str(err), "error")
    return redirect(url_for(endpoint))


# ---------- Accounts ----------

def start_session(user):
    session.clear()  # drop anything from before the login
    session["user_id"] = user["id"]


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("home"))
    if request.method == "POST":
        f = request.form
        with LOCK:
            root = load_data()
            try:
                user = logic.register_user(root, f.get("username", ""),
                                           f.get("password", ""), f.get("confirm", ""))
                save_data(root)
            except logic.ValidationError as err:
                flash(str(err), "error")
                return render_template("register.html", username=f.get("username", ""))
        start_session(user)
        flash(f"Welcome to StudyPilot, {user['username']}!", "success")
        return redirect(url_for("home"))
    return render_template("register.html", username="")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))
    if request.method == "POST":
        f = request.form
        try:
            user = logic.authenticate(load_data(), f.get("username", ""),
                                      f.get("password", ""))
        except logic.ValidationError as err:
            flash(str(err), "error")
            return render_template("login.html", username=f.get("username", ""))
        start_session(user)
        return redirect(url_for("home"))
    return render_template("login.html", username="")


@app.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------- Pages ----------

@app.get("/")
def home():
    store = current_store()
    done, total, percent = logic.progress(store)
    return render_template("home.html", groups=logic.reminders(store),
                           done=done, total=total, percent=percent)


@app.get("/tasks")
def tasks():
    sort = request.args.get("sort", "deadline")
    if sort not in ("deadline", "priority"):
        sort = "deadline"
    store = current_store()
    return render_template("tasks.html", tasks=logic.sorted_tasks(store, sort), sort=sort)


@app.post("/tasks/add")
def add_task_route():
    return change(
        lambda s: logic.add_task(s, request.form.get("title", ""),
                                 date_from_form(request.form.get("deadline")),
                                 request.form.get("priority", type=int, default=0)),
        lambda t: f"Task saved: {t['title']}.", "tasks")


@app.post("/tasks/<int:task_id>/complete")
def complete_task_route(task_id):
    return change(lambda s: logic.complete_task(s, task_id),
                  lambda t: f"Well done! {t['title']} is complete.", "tasks")


@app.post("/tasks/<int:task_id>/delete")
def delete_task_route(task_id):
    return change(lambda s: logic.delete_task(s, task_id),
                  lambda t: f"Deleted task: {t['title']}.", "tasks")


@app.get("/timetable")
def timetable():
    store = current_store()
    week = [(day, logic.lessons_on(store, day)) for day in logic.DAYS]
    return render_template("timetable.html", week=week)


@app.post("/timetable/add")
def add_lesson_route():
    f = request.form
    return change(
        lambda s: logic.add_lesson(s, f.get("day", ""), f.get("start", ""), f.get("end", ""),
                                   f.get("name", ""), f.get("room", "")),
        lambda l: f"Lesson added: {l['name']} on {l['day']}.", "timetable")


@app.post("/timetable/<int:lesson_id>/delete")
def delete_lesson_route(lesson_id):
    return change(lambda s: logic.delete_lesson(s, lesson_id),
                  lambda l: f"Deleted lesson: {l['name']}.", "timetable")


@app.get("/notes")
def notes():
    store = current_store()
    return render_template("notes.html", notes=list(reversed(store["notes"])))


@app.post("/notes/add")
def add_note_route():
    return change(lambda s: logic.add_note(s, request.form.get("text", "")),
                  lambda n: "Note saved.", "notes")


@app.post("/notes/<int:note_id>/delete")
def delete_note_route(note_id):
    return change(lambda s: logic.delete_note(s, note_id),
                  lambda n: "Note deleted.", "notes")


@app.get("/help")
def help_page():
    return render_template("help.html")


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


@app.errorhandler(400)
def bad_request(_):
    flash("That form expired. Please try again.", "error")
    return redirect(request.referrer or url_for("home"))


if __name__ == "__main__":
    app.run()  # debug mode is deliberately off
