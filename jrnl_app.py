import argparse
import sqlite3
from datetime import datetime, timedelta, date
from collections import defaultdict
from colorama import Fore, Back, Style, init

DB_FILE = "jrnl.db"
init(autoreset=True)  # colorama setup

# --- DB Helpers ---

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        # Create tasks table with all columns
        conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT CHECK(status IN ('todo','doing','waiting','done')) DEFAULT 'todo',
            creation_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            completion_date TEXT,
            recur TEXT
        )""")
        
        # Check if recur column exists, and add it if it doesn't
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN recur TEXT")
        except sqlite3.OperationalError:
            # Column already exists, which is fine
            pass
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            creation_date TEXT NOT NULL,
            task_id INTEGER,
            FOREIGN KEY(task_id) REFERENCES tasks(id)
        )""")

# --- Date Helpers ---

def parse_due(keyword):
    today = datetime.now().date()
    if keyword == "today":
        return today
    elif keyword == "tomorrow":
        return today + timedelta(days=1)
    elif keyword == "eow":
        return today + timedelta(days=(6 - today.weekday()))
    elif keyword == "eom":
        next_month = today.replace(day=28) + timedelta(days=4)
        return next_month - timedelta(days=next_month.day)
    elif keyword == "eoy":
        return today.replace(month=12, day=31)
    else:
        try:
            return datetime.strptime(keyword, "%Y-%m-%d").date()
        except ValueError:
            return today  # fallback

# --- Display Helpers ---

def format_task(task):
    # task now has 7 elements: id, title, status, creation_date, due_date, completion_date, recur
    tid, title, status, creation_date, due_date, completion_date, recur = task
    checkbox = "[x]" if status == "done" else "[ ]"

    # Color based on status
    if status == "doing":
        text = Fore.YELLOW + f"{checkbox} {title} (id:{tid})"
    elif status == "waiting":
        text = Back.WHITE + Fore.BLACK + f"{checkbox} {title} (id:{tid})"
    elif status == "done":
        text = Fore.GREEN + f"{checkbox} {title} (id:{tid})"
    else:  # todo
        text = f"{checkbox} {title}  (id:{tid})"

    # Show recur pattern if it exists
    if recur:
        text += f" (recur: {recur})"

    # Show due date
    due = datetime.strptime(due_date, "%Y-%m-%d").date()
    today = datetime.now().date()
    if status != "done":
        if due < today:
            text += Fore.RED + f" (due: {due})"
        elif due == today:
            text += Fore.CYAN + f" (due: {due})"
        else:
            text += f" (due: {due})"

    return text + Style.RESET_ALL

def format_note(note, indent="    "):
    nid, text, creation_date, task_id = note
    return indent + f"- {text} (id:{nid})"

def format_note_for_due_view(note, indent="      "):
    nid, text, creation_date, task_id = note
    return Back.YELLOW + Fore.BLACK + indent + f"- {text} (id:{nid})" + Style.RESET_ALL

# --- Command Handlers ---

def add_task(texts):
    today = datetime.now().date().strftime("%Y-%m-%d")
    added_count = 0
    with sqlite3.connect(DB_FILE) as conn:
        for raw in texts:
            raw = raw.strip()
            if "@" in raw:
                title, due_kw = raw.split("@", 1)
                due = parse_due(due_kw.strip())
            else:
                title = raw
                due = datetime.now().date()
            conn.execute(
                "INSERT INTO tasks (title,status,creation_date,due_date) VALUES (?,?,?,?)",
                (title.strip(), "todo", today, due.strftime("%Y-%m-%d"))
            )
            added_count += 1
    if added_count > 0:
        print(f"Added {added_count} task(s)")

def add_note(task_ids, text):
    today = datetime.now().date().strftime("%Y-%m-%d")
    added_count = 0
    with sqlite3.connect(DB_FILE) as conn:
        if not task_ids:
            conn.execute(
                "INSERT INTO notes (text,creation_date) VALUES (?,?)",
                (text, today)
            )
            added_count += 1
        else:
            for tid in task_ids:
                conn.execute(
                    "INSERT INTO notes (text,creation_date,task_id) VALUES (?,?,?)",
                    (text, today, tid)
                )
                added_count += 1
    if added_count > 0:
        if task_ids:
            print(f"Added note to {added_count} task(s)")
        else:
            print("Added standalone note")

def update_task_status(task_ids, status):
    updated_count = 0
    with sqlite3.connect(DB_FILE) as conn:
        for tid in task_ids:
            # If marking as done, check if it's a recurring task
            if status == "done":
                # Get the task's recur pattern
                task = conn.execute(
                    "SELECT title, due_date, recur FROM tasks WHERE id=?", (tid,)
                ).fetchone()
                
                if task and task[2]:  # If task has a recur pattern
                    # Create a new task with the same details but new due date
                    title, due_date, recur = task
                    new_due_date = calculate_next_due_date(due_date, recur)
                    
                    today = datetime.now().date().strftime("%Y-%m-%d")
                    conn.execute(
                        "INSERT INTO tasks (title,status,creation_date,due_date,recur) VALUES (?,?,?,?,?)",
                        (title, "todo", today, new_due_date, recur)
                    )
                    print(f"Created recurring task for '{title}'")
                
                # Set completion date for the original task
                today = datetime.now().date().strftime("%Y-%m-%d")
                conn.execute(
                    "UPDATE tasks SET status=?, completion_date=? WHERE id=?",
                    (status, today, tid)
                )
                updated_count += 1
            # If moving from done to another status, clear completion date
            elif status in ["todo", "doing", "waiting"]:
                conn.execute(
                    "UPDATE tasks SET status=?, completion_date=NULL WHERE id=?",
                    (status, tid)
                )
                updated_count += 1
            else:
                conn.execute(
                    "UPDATE tasks SET status=? WHERE id=?",
                    (status, tid)
                )
                updated_count += 1
    if updated_count > 0:
        status_display = "undone" if status == "todo" else status
        print(f"Updated {updated_count} task(s) to {status_display}")

def calculate_next_due_date(current_due_date, recur_pattern):
    """Calculate the next due date based on the recur pattern"""
    try:
        # Parse the recur pattern (e.g., "4w", "2d", "1m", "1y")
        if not recur_pattern or len(recur_pattern) < 2:
            return current_due_date
            
        number = int(recur_pattern[:-1])
        unit = recur_pattern[-1].lower()
        
        # Validate number range
        if number < 1 or number > 31:
            return current_due_date
        
        current_date = datetime.strptime(current_due_date, "%Y-%m-%d").date()
        
        if unit == 'd':  # days
            new_date = current_date + timedelta(days=number)
        elif unit == 'w':  # weeks
            new_date = current_date + timedelta(weeks=number)
        elif unit == 'm':  # months
            # For months, we add the months
            if current_date.month + number <= 12:
                new_date = current_date.replace(month=current_date.month + number)
            else:
                new_year = current_date.year + (current_date.month + number - 1) // 12
                new_month = (current_date.month + number - 1) % 12 + 1
                new_date = current_date.replace(year=new_year, month=new_month)
        elif unit == 'y':  # years
            new_date = current_date.replace(year=current_date.year + number)
        else:
            return current_due_date
            
        return new_date.strftime("%Y-%m-%d")
    except:
        return current_due_date

def set_task_recur(task_ids, recur_pattern):
    """Set the recur pattern for tasks"""
    # Validate the recur pattern
    if not recur_pattern or len(recur_pattern) < 2:
        print("Error: Invalid recur pattern. Use format: <number><unit> (e.g., 4w, 2d, 1m, 1y)")
        return False
        
    unit = recur_pattern[-1].lower()
    if unit not in ['d', 'w', 'm', 'y']:
        print("Error: Invalid unit. Use d (days), w (weeks), m (months), or y (years)")
        return False
        
    try:
        number = int(recur_pattern[:-1])
        if number < 1 or number > 31:
            print("Error: Number must be between 1 and 31")
            return False
    except ValueError:
        print("Error: Invalid number in recur pattern")
        return False
    
    with sqlite3.connect(DB_FILE) as conn:
        for tid in task_ids:
            conn.execute(
                "UPDATE tasks SET recur=? WHERE id=?",
                (recur_pattern, tid)
            )
    return True

def delete_task(task_ids):
    """Delete tasks from the database"""
    deleted_count = 0
    with sqlite3.connect(DB_FILE) as conn:
        for tid in task_ids:
            # First delete associated notes
            conn.execute("DELETE FROM notes WHERE task_id=?", (tid,))
            # Then delete the task
            cursor = conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
            if cursor.rowcount > 0:
                deleted_count += 1
    if deleted_count > 0:
        print(f"Deleted {deleted_count} task(s)")
    else:
        print("No tasks were deleted")

def delete_note(note_ids):
    """Delete notes from the database"""
    deleted_count = 0
    with sqlite3.connect(DB_FILE) as conn:
        for nid in note_ids:
            cursor = conn.execute("DELETE FROM notes WHERE id=?", (nid,))
            if cursor.rowcount > 0:
                deleted_count += 1
    if deleted_count > 0:
        print(f"Deleted {deleted_count} note(s)")
    else:
        print("No notes were deleted")

def show_journal():
    with sqlite3.connect(DB_FILE) as conn:
        # get tasks
        tasks = conn.execute(
            "SELECT id,title,status,creation_date,due_date,completion_date,recur FROM tasks ORDER BY creation_date ASC,id ASC"
        ).fetchall()

        # get notes
        notes = conn.execute(
            "SELECT id,text,creation_date,task_id FROM notes ORDER BY creation_date ASC,id ASC"
        ).fetchall()

    # group tasks/notes by creation_date
    grouped = defaultdict(lambda: {"tasks": [], "notes": []})
    for t in tasks:
        grouped[t[3]]["tasks"].append(t)
    for n in notes:
        if n[3]:  # attached to task
            # handled under task display
            pass
        else:
            grouped[n[2]]["notes"].append(n)

    for day in sorted(grouped.keys()):
        print(day)
        for task in grouped[day]["tasks"]:
            print("  " + format_task(task))
            # show notes for this task
            for n in notes:
                if n[3] == task[0]:
                    print(format_note(n, indent="      "))
        # show standalone notes
        for n in grouped[day]["notes"]:
            if not n[3]:
                print(format_note(n, indent="  "))

def show_due():
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute(
            "SELECT id,title,status,creation_date,due_date,completion_date,recur FROM tasks WHERE status != 'done' ORDER BY due_date ASC"
        ).fetchall()
        
        # Get all notes for tasks that will be displayed
        notes = conn.execute(
            "SELECT id,text,creation_date,task_id FROM notes WHERE task_id IN (SELECT id FROM tasks WHERE status != 'done') ORDER BY creation_date ASC,id ASC"
        ).fetchall()

    # Create a mapping of task_id to list of notes for that task
    task_notes = defaultdict(list)
    for note in notes:
        task_notes[note[3]].append(note)  # note[3] is task_id

    today = datetime.now().date()
    buckets = {"Overdue": [], "Due Today": [], "Upcoming": [], "No Due Date": []}

    for t in tasks:
        # t[4] is due_date
        if t[4]:  # Check if due date exists
            due = datetime.strptime(t[4], "%Y-%m-%d").date()
            if due < today:  # No need to check status since we filtered in query
                buckets["Overdue"].append(t)
            elif due == today:
                buckets["Due Today"].append(t)
            else:
                buckets["Upcoming"].append(t)
        else:
            buckets["No Due Date"].append(t)

    for label in ["Overdue", "Due Today", "Upcoming", "No Due Date"]:
        if buckets[label]:
            print(f"\n{label}")
            for t in buckets[label]:
                print("  " + format_task(t))
                # Show notes for this task if any exist
                task_id = t[0]  # t[0] is task id
                if task_id in task_notes:
                    for note in task_notes[task_id]:
                        print(format_note_for_due_view(note, indent="      "))  # 6 spaces for indentation

def show_task():
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute(
            "SELECT id,title,status,creation_date,due_date,completion_date,recur FROM tasks WHERE status != 'done' ORDER BY creation_date ASC"
        ).fetchall()

    # Group tasks by creation_date
    grouped = defaultdict(list)
    for t in tasks:
        grouped[t[3]].append(t)  # t[3] is creation_date

    for day in sorted(grouped.keys()):
        print(day)
        for task in grouped[day]:
            print("  " + format_task(task))

def show_note():
    with sqlite3.connect(DB_FILE) as conn:
        # get notes with their tasks (if any)
        notes = conn.execute("""
            SELECT n.id, n.text, n.creation_date, n.task_id, t.title
            FROM notes n
            LEFT JOIN tasks t ON n.task_id = t.id
            ORDER BY n.creation_date ASC, n.id ASC
        """).fetchall()

    # Group notes by creation_date
    grouped = defaultdict(list)
    for n in notes:
        grouped[n[2]].append(n)  # n[2] is creation_date

    for day in sorted(grouped.keys()):
        print(day)
        for note in grouped[day]:
            nid, text, creation_date, task_id, task_title = note
            if task_id:
                print(f"  - {text} (id: {nid}) (for task: {task_id}. {task_title})")
            else:
                print(f"  - {text} (id: {nid})")

def show_completed_tasks():
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute("""
            SELECT id, title, status, creation_date, due_date, completion_date, recur
            FROM tasks 
            WHERE status = 'done' AND completion_date IS NOT NULL
            ORDER BY completion_date ASC, id ASC
        """).fetchall()
    
    # Group tasks by completion date
    grouped = defaultdict(list)
    for t in tasks:
        completion_date = t[5]  # completion_date
        grouped[completion_date].append(t)
    
    # Display tasks grouped by completion date
    for completion_date in sorted(grouped.keys()):
        print(completion_date)
        for task in grouped[completion_date]:
            print("  " + format_task(task))

# --- CLI Parser ---

def main():
    init_db()

    parser = argparse.ArgumentParser(prog="jrnl", add_help=False)
    parser.add_argument("command", nargs="?", default=None)
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()

    cmd = args.command
    rest = args.args

    if cmd is None:
        show_journal()
    elif cmd == "task" and rest:  # Only handle as add task command if there are arguments
        add_task(" ".join(rest).split(","))
    elif cmd == "t" and rest:  # Alias for adding tasks
        add_task(" ".join(rest).split(","))
    elif cmd == "note" and rest:  # Only handle as add note command if there are arguments
        if all(c.isdigit() or c == "," for c in rest[0]):
            ids = rest[0].split(",")
            text = " ".join(rest[1:])
            if text:
                add_note([int(i) for i in ids], text)
            else:
                print("Error: Please provide note text")
        else:
            text = " ".join(rest)
            if text:
                add_note([], text)
            else:
                print("Error: Please provide note text")
    elif cmd == "n" and rest:  # Alias for adding notes
        if all(c.isdigit() or c == "," for c in rest[0]):
            ids = rest[0].split(",")
            text = " ".join(rest[1:])
            if text:
                add_note([int(i) for i in ids], text)
            else:
                print("Error: Please provide note text")
        else:
            text = " ".join(rest)
            if text:
                add_note([], text)
            else:
                print("Error: Please provide note text")
    elif cmd == "rm":
        if rest:
            task_ids = []
            note_ids = []
            
            # Handle all arguments
            for arg in rest:
                # Handle comma-separated IDs
                id_parts = arg.split(",")
                for id_part in id_parts:
                    # Check if argument has a prefix
                    if id_part.startswith("t") and id_part[1:].isdigit():
                        task_ids.append(int(id_part[1:]))
                    elif id_part.startswith("n") and id_part[1:].isdigit():
                        note_ids.append(int(id_part[1:]))
                    elif id_part.isdigit():
                        # For backward compatibility, assume it's a task ID
                        task_ids.append(int(id_part))
                    else:
                        print(f"Error: Invalid ID format '{id_part}'. Use 't<ID>' for tasks or 'n<ID>' for notes")
                        return
            
            # Delete items
            if task_ids:
                delete_task(task_ids)
            if note_ids:
                delete_note(note_ids)
        else:
            print("Error: Please provide IDs to delete")
    elif cmd in ["task", "t"]:
        show_task()
    elif cmd in ["note", "n"]:
        show_note()
    elif cmd == "done" and not rest:  # Only if no additional arguments (to distinguish from 'done' status command)
        show_completed_tasks()
    elif cmd in ["due", "d"]:
        if rest and all(c.isdigit() or c == "," for c in rest[0]):
            # Parse task IDs (supporting multiple IDs separated by commas)
            task_ids = []
            for arg in rest[0].split(","):
                if arg.isdigit():
                    task_ids.append(int(arg))
            
            # Parse the date
            if len(rest) > 1:
                due = parse_due(rest[1])
                updated_count = 0
                with sqlite3.connect(DB_FILE) as conn:
                    for tid in task_ids:
                        conn.execute(
                            "UPDATE tasks SET due_date=? WHERE id=?",
                            (due.strftime("%Y-%m-%d"), tid)
                        )
                        updated_count += 1
                if updated_count > 0:
                    print(f"Updated due date for {updated_count} task(s) to {due.strftime('%Y-%m-%d')}")
            else:
                print("Error: Please provide a date.")
        else:
            show_due()
    elif cmd == "recur":
        if rest and all(c.isdigit() or c == "," for c in rest[0]) and len(rest) > 1:
            # Parse task IDs (supporting multiple IDs separated by commas)
            task_ids = []
            for arg in rest[0].split(","):
                if arg.isdigit():
                    task_ids.append(int(arg))
            
            # Parse the recur pattern
            recur_pattern = rest[1]
            if set_task_recur(task_ids, recur_pattern):
                print(f"Set recur pattern '{recur_pattern}' for {len(task_ids)} task(s)")
        else:
            print("Error: Please provide task IDs and a recur pattern (e.g., 4w, 2d, 1m, 1y)")
    elif cmd in ["undone", "doing", "waiting"]:  # Removed "done" from here
        if rest:
            ids = []
            for arg in rest:
                if all(c.isdigit() or c == "," for c in arg):
                    ids.extend([int(i) for i in arg.split(",")])
                else:
                    print(f"Error: Invalid task ID '{arg}'")
                    return
            if ids:
                # "undone" should set status back to "todo"
                status = "todo" if cmd == "undone" else cmd
                update_task_status(ids, status)
            else:
                print("Error: Please provide valid task IDs")
        else:
            print("Error: Please provide task IDs")
    elif cmd == "done":  # Handle "done" status command
        if rest:
            ids = []
            for arg in rest:
                if all(c.isdigit() or c == "," for c in arg):
                    ids.extend([int(i) for i in arg.split(",")])
                else:
                    print(f"Error: Invalid task ID '{arg}'")
                    return
            if ids:
                update_task_status(ids, "done")
            else:
                print("Error: Please provide valid task IDs")
        else:
            print("Error: Please provide task IDs")
    elif cmd == "x":
        if rest:
            ids = []
            for arg in rest:
                if all(c.isdigit() or c == "," for c in arg):
                    ids.extend([int(i) for i in arg.split(",")])
                else:
                    print(f"Error: Invalid task ID '{arg}'")
                    return
            if ids:
                update_task_status(ids, "done")
            else:
                print("Error: Please provide valid task IDs")
        else:
            print("Error: Please provide task IDs")
    elif cmd in ["help", "h"]:
        print("""
jrnl - Command Line Journal and Task Manager

USAGE:
    jrnl [command] [arguments...]

COMMANDS:
    jrnl                    Show journal (default view)
    jrnl task <text>[,<text>...]     Add tasks
    jrnl t <text>[,<text>...]        Add tasks (alias)
    jrnl note [<task id>[,<task id>...]] <text>  Add notes
    jrnl n [<task id>[,<task id>...]] <text>     Add notes (alias)
    jrnl task (or t)        Show all unfinished tasks
    jrnl note (or n)        Show all notes
    jrnl done               Show all completed tasks grouped by completion date
    jrnl due                Show tasks grouped by due date
    jrnl due <id>[,<id>...] <date>  Change due date for task(s)
    jrnl recur <id>[,<id>...] <Nd|Nw|Nm|Ny>  Make task(s) recurring
    jrnl undone <id>[,<id>...]    Mark tasks as not done
    jrnl doing <id>[,<id>...]     Mark tasks as in progress
    jrnl waiting <id>[,<id>...]   Mark tasks as waiting
    jrnl done <id>[,<id>...]      Mark tasks as done
    jrnl x <id>[,<id>...]         Mark tasks as done (shortcut)
    jrnl rm t<id>[,n<id>...]      Delete tasks (t) or notes (n)
    jrnl help (or h)        Show this help message

DATE FORMATS:
    Keywords:
        today       - Today's date
        tomorrow    - Tomorrow's date
        eow         - End of current week (Saturday)
        eom         - End of current month
        eoy         - End of current year
    
    Explicit dates:
        YYYY-MM-DD  - Specific date (e.g., 2025-12-25)
    
    Recur patterns:
        Nd          - Every N days (N between 1-31)
        Nw          - Every N weeks (N between 1-31)
        Nm          - Every N months (N between 1-31)
        Ny          - Every N years (N between 1-31)

EXAMPLES:
    jrnl task "Do homework @tomorrow,Finish report @2025-12-25"
    jrnl t "Do homework @tomorrow,Finish report @2025-12-25"
    jrnl note 2 "Remember to check references"
    jrnl n 2 "Remember to check references"
    jrnl done 2
    jrnl due 1,2,3 eom
    jrnl recur 2,3 4w
    jrnl rm t1,n2
    jrnl due
    jrnl task
    jrnl note
    jrnl done
""")

if __name__ == "__main__":
    main()
