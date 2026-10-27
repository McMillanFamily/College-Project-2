# Study Pilot

A college organizer that helps students keep track of tasks, deadlines, lessons and notes in one place.

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

- **Python 3** for the logic and back end
- **Flask** to display the app as a website
- **JSON file** for data storage (SQLite planned as a future upgrade)

## Project status

| Part | Status |
| --- | --- |
| Python logic (`studypilot.py`) | Working (terminal prototype) |
| Automated tests (`test_studypilot.py`) | 27 of 27 passing |
| Flask website | In development |

## How to run

**Terminal prototype** (nothing to install):

```
python3 studypilot.py
```

**Run the tests:**

```
python3 test_studypilot.py
```

**Flask website** (once built):

```
pip install flask
flask --app app run
```

Then open http://127.0.0.1:5000 in your browser.

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
