"""
StudyPilot - logic layer
========================
All the rules, validation and calculations. This module never prints,
never asks for input and never touches the web or the disk, so it can be
used by the Flask website (app.py) and tested on its own.
"""

import re
from datetime import date, datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

DATE_FORMAT = "%d/%m/%Y"
TIME_FORMAT = "%H:%M"
PRIORITIES = {1: "High", 2: "Medium", 3: "Low"}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
SOON_DAYS = 3  # tasks due within this many days count as "due soon"


# =====================================================================
# RULES
# =====================================================================

class ValidationError(ValueError):
    """Raised when the user gives information the app cannot accept."""


def parse_date(text):
    """Turn 'DD/MM/YYYY' into a date, or raise ValidationError."""
    try:
        return datetime.strptime(text.strip(), DATE_FORMAT).date()
    except ValueError:
        raise ValidationError("That is not a valid date. Use DD/MM/YYYY, e.g. 25/12/2026.")


def parse_time(text):
    """Turn 'HH:MM' (24-hour) into a time, or raise ValidationError."""
    try:
        return datetime.strptime(text.strip(), TIME_FORMAT).time()
    except ValueError:
        raise ValidationError("That is not a valid time. Use 24-hour HH:MM, e.g. 09:30.")


def new_store():
    """An empty data store."""
    return {"tasks": [], "notes": [], "timetable": [], "next_id": 1}


def _take_id(store):
    value = store["next_id"]
    store["next_id"] += 1
    return value


# ---------- Tasks ----------

def add_task(store, title, deadline_text, priority, today=None):
    """
    ALGORITHM (Stage Three):
      1. Remove spaces from the title.
      2. IF the title is empty            -> error.
      3. Convert the deadline text to a date (error if the format is wrong).
      4. IF the deadline is before today  -> error, ELSE continue.
      5. IF the priority is not 1, 2 or 3 -> error.
      6. Save the task and return it.
    """
    today = today or date.today()
    title = title.strip()
    if not title:
        raise ValidationError("The task name cannot be empty.")
    if len(title) > 80:
        raise ValidationError("The task name is too long (80 characters max).")
    deadline = parse_date(deadline_text)
    if deadline < today:
        raise ValidationError("That deadline is in the past. Please check the date.")
    if priority not in PRIORITIES:
        raise ValidationError("Priority must be 1 (High), 2 (Medium) or 3 (Low).")

    task = {
        "id": _take_id(store),
        "title": title,
        "deadline": deadline.isoformat(),
        "priority": priority,
        "done": False,
    }
    store["tasks"].append(task)
    return task


def find_task(store, task_id):
    for task in store["tasks"]:
        if task["id"] == task_id:
            return task
    raise ValidationError(f"There is no task with ID {task_id}.")


def complete_task(store, task_id):
    task = find_task(store, task_id)
    task["done"] = True
    return task


def delete_task(store, task_id):
    task = find_task(store, task_id)
    store["tasks"].remove(task)
    return task


def sorted_tasks(store, by="deadline"):
    """Return tasks sorted by 'deadline' or 'priority' (ties broken by the other)."""
    if by == "priority":
        key = lambda t: (t["priority"], t["deadline"])
    else:
        key = lambda t: (t["deadline"], t["priority"])
    return sorted(store["tasks"], key=key)


def task_status(task, today=None):
    """Return 'done', 'overdue', 'today', 'soon' or 'ok'."""
    today = today or date.today()
    if task["done"]:
        return "done"
    deadline = date.fromisoformat(task["deadline"])
    if deadline < today:
        return "overdue"
    if deadline == today:
        return "today"
    if deadline <= today + timedelta(days=SOON_DAYS):
        return "soon"
    return "ok"


def reminders(store, today=None):
    """Return a dict of unfinished tasks that need attention."""
    today = today or date.today()
    groups = {"overdue": [], "today": [], "soon": []}
    for task in sorted_tasks(store, "deadline"):
        status = task_status(task, today)
        if status in groups:
            groups[status].append(task)
    return groups


def progress(store):
    """Return (completed, total, percent)."""
    total = len(store["tasks"])
    done = sum(1 for t in store["tasks"] if t["done"])
    percent = round(100 * done / total) if total else 0
    return done, total, percent


# ---------- Notes ----------

def add_note(store, text):
    text = text.strip()
    if not text:
        raise ValidationError("A note cannot be empty.")
    note = {"id": _take_id(store), "text": text,
            "created": datetime.now().strftime("%d/%m/%Y %H:%M")}
    store["notes"].append(note)
    return note


def delete_note(store, note_id):
    for note in store["notes"]:
        if note["id"] == note_id:
            store["notes"].remove(note)
            return note
    raise ValidationError(f"There is no note with ID {note_id}.")


# ---------- Timetable ----------

def add_lesson(store, day, start_text, end_text, name, room):
    day = day.strip().capitalize()
    if day not in DAYS:
        raise ValidationError("Day must be Monday to Friday.")
    start, end = parse_time(start_text), parse_time(end_text)
    if end <= start:
        raise ValidationError("The lesson must end after it starts.")
    name, room = name.strip(), room.strip()
    if not name:
        raise ValidationError("The lesson name cannot be empty.")
    if not room:
        room = "TBC"
    # Clash check: two lessons on the same day cannot overlap.
    for lesson in store["timetable"]:
        if lesson["day"] == day:
            l_start = parse_time(lesson["start"])
            l_end = parse_time(lesson["end"])
            if start < l_end and l_start < end:
                raise ValidationError(
                    f"That clashes with {lesson['name']} ({lesson['start']}-{lesson['end']}).")
    lesson = {"id": _take_id(store), "day": day, "start": start.strftime(TIME_FORMAT),
              "end": end.strftime(TIME_FORMAT), "name": name, "room": room}
    store["timetable"].append(lesson)
    return lesson


def delete_lesson(store, lesson_id):
    for lesson in store["timetable"]:
        if lesson["id"] == lesson_id:
            store["timetable"].remove(lesson)
            return lesson
    raise ValidationError(f"There is no lesson with ID {lesson_id}.")


def lessons_on(store, day):
    return sorted((l for l in store["timetable"] if l["day"] == day), key=lambda l: l["start"])



# =====================================================================
# USERS
# =====================================================================
# The data file now holds every user's data:
#   {"users": [{"id", "username", "password_hash"}, ...],
#    "next_user_id": 3,
#    "stores": {"1": <that user's tasks/notes/timetable store>, "2": ...}}
# The task, note and lesson functions above are unchanged: they are simply
# given the logged-in user's own store.

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
MIN_PASSWORD = 8
MAX_PASSWORD = 128
_DUMMY_HASH = generate_password_hash("not-a-real-password")  # see authenticate()


def _ensure_root(root):
    root.setdefault("users", [])
    root.setdefault("next_user_id", 1)
    root.setdefault("stores", {})
    return root


def user_store(root, user_id):
    """Return (creating if needed) one user's own store."""
    _ensure_root(root)
    return root["stores"].setdefault(str(user_id), new_store())


def get_user(root, user_id):
    """Return the user dict for an ID, or None."""
    for user in _ensure_root(root)["users"]:
        if user["id"] == user_id:
            return user
    return None


def _find_by_username(root, username):
    wanted = username.strip().lower()
    for user in _ensure_root(root)["users"]:
        if user["username"].lower() == wanted:
            return user
    return None


def _claim_legacy_data(root):
    """Pre-accounts data sat at the top level. Move it into a store."""
    if any(key in root for key in ("tasks", "notes", "timetable")):
        return {"tasks": root.pop("tasks", []),
                "notes": root.pop("notes", []),
                "timetable": root.pop("timetable", []),
                "next_id": root.pop("next_id", 1)}
    return new_store()


def register_user(root, username, password, confirm):
    """
    ALGORITHM:
      1. Remove spaces from the username.
      2. IF it is not 3-20 letters, numbers or underscores -> error.
      3. IF the username is already taken (any capitalisation) -> error.
      4. IF the password is too short / too long -> error.
      5. IF the two passwords differ -> error.
      6. Hash the password, save the user and give them a store.
         The FIRST user also inherits any data from before accounts existed.
    """
    _ensure_root(root)
    username = username.strip()
    if not USERNAME_RE.match(username):
        raise ValidationError(
            "Usernames must be 3-20 characters: letters, numbers or underscores.")
    if _find_by_username(root, username):
        raise ValidationError("That username is already taken.")
    if len(password) < MIN_PASSWORD:
        raise ValidationError(f"Passwords must be at least {MIN_PASSWORD} characters.")
    if len(password) > MAX_PASSWORD:
        raise ValidationError(f"Passwords can be at most {MAX_PASSWORD} characters.")
    if password != confirm:
        raise ValidationError("The two passwords do not match.")

    first_user = not root["users"]
    user = {"id": root["next_user_id"], "username": username,
            "password_hash": generate_password_hash(password)}
    root["next_user_id"] += 1
    root["users"].append(user)
    root["stores"][str(user["id"])] = _claim_legacy_data(root) if first_user else new_store()
    return user


def authenticate(root, username, password):
    """Return the user if the login is right, else raise ValidationError.

    The same vague message is used for 'no such user' and 'wrong password', and
    a dummy hash is checked when the user does not exist, so the response gives
    nothing away about which usernames are registered.
    """
    user = _find_by_username(root, username)
    ok = check_password_hash(user["password_hash"] if user else _DUMMY_HASH, password)
    if not user or not ok:
        raise ValidationError("Incorrect username or password.")
    return user
