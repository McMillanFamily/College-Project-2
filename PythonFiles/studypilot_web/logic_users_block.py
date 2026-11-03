# =====================================================================
# PASTE 1: add these two lines to the imports at the top of logic.py
# =====================================================================
import re
from werkzeug.security import check_password_hash, generate_password_hash


# =====================================================================
# PASTE 2: add this block at the END of logic.py
# =====================================================================

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
