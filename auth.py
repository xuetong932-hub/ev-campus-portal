"""User login and registration backed by ev_campus_dataset.csv.

The dataset has no separate user table, so the Session_ID column is the list
of known user IDs. Registering appends a new row to the same CSV with only
Session_ID and User_Type filled in. Task 1 and Task 2 drop rows without a
Grid_Status_Label, so registrations never change the cleaned data or model.
"""
import csv
import json
import re
import threading
from pathlib import Path

ID_COLUMN = 'Session_ID'
USER_TYPES = ['Staff', 'Student', 'Visitor']
# Letters, digits, '-' and '_' only, so an ID can never break the CSV format.
ID_PATTERN = re.compile(r'^[A-Z0-9][A-Z0-9_-]{2,19}$')

# One writer at a time: Streamlit serves every user from the same process.
_write_lock = threading.Lock()


def normalise_id(user_id):
    """IDs are compared case-insensitively, without surrounding spaces."""
    return str(user_id or '').strip().upper()


def load_user_ids(path):
    """Return the set of registered IDs. Read fresh each time so new
    registrations are visible immediately."""
    with Path(path).open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if ID_COLUMN not in (reader.fieldnames or []):
            raise ValueError(f'{Path(path).name} has no {ID_COLUMN} column.')
        return {normalise_id(row[ID_COLUMN]) for row in reader if row[ID_COLUMN]}


def is_registered(path, user_id):
    return normalise_id(user_id) in load_user_ids(path)


def validate_new_id(user_id):
    """Return an error message, or None if the ID can be registered."""
    user_id = normalise_id(user_id)
    if not user_id:
        return 'Please enter a user ID.'
    if not ID_PATTERN.match(user_id):
        return ('User ID must be 3-20 characters: letters, digits, "-" or "_", '
                'starting with a letter or digit.')
    return None


def suggest_id(path):
    """Next free ID in the dataset's SESS-#### style."""
    numbers = [int(m.group(1)) for i in load_user_ids(path)
               if (m := re.fullmatch(r'SESS-(\d+)', i))]
    return f'SESS-{max(numbers, default=999) + 1}'


def _onboarding_file(path):
    return Path(path).with_name('onboarded_users.json')


def needs_onboarding(path, user_id):
    """New users are those who registered through the portal (their row has no
    Grid_Status_Label) and have not finished or skipped the guide yet."""
    user_id = normalise_id(user_id)
    with Path(path).open(newline='', encoding='utf-8-sig') as f:
        registered_here = any(normalise_id(r[ID_COLUMN]) == user_id and not (r.get('Grid_Status_Label') or '').strip()
                              for r in csv.DictReader(f))
    if not registered_here:
        return False
    store = _onboarding_file(path)
    done = json.loads(store.read_text(encoding='utf-8')) if store.exists() else []
    return user_id not in done


def mark_onboarded(path, user_id):
    store = _onboarding_file(path)
    with _write_lock:
        done = json.loads(store.read_text(encoding='utf-8')) if store.exists() else []
        if normalise_id(user_id) not in done:
            done.append(normalise_id(user_id))
            store.write_text(json.dumps(done, indent=2), encoding='utf-8')


def register(path, user_id, user_type):
    """Append a new user row to the dataset and return the stored ID.
    Raises ValueError if the input is invalid or the ID already exists."""
    user_id = normalise_id(user_id)
    error = validate_new_id(user_id)
    if error:
        raise ValueError(error)
    if user_type not in USER_TYPES:
        raise ValueError(f'User type must be one of: {", ".join(USER_TYPES)}.')
    path = Path(path)
    with _write_lock:
        # Check again inside the lock so two people cannot claim the same ID.
        if user_id in load_user_ids(path):
            raise ValueError(f'{user_id} is already registered. Please log in instead.')
        with path.open(newline='', encoding='utf-8-sig') as f:
            header = next(csv.reader(f))
        needs_newline = path.read_bytes()[-1:] not in (b'\n', b'')
        with path.open('a', newline='', encoding='utf-8') as f:
            if needs_newline:
                f.write('\n')
            row = {col: '' for col in header}
            row.update({ID_COLUMN: user_id, 'User_Type': user_type})
            csv.DictWriter(f, fieldnames=header, lineterminator='\n').writerow(row)
    return user_id
