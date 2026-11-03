"""
Test plan for StudyPilot logic tests (Stage Five).  Run from the project folder with:  python3 tests/test_logic.py
Each test says what it does and what we EXPECT to happen. PASS/FAIL is printed.
"""

import os
import tempfile
from datetime import date, timedelta

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import logic as sp
import storage

TODAY = date(2026, 10, 27)
results = []


def fmt(d):
    return d.strftime(sp.DATE_FORMAT)


def check(name, action, expected, fn):
    try:
        ok = bool(fn())
    except Exception as exc:  # an unexpected crash is a FAIL
        ok = False
        action += f"  [crashed: {exc!r}]"
    results.append((name, action, expected, "PASS" if ok else "FAIL"))


def raises(fn):
    try:
        fn()
    except sp.ValidationError:
        return True
    return False


# --- 1. Adding a task ---------------------------------------------------
s = sp.new_store()
t = sp.add_task(s, "Maths homework", fmt(TODAY + timedelta(days=5)), 1, today=TODAY)
check("1", "Add a valid task", "Task appears in the task list",
      lambda: t in s["tasks"] and len(s["tasks"]) == 1)

# --- 2. Completing a task -----------------------------------------------
sp.complete_task(s, t["id"])
check("2", "Mark a task as complete", "Task is shown as completed",
      lambda: sp.task_status(s["tasks"][0], TODAY) == "done")

# --- 3. Empty name ------------------------------------------------------
s2 = sp.new_store()
check("3", "Leave the task name empty", "Error message, nothing saved",
      lambda: raises(lambda: sp.add_task(s2, "   ", "01/12/2026", 2, today=TODAY)) and not s2["tasks"])

# --- 4. Invalid deadlines ----------------------------------------------
for i, bad in enumerate(["31/02/2026", "tomorrow", "2026-12-01", ""]):
    check(f"4{'abcd'[i]}", f"Enter invalid deadline '{bad}'", "Error message, nothing saved",
          lambda bad=bad: raises(lambda: sp.add_task(s2, "X", bad, 2, today=TODAY)) and not s2["tasks"])

# --- 5. Deadline in the past (IF/ELSE from the algorithm) ---------------
check("5", "Enter a deadline in the past", "Error message, nothing saved",
      lambda: raises(lambda: sp.add_task(s2, "X", fmt(TODAY - timedelta(days=1)), 2, today=TODAY)))
check("6", "Enter a deadline of today", "Task is accepted",
      lambda: sp.add_task(s2, "Due today", fmt(TODAY), 2, today=TODAY)["title"] == "Due today")

# --- 7. Invalid priority ------------------------------------------------
check("7", "Enter priority 9", "Error message, nothing saved",
      lambda: raises(lambda: sp.add_task(s2, "Y", fmt(TODAY), 9, today=TODAY)))

# --- 8. Unknown task ID -------------------------------------------------
check("8", "Complete a task ID that does not exist", "Error message, no crash",
      lambda: raises(lambda: sp.complete_task(s2, 999)))

# --- 9. Sorting ---------------------------------------------------------
s3 = sp.new_store()
sp.add_task(s3, "Late but high", fmt(TODAY + timedelta(days=10)), 1, today=TODAY)
sp.add_task(s3, "Soon but low", fmt(TODAY + timedelta(days=1)), 3, today=TODAY)
check("9a", "Sort by deadline", "Earliest deadline first",
      lambda: sp.sorted_tasks(s3, "deadline")[0]["title"] == "Soon but low")
check("9b", "Sort by priority", "High priority first",
      lambda: sp.sorted_tasks(s3, "priority")[0]["title"] == "Late but high")

# --- 10. Reminders / overdue -------------------------------------------
s4 = sp.new_store()
overdue = {"id": 1, "title": "Old", "deadline": (TODAY - timedelta(days=2)).isoformat(), "priority": 1, "done": False}
s4["tasks"] = [overdue,
               {"id": 2, "title": "Now", "deadline": TODAY.isoformat(), "priority": 2, "done": False},
               {"id": 3, "title": "Soon", "deadline": (TODAY + timedelta(days=2)).isoformat(), "priority": 2, "done": False},
               {"id": 4, "title": "Far", "deadline": (TODAY + timedelta(days=30)).isoformat(), "priority": 3, "done": False}]
r = sp.reminders(s4, TODAY)
check("10", "Check reminders", "1 overdue, 1 due today, 1 due soon; far task ignored",
      lambda: (len(r["overdue"]), len(r["today"]), len(r["soon"])) == (1, 1, 1))
sp.complete_task(s4, 1)
check("11", "Complete an overdue task", "It no longer appears as overdue",
      lambda: not sp.reminders(s4, TODAY)["overdue"])

# --- 12. Progress -------------------------------------------------------
check("12", "Progress with 1 of 4 tasks done", "25%", lambda: sp.progress(s4) == (1, 4, 25))
check("13", "Progress with no tasks", "0% and no crash", lambda: sp.progress(sp.new_store()) == (0, 0, 0))

# --- 14. Notes ----------------------------------------------------------
s5 = sp.new_store()
sp.add_note(s5, "Bring calculator on Friday")
check("14a", "Add a note", "Note is saved", lambda: len(s5["notes"]) == 1)
check("14b", "Add an empty note", "Error message", lambda: raises(lambda: sp.add_note(s5, "  ")))

# --- 15. Timetable ------------------------------------------------------
s6 = sp.new_store()
sp.add_lesson(s6, "monday", "09:00", "10:30", "Programming", "B12")
check("15a", "Add a valid lesson", "Lesson appears on Monday",
      lambda: sp.lessons_on(s6, "Monday")[0]["name"] == "Programming")
check("15b", "Add an overlapping lesson", "Clash error",
      lambda: raises(lambda: sp.add_lesson(s6, "Monday", "10:00", "11:00", "Maths", "A1")))
check("15c", "Lesson ends before it starts", "Error message",
      lambda: raises(lambda: sp.add_lesson(s6, "Tuesday", "11:00", "10:00", "Maths", "A1")))
check("15d", "Invalid day 'Sunday'", "Error message",
      lambda: raises(lambda: sp.add_lesson(s6, "Sunday", "09:00", "10:00", "Maths", "A1")))
check("15e", "Invalid time '25:99'", "Error message",
      lambda: raises(lambda: sp.add_lesson(s6, "Tuesday", "25:99", "26:00", "Maths", "A1")))

# --- 16. Saving and loading --------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    path = os.path.join(tmp, "data.json")
    storage.save_data(s3, path)
    check("16a", "Save then reload data", "Same tasks come back",
          lambda: storage.load_data(path)["tasks"] == s3["tasks"])
    check("16b", "Load when no file exists", "Empty store, no crash",
          lambda: storage.load_data(os.path.join(tmp, "missing.json")) == sp.new_store())
    with open(path, "w") as f:
        f.write("{ this is not json")
    check("16c", "Load a corrupted file", "Empty store, no crash",
          lambda: storage.load_data(path) == sp.new_store())

# --- Report -------------------------------------------------------------
print(f"\n{'Test':<5} {'Action':<48} {'Expected result':<50} Result")
print("-" * 112)
for name, action, expected, outcome in results:
    print(f"{name:<5} {action[:47]:<48} {expected[:49]:<50} {outcome}")
passed = sum(1 for r in results if r[3] == "PASS")
print("-" * 112)
print(f"{passed}/{len(results)} tests passed")
raise SystemExit(0 if passed == len(results) else 1)
