# StudyPilot

A college organiser that helps students keep track of tasks, deadlines, lessons and notes in one place.

Created for **The Apprentice App Challenge**, Foundation Apprenticeship (Year 2), South Lanarkshire College, East Kilbride.

## What it does

- **Task manager:** add, view and delete tasks
- **Deadline tracker:** every task has a deadline (DD/MM/YYYY)
- **Priority system:** High, Medium or Low
- **Progress tracker:** mark tasks complete and see a progress bar
- **Reminders:** overdue, due today and due within 3 days
- **Timetable:** weekly lessons with times and rooms, with clash checking
- **Notes:** write and save notes
- **Help section:** built-in guidance
- **Sorting:** by deadline or by priority

## Built with

- **Python 3** for the logic and backend
- **Flask** to display the app as a website
- **JSON file** for data storage (SQLite planned as a future upgrade)

## Project status

| Part | Status |
| --- | --- |
| Python logic (`logic.py`) | Working, 27 of 27 tests passing |
| Storage (`storage.py`) | Working (JSON file) |
| Flask website (`app.py`, `templates/`, `static/`) | Working, 20 of 20 scripted tests passing |
| Keyboard, phone-width and zoom checks | To be tested by hand in a browser |

## How to run

```
pip install -r requirements.txt
flask --app app run
```

Then open http://127.0.0.1:5000 in your browser.

**Run the tests** (from the project folder):

```
python3 tests/test_logic.py
python3 tests/test_web.py
```

Optional: set `STUDYPILOT_SECRET_KEY` to a long random value so sessions survive a restart.

## Project structure

```
app.py          Flask routes (web layer)
logic.py        Rules, validation and calculations (logic layer)
storage.py      Loads and saves the data file (storage layer)
templates/      HTML pages (Jinja2)
static/         style.css
tests/          test_logic.py and test_web.py
```

## Team

| Name | Role |
| --- | --- |
| Alex Cowan | Project Manager |
| Lewis McMillan | Lead Developer |
| Ciaran Bell | Developer |
| Ross | Developer |
| Daisy Wells | Documentation and Research Lead |
| Cian | Software Tester |

## Documentation

Full project documentation (requirements, design, algorithms, test plan and more) is in the StudyPilot Project Documentation document.

## Privacy

StudyPilot does not collect names, emails or passwords. Use made-up data only when testing.
