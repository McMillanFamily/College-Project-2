"""
StudyPilot - logic layer
========================
All the rules, validation and calculations. This module never prints,
never asks for input and never touches the web or the disk, so it can be
used by the Flask website (app.py) and tested on its own.
"""

from datetime import date, datetime, timedelta

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
