"""
StudyPilot website tests (Part B of the test plan, the ones a script can check).
Run from the project folder with:  python3 tests/test_web.py
Uses a temporary data file, so your real data is never touched.
Keyboard, phone-width and zoom tests (W14 to W16) still need a person and a browser.
"""

import os
import re
import sys
import tempfile
from datetime import date, timedelta

tmp = tempfile.TemporaryDirectory()
os.environ["STUDYPILOT_DATA"] = os.path.join(tmp.name, "data.json")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import app as web  # noqa: E402

web.app.config["TESTING"] = True
results = []


def fmt(d):
    return d.strftime("%d/%m/%Y")


def iso(d):
    return d.isoformat()


def check(name, action, expected, fn):
    try:
        ok = bool(fn())
    except Exception as exc:
        ok, action = False, action + f"  [crashed: {exc!r}]"
    results.append((name, action, expected, "PASS" if ok else "FAIL"))


def new_client():
    c = web.app.test_client()
    page = c.get("/tasks").get_data(as_text=True)
    token = re.search(r'name="csrf" value="([^"]+)"', page).group(1)
    return c, token


def post(c, token, url, **data):
    return c.post(url, data={"csrf": token, **data}, follow_redirects=True).get_data(as_text=True)


c, tok = new_client()
today = date.today()

# W1 / W2
home = c.get("/")
check("W1", "Open the home page", "200 OK with progress and reminders",
      lambda: home.status_code == 200 and b"Your progress" in home.data)
check("W2", "Open every page in the menu", "All return 200",
      lambda: all(c.get(u).status_code == 200 for u in ("/tasks", "/timetable", "/notes", "/help")))

# W3 add a valid task
page = post(c, tok, "/tasks/add", title="English essay", deadline=iso(today + timedelta(days=5)), priority="1")
check("W3", "Add a valid task", "Task listed with a success message",
      lambda: "English essay" in page and "Task saved" in page)

# W4 / W5 / W9 / invalid priority
page = post(c, tok, "/tasks/add", title="  ", deadline=iso(today), priority="2")
check("W4", "Empty task name", "Error message shown", lambda: "cannot be empty" in page)
page = post(c, tok, "/tasks/add", title="Bad date", deadline="31/02/2026", priority="2")
check("W5", "Invalid deadline", "Error message shown", lambda: "not a valid date" in page and "Bad date" not in page.split("Add a task")[0].split("<tbody>")[-1])
page = post(c, tok, "/tasks/add", title="Due today", deadline=iso(today), priority="2")
check("W9a", "Deadline of today", "Accepted", lambda: "Task saved: Due today" in page)
page = post(c, tok, "/tasks/add", title="Too late", deadline=iso(today - timedelta(days=1)), priority="2")
check("W9b", "Deadline in the past", "Rejected", lambda: "in the past" in page)
page = post(c, tok, "/tasks/add", title="Bad priority", deadline=iso(today), priority="9")
check("W5b", "Priority 9", "Rejected", lambda: "Priority must be" in page)

# W6 refresh does not add twice (Post/Redirect/Get)
r = c.post("/tasks/add", data={"csrf": tok, "title": "Once only", "deadline": iso(today), "priority": "3"})
check("W6a", "Submit a task", "Server redirects (303/302) to the task list",
      lambda: r.status_code in (302, 303) and r.headers["Location"].endswith("/tasks"))
c.get("/tasks"); c.get("/tasks")
check("W6b", "Reload the page twice", "Task appears only once",
      lambda: c.get("/tasks").get_data(as_text=True).count("<strong>Once only</strong>") == 1)

# W7 complete
store = web.load_data()
tid = next(t["id"] for t in store["tasks"] if t["title"] == "English essay")
page = post(c, tok, f"/tasks/{tid}/complete")
check("W7", "Mark a task done", "Shown as Done, progress above 0%",
      lambda: "Well done" in page and "Done</span>" in page and 'aria-valuenow="0"' not in c.get("/").get_data(as_text=True))

# W8 sorting
by_pri = c.get("/tasks?sort=priority").get_data(as_text=True)
by_dead = c.get("/tasks?sort=deadline").get_data(as_text=True)
check("W8", "Sort by priority then deadline", "Order changes; bad sort value does not crash",
      lambda: by_pri != by_dead and c.get("/tasks?sort=evil").status_code == 200)

# W10 timetable clash
post(c, tok, "/timetable/add", day="Monday", start="09:00", end="10:30", name="Programming", room="B12")
page = post(c, tok, "/timetable/add", day="Monday", start="10:00", end="11:00", name="Maths", room="A1")
check("W10", "Add overlapping lesson", "Clash message", lambda: "clashes" in page)
page = post(c, tok, "/timetable/add", day="Monday", start="11:00", end="12:00", name="Maths", room="")
check("W10b", "Add lesson with no room", "Saved with room TBC", lambda: "room TBC" in page)

# W11 XSS
page = post(c, tok, "/notes/add", text="<script>alert(1)</script><b>hi</b>")
check("W11", "Note containing HTML", "Shown as text, not run",
      lambda: "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page)

# W12 persistence (a brand new client reads the same saved file)
c2 = web.app.test_client()
check("W12", "Fresh browser session", "Data is still there",
      lambda: "English essay" in c2.get("/tasks").get_data(as_text=True))

# W13 404 and extra safety checks
r = c.get("/nope")
check("W13", "Unknown page", "Friendly 404", lambda: r.status_code == 404 and b"could not find" in r.data)
r = c.post("/tasks/add", data={"title": "x", "deadline": iso(today), "priority": "1"})
check("S1", "POST without CSRF token", "Rejected, nothing saved",
      lambda: r.status_code in (302, 303) and "x" not in [t["title"] for t in web.load_data()["tasks"]])
page = post(c, tok, "/tasks/99999/delete")
check("S2", "Delete a task that does not exist", "Error message, no crash", lambda: "no task with ID 99999" in page)
check("S3", "GET on a change URL", "Not allowed (405)", lambda: c.get("/tasks/1/delete").status_code == 405)

print(f"\n{'Test':<6} {'Action':<42} {'Expected':<48} Result")
print("-" * 106)
for n, a, e, r_ in results:
    print(f"{n:<6} {a[:41]:<42} {e[:47]:<48} {r_}")
passed = sum(1 for r_ in results if r_[3] == "PASS")
print("-" * 106)
print(f"{passed}/{len(results)} tests passed")
tmp.cleanup()
raise SystemExit(0 if passed == len(results) else 1)
