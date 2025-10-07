import argparse
import sqlite3
from datetime import datetime, timedelta, date
from collections import defaultdict
from colorama import Fore, Back, Style, init

DB_FILE = "jrnl.db"
init(autoreset=True)  # colorama setup

# --- Date Helpers ---

def format_date_with_day(date_str):
    """Format a date string (YYYY-MM-DD) to include the day name"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%A, %Y-%m-%d")
    except ValueError:
        # If parsing fails, return the original string
        return date_str

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
        
        # Create table for linking notes to each other
        conn.execute("""
        CREATE TABLE IF NOT EXISTS note_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note1_id INTEGER NOT NULL,
            note2_id INTEGER NOT NULL,
            FOREIGN KEY(note1_id) REFERENCES notes(id),
            FOREIGN KEY(note2_id) REFERENCES notes(id),
            UNIQUE(note1_id, note2_id)
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
        # Check for day names (monday, tuesday, etc.)
        day_names = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        keyword_lower = keyword.lower()
        if keyword_lower in day_names:
            target_weekday = day_names[keyword_lower]
            days_ahead = (target_weekday - today.weekday() + 7) % 7
            # If the day is today, move to next week
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead)
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
        text = Back.YELLOW + Fore.BLACK + f"{checkbox} {title} (id:{tid})" + Style.RESET_ALL
    elif status == "waiting":
        text = Back.LIGHTBLACK_EX + Fore.WHITE + f"{checkbox} {title} (id:{tid})" + Style.RESET_ALL
    elif status == "done":
        text = Fore.GREEN + f"{checkbox} {title} (id:{tid})" + Style.RESET_ALL
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
            text += Fore.RED + f" (due: {format_date_with_day(due_date)})"
        elif due == today:
            text += Fore.CYAN + f" (due: {format_date_with_day(due_date)})"
        else:
            text += f" (due: {format_date_with_day(due_date)})"

    return text + Style.RESET_ALL

def format_note(note, indent="\t"):
    nid, text, creation_date, task_id = note
    return Fore.YELLOW + indent + f"- {text} (id:{nid}) ({creation_date})" + Style.RESET_ALL

def search_tasks_and_notes(search_text):
    """Search for tasks and notes containing the search text"""
    with sqlite3.connect(DB_FILE) as conn:
        # Search in tasks (title column)
        tasks = conn.execute(
            """
            SELECT id,title,status,creation_date,due_date,completion_date,recur 
            FROM tasks 
            WHERE title LIKE ? 
            ORDER BY creation_date ASC,id ASC
            """,
            (f"%{search_text}%",)
        ).fetchall()

        # Search in notes (text column)
        notes = conn.execute(
            """
            SELECT id,text,creation_date,task_id 
            FROM notes 
            WHERE text LIKE ? 
            ORDER BY creation_date ASC,id ASC
            """,
            (f"%{search_text}%",)
        ).fetchall()

    # Group by creation_date
    grouped = defaultdict(lambda: {"tasks": [], "notes": []})
    
    # Add tasks to grouped dict
    for t in tasks:
        grouped[t[3]]["tasks"].append(t)  # t[3] is creation_date
    
    # Add notes to grouped dict
    for n in notes:
        if n[3]:  # attached to task
            # We'll handle these under task display
            pass
        else:
            grouped[n[2]]["notes"].append(n)  # n[2] is creation_date

    # Get all notes that are attached to tasks (we need to show them with their tasks)
    # Also get tasks that have notes matching the search term but the task title doesn't match
    task_ids_from_notes = [note[3] for note in notes if note[3]]  # task_id for attached notes
    task_ids_from_tasks = [task[0] for task in tasks]  # id for matching tasks
    
    # Get all unique task IDs we need to display
    all_task_ids = list(set(task_ids_from_notes + task_ids_from_tasks))
    
    # Get the actual task records for those IDs
    if all_task_ids:
        with sqlite3.connect(DB_FILE) as conn:
            task_query = """
                SELECT id,title,status,creation_date,due_date,completion_date,recur 
                FROM tasks 
                WHERE id IN ({})
                ORDER BY creation_date ASC,id ASC
            """.format(",".join("?" * len(all_task_ids)))
            all_tasks = conn.execute(task_query, all_task_ids).fetchall()
            
            # Update grouped with all tasks (in case some were missing)
            for t in all_tasks:
                grouped[t[3]]["tasks"].append(t)  # t[3] is creation_date
            
            # Remove duplicates
            for day in grouped:
                # Remove duplicate tasks
                seen_task_ids = set()
                unique_tasks = []
                for t in grouped[day]["tasks"]:
                    if t[0] not in seen_task_ids:
                        unique_tasks.append(t)
                        seen_task_ids.add(t[0])
                grouped[day]["tasks"] = unique_tasks

    return grouped, tasks, notes

def display_search_results(grouped):
    """Display search results in the same format as the default journal view"""
    has_results = any(grouped[day]["tasks"] or grouped[day]["notes"] for day in grouped)
    
    if not has_results:
        print("No matching tasks or notes found.")
        return

    # Get all tasks and notes to properly display attached notes
    with sqlite3.connect(DB_FILE) as conn:
        all_tasks = conn.execute(
            "SELECT id,title,status,creation_date,due_date,completion_date,recur FROM tasks ORDER BY creation_date ASC,id ASC"
        ).fetchall()
        all_notes = conn.execute(
            "SELECT id,text,creation_date,task_id FROM notes ORDER BY creation_date ASC,id ASC"
        ).fetchall()

    # Create a mapping of task_id to list of notes for that task
    task_notes = defaultdict(list)
    for note in all_notes:
        if note[3]:  # note[3] is task_id
            task_notes[note[3]].append(note)

    for day in sorted(grouped.keys()):
        tasks_for_day = grouped[day]["tasks"]
        notes_for_day = grouped[day]["notes"]
        
        if tasks_for_day or notes_for_day:
            print()
            print(format_date_with_day(day))
            
            # Display tasks
            for task in tasks_for_day:
                print("\t" + format_task(task))
                # Show notes for this task
                task_id = task[0]  # task[0] is task id
                if task_id in task_notes:
                    for note in task_notes[task_id]:
                        print(format_note(note, indent="\t\t"))
            
            # Display standalone notes
            for note in notes_for_day:
                if not note[3]:  # note[3] is task_id, only show standalone notes
                    print(format_note(note, indent="\t"))

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

def update_task_status(task_ids, status, note_text=None):
    updated_count = 0
    with sqlite3.connect(DB_FILE) as conn:
        for tid in task_ids:
            # If marking as done, check if it's a recurring task
            if status == "done":
                # Get the task's recur pattern
                task = conn.execute(
                    "SELECT title, due_date, recur FROM tasks WHERE id=?", (tid,)
                ).fetchone()
                today = datetime.now().date().strftime("%Y-%m-%d")                
                if task and task[2]:  # If task has a recur pattern
                    # Create a new task with the same details but new due date

                    title, due_date, recur = task
                    new_due_date = calculate_next_due_date(today, recur)
                    
                    conn.execute(
                        "INSERT INTO tasks (title,status,creation_date,due_date,recur) VALUES (?,?,?,?,?)",
                        (title, "todo", today, new_due_date, recur)
                    )
                    print(f"Created recurring task for '{title}'")
                
                # Set completion date for the original task
                conn.execute(
                    "UPDATE tasks SET status=?, completion_date=? WHERE id=?",
                    (status, today, tid)
                )
                updated_count += 1
                
                # Add note to the completed task if provided
                if note_text:
                    conn.execute(
                        "INSERT INTO notes (text,creation_date,task_id) VALUES (?,?,?)",
                        (note_text, today, tid)
                    )
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

def edit_task(task_id, new_title):
    """Edit the title of a task"""
    with sqlite3.connect(DB_FILE) as conn:
        # Check if task exists
        cursor = conn.execute("SELECT id FROM tasks WHERE id=?", (task_id,))
        if not cursor.fetchone():
            print(f"Error: Task with ID {task_id} not found")
            return False
        
        # Update the task title
        conn.execute(
            "UPDATE tasks SET title=? WHERE id=?",
            (new_title, task_id)
        )
        print(f"Updated task {task_id} title to: {new_title}")
        return True

def edit_note(note_id, new_text):
    """Edit the text of a note"""
    with sqlite3.connect(DB_FILE) as conn:
        # Check if note exists
        cursor = conn.execute("SELECT id FROM notes WHERE id=?", (note_id,))
        if not cursor.fetchone():
            print(f"Error: Note with ID {note_id} not found")
            return False
        
        # Update the note text
        conn.execute(
            "UPDATE notes SET text=? WHERE id=?",
            (new_text, note_id)
        )
        print(f"Updated note {note_id} text to: {new_text}")
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
            # First delete any links associated with this note
            conn.execute("DELETE FROM note_links WHERE note1_id=? OR note2_id=?", (nid, nid))
            # Then delete the note itself
            cursor = conn.execute("DELETE FROM notes WHERE id=?", (nid,))
            if cursor.rowcount > 0:
                deleted_count += 1
    if deleted_count > 0:
        print(f"Deleted {deleted_count} note(s)")
    else:
        print("No notes were deleted")

def link_notes(note1_id, note2_id):
    """Create a link between two notes"""
    if note1_id == note2_id:
        print(f"Error: Cannot link a note to itself (id: {note1_id})")
        return False
        
    with sqlite3.connect(DB_FILE) as conn:
        # Check if both notes exist
        note1_exists = conn.execute("SELECT id FROM notes WHERE id=?", (note1_id,)).fetchone()
        note2_exists = conn.execute("SELECT id FROM notes WHERE id=?", (note2_id,)).fetchone()
        
        if not note1_exists:
            print(f"Error: Note with ID {note1_id} does not exist")
            return False
        if not note2_exists:
            print(f"Error: Note with ID {note2_id} does not exist")
            return False
        
        # Check if the link already exists (in either direction)
        link_exists = conn.execute(
            "SELECT id FROM note_links WHERE (note1_id=? AND note2_id=?) OR (note1_id=? AND note2_id=?)",
            (note1_id, note2_id, note2_id, note1_id)
        ).fetchone()
        
        if link_exists:
            print(f"Notes {note1_id} and {note2_id} are already linked")
            return True
        
        # Create the link (order notes in ascending order for consistency)
        if note1_id > note2_id:
            note1_id, note2_id = note2_id, note1_id
            
        conn.execute(
            "INSERT INTO note_links (note1_id, note2_id) VALUES (?, ?)",
            (note1_id, note2_id)
        )
        print(f"Linked notes {note1_id} and {note2_id}")
        return True

def unlink_notes(note1_id, note2_id):
    """Remove a link between two notes"""
    with sqlite3.connect(DB_FILE) as conn:
        # Check if both notes exist
        note1_exists = conn.execute("SELECT id FROM notes WHERE id=?", (note1_id,)).fetchone()
        note2_exists = conn.execute("SELECT id FROM notes WHERE id=?", (note2_id,)).fetchone()
        
        if not note1_exists:
            print(f"Error: Note with ID {note1_id} does not exist")
            return False
        if not note2_exists:
            print(f"Error: Note with ID {note2_id} does not exist")
            return False
        
        # Delete the link (handle it in either direction)
        cursor = conn.execute(
            "DELETE FROM note_links WHERE (note1_id=? AND note2_id=?) OR (note1_id=? AND note2_id=?)",
            (note1_id, note2_id, note2_id, note1_id)
        )
        
        if cursor.rowcount > 0:
            print(f"Unlinked notes {note1_id} and {note2_id}")
            return True
        else:
            print(f"Notes {note1_id} and {note2_id} were not linked")
            return True

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
        print()
        print(format_date_with_day(day))
        for task in grouped[day]["tasks"]:
            print("\t" + format_task(task))
            # show notes for this task
            for n in notes:
                if n[3] == task[0]:
                    print(format_note(n, indent="\t\t"))
        # show standalone notes
        for n in grouped[day]["notes"]:
            if not n[3]:
                print(format_note(n, indent="\t"))

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
    # Calculate the end of this week (Sunday) and end of this month
    end_of_week = today + timedelta(days=(6 - today.weekday()))
    # For end of month, we get the last day of the current month
    if today.month == 12:
        end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    buckets = {"Overdue": [], "Due Today": [], "This Week": [], "This Month": [], "Future": [], "No Due Date": []}

    for t in tasks:
        # t[4] is due_date
        if t[4]:  # Check if due date exists
            due = datetime.strptime(t[4], "%Y-%m-%d").date()
            if due < today:  # No need to check status since we filtered in query
                buckets["Overdue"].append(t)
            elif due == today:
                buckets["Due Today"].append(t)
            elif due <= end_of_week:
                buckets["This Week"].append(t)
            elif due <= end_of_month:
                buckets["This Month"].append(t)
            else:
                buckets["Future"].append(t)
        else:
            buckets["No Due Date"].append(t)

    # Updated order: Overdue, Due Today, This Week, This Month, Future, No Due Date
    for label in ["Overdue", "Due Today", "This Week", "This Month", "Future", "No Due Date"]:
        if buckets[label]:
            print(f"\n{label}")
            for t in buckets[label]:
                print("\t" + format_task(t))
                # Show notes for this task if any exist
                task_id = t[0]  # t[0] is task id
                if task_id in task_notes:
                    for note in task_notes[task_id]:
                        print(format_note(note, indent="\t\t"))  # 6 spaces for indentation

def show_task():
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute(
            "SELECT id,title,status,creation_date,due_date,completion_date,recur FROM tasks WHERE status != 'done' ORDER BY creation_date ASC"
        ).fetchall()
        
        # Get all notes for tasks that will be displayed
        notes = conn.execute(
            "SELECT id,text,creation_date,task_id FROM notes WHERE task_id IN (SELECT id FROM tasks WHERE status != 'done') ORDER BY creation_date ASC,id ASC"
        ).fetchall()

    # Create a mapping of task_id to list of notes for that task
    task_notes = defaultdict(list)
    for note in notes:
        task_notes[note[3]].append(note)  # note[3] is task_id

    # Group tasks by creation_date
    grouped = defaultdict(list)
    for t in tasks:
        grouped[t[3]].append(t)  # t[3] is creation_date

    for day in sorted(grouped.keys()):
        print()
        print(format_date_with_day(day))
        for task in grouped[day]:
            print("\t" + format_task(task))
            # Show notes for this task if any exist
            task_id = task[0]  # task[0] is task id
            if task_id in task_notes:
                for note in task_notes[task_id]:
                    print(format_note(note, indent="\t\t"))  # 6 spaces for indentation

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
        print()
        print(format_date_with_day(day))
        for note in grouped[day]:
            nid, text, creation_date, task_id, task_title = note
            if task_id:
                print(Fore.YELLOW + f"\t- {text} (id: {nid}) ({creation_date}) (for task: {task_id}. {task_title})" + Style.RESET_ALL)
            else:
                print(Fore.YELLOW + f"\t- {text} (id: {nid}) ({creation_date})" + Style.RESET_ALL)

def show_note_details(note_id):
    """Show details of a specific note, including linked notes"""
    with sqlite3.connect(DB_FILE) as conn:
        # Get the specific note
        note = conn.execute("""
            SELECT n.id, n.text, n.creation_date, n.task_id, t.title
            FROM notes n
            LEFT JOIN tasks t ON n.task_id = t.id
            WHERE n.id=?
        """, (note_id,)).fetchone()
        
        if not note:
            print(f"Error: Note with ID {note_id} does not exist")
            return
        
        nid, text, creation_date, task_id, task_title = note
        
        # Print the note text in consistent format
        if task_id:
            print(Fore.YELLOW + f"- {text} (id:{nid}) ({creation_date}) (for task: {task_id}. {task_title})" + Style.RESET_ALL)
        else:
            print(Fore.YELLOW + f"- {text} (id:{nid}) ({creation_date})" + Style.RESET_ALL)
        
        # Get linked notes with their task information and creation dates
        linked_notes = conn.execute("""
            SELECT nl.note1_id, nl.note2_id, n1.text as note1_text, n2.text as note2_text, 
                   n1.task_id as note1_task_id, n2.task_id as note2_task_id,
                   n1.creation_date as note1_creation_date, n2.creation_date as note2_creation_date,
                   t1.title as task1_title, t2.title as task2_title
            FROM note_links nl
            JOIN notes n1 ON (nl.note1_id = n1.id)
            JOIN notes n2 ON (nl.note2_id = n2.id)
            LEFT JOIN tasks t1 ON (n1.task_id = t1.id)
            LEFT JOIN tasks t2 ON (n2.task_id = t2.id)
            WHERE nl.note1_id = ? OR nl.note2_id = ?
        """, (note_id, note_id)).fetchall()
        
        # Print linked notes in consistent format
        if linked_notes:
            print(Fore.CYAN + f"\nLinked notes:" + Style.RESET_ALL)
            for link in linked_notes:
                # Determine which note is the other one (not the one we're viewing)
                if link[0] == note_id:  # note1_id is the current note
                    other_note_id = link[1]
                    other_note_text = link[3]  # note2_text
                    other_task_id = link[5]   # note2_task_id
                    other_creation_date = link[7] # note2_creation_date
                    other_task_title = link[9] # task2_title
                else:  # note2_id is the current note
                    other_note_id = link[0]
                    other_note_text = link[2]  # note1_text
                    other_task_id = link[4]   # note1_task_id
                    other_creation_date = link[6] # note1_creation_date
                    other_task_title = link[8] # task1_title
                
                # Format the linked note consistently
                if other_task_id and other_task_title:
                    print(Fore.CYAN + f"  - {other_note_text} (id:{other_note_id}) ({other_creation_date}) (for task: {other_task_id}. {other_task_title})" + Style.RESET_ALL)
                else:
                    print(Fore.CYAN + f"  - {other_note_text} (id:{other_note_id}) ({other_creation_date})" + Style.RESET_ALL)
        else:
            print(Fore.CYAN + f"\nNo linked notes found." + Style.RESET_ALL)

def show_completed_tasks():
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute("""
            SELECT id, title, status, creation_date, due_date, completion_date, recur
            FROM tasks 
            WHERE status = 'done' AND completion_date IS NOT NULL
            ORDER BY completion_date ASC, id ASC
        """).fetchall()
        
        # Get all notes for tasks that will be displayed
        if tasks:
            task_ids = [str(task[0]) for task in tasks]
            notes_query = """
                SELECT id, text, creation_date, task_id 
                FROM notes 
                WHERE task_id IN ({})
                ORDER BY creation_date ASC, id ASC
            """.format(",".join("?" * len(task_ids)))
            notes = conn.execute(notes_query, task_ids).fetchall()
        else:
            notes = []

    # Create a mapping of task_id to list of notes for that task
    task_notes = defaultdict(list)
    for note in notes:
        task_notes[note[3]].append(note)  # note[3] is task_id
    
    # Group tasks by completion date
    grouped = defaultdict(list)
    for t in tasks:
        completion_date = t[5]  # completion_date
        grouped[completion_date].append(t)
    
    # Display tasks grouped by completion date
    for completion_date in sorted(grouped.keys()):
        print()
        print(format_date_with_day(completion_date))
        for task in grouped[completion_date]:
            print("\t" + format_task(task))
            # Show notes for this task if any exist
            task_id = task[0]  # task[0] is task id
            if task_id in task_notes:
                for note in task_notes[task_id]:
                    print(format_note(note, indent="\t\t"))  # 6 spaces for indentation


def show_tasks_by_status():
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute("""
            SELECT id, title, status, creation_date, due_date, completion_date, recur
            FROM tasks 
            WHERE status != 'done'
            ORDER BY 
                CASE status 
                    WHEN 'todo' THEN 1
                    WHEN 'doing' THEN 2
                    WHEN 'waiting' THEN 3
                    ELSE 4
                END,
                due_date ASC, id ASC
        """).fetchall()
        
        # Get all notes for tasks that will be displayed
        if tasks:
            task_ids = [str(task[0]) for task in tasks]
            notes_query = """
                SELECT id, text, creation_date, task_id 
                FROM notes 
                WHERE task_id IN ({})
                ORDER BY creation_date ASC, id ASC
            """.format(",".join("?" * len(task_ids)))
            notes = conn.execute(notes_query, task_ids).fetchall()
        else:
            notes = []

    # Create a mapping of task_id to list of notes for that task
    task_notes = defaultdict(list)
    for note in notes:
        task_notes[note[3]].append(note)  # note[3] is task_id

    # Group tasks by status
    grouped = defaultdict(list)
    for t in tasks:
        grouped[t[2]].append(t)  # t[2] is status

    # Display tasks grouped by status in the order: Todo, Doing, Waiting
    status_order = ['todo', 'doing', 'waiting']
    status_labels = {'todo': 'Todo', 'doing': 'Doing', 'waiting': 'Waiting'}
    
    for status in status_order:
        if status in grouped and grouped[status]:
            print(f"\n{status_labels[status]}")
            for task in grouped[status]:
                print("\t" + format_task(task))
                # Show notes for this task if any exist
                task_id = task[0]  # task[0] is task id
                if task_id in task_notes:
                    for note in task_notes[task_id]:
                        print(format_note(note, indent="\t\t"))  # 6 spaces for indentation


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
        show_due()
    elif cmd in ["page", "p"]:
        show_journal()
    elif cmd in ["task", "t"] and rest:  # Handle task commands
        # Check if it's a task edit command: jrnl task <id> edit [text:<text>] [due:<text>] [note:<text>] [recur:<Nd|Nw|Nm|Ny>]
        if len(rest) >= 2 and rest[0].isdigit() and rest[1] == "edit":
            task_id = int(rest[0])
            
            # Parse additional arguments for editing (format: key:value)
            new_title = None
            new_due = None
            note_text = None
            recur_pattern = None
            
            # Process each argument after "edit"
            for i in range(2, len(rest)):
                arg = rest[i]
                
                if arg.startswith("text:"):
                    # Extract text after "text:"
                    new_title = arg[5:]  # Remove "text:" prefix
                
                elif arg.startswith("due:"):
                    # Parse due date after "due:"
                    due_text = arg[4:]  # Remove "due:" prefix
                    new_due = parse_due(due_text)
                
                elif arg.startswith("note:"):
                    # Extract note text after "note:"
                    note_text = arg[5:]  # Remove "note:" prefix
                
                elif arg.startswith("recur:"):
                    # Extract recur pattern after "recur:"
                    recur_pattern = arg[6:]  # Remove "recur:" prefix
            
            # Perform operations in order
            if new_title:
                edit_task(task_id, new_title)
            
            if new_due:
                with sqlite3.connect(DB_FILE) as conn:
                    conn.execute(
                        "UPDATE tasks SET due_date=? WHERE id=?",
                        (new_due.strftime("%Y-%m-%d"), task_id)
                    )
                    print(f"Updated due date for task {task_id} to {new_due.strftime('%Y-%m-%d')}")
            
            if note_text:
                # Add note to the task
                add_note([task_id], note_text)
                
            if recur_pattern:
                # Validate and set recur pattern
                if set_task_recur([task_id], recur_pattern):
                    print(f"Set recur pattern '{recur_pattern}' for task {task_id}")
        else:
            # Otherwise, treat as adding tasks (original functionality)
            add_task(" ".join(rest).split(","))
    elif cmd in ["note", "n"] and rest:  # Handle note commands with arguments
        # Check if first argument is a single digit/number (for note lookup)
        if len(rest) == 1 and rest[0].isdigit():
            # View specific note with links
            note_id = int(rest[0])
            show_note_details(note_id)
        elif len(rest) >= 2 and rest[0].isdigit():
            # Handle consolidated note edit command: jrnl note <id> edit [text:<text>] [link:<id>[,<id>,...]] [unlink:<id>[,<id>,...]]
            note_id = int(rest[0])
            if rest[1] == "edit":
                # Parse additional arguments for editing (format: key:value)
                new_text = None
                link_ids = []
                unlink_ids = []
                
                # Process each argument after "edit"
                for i in range(2, len(rest)):
                    arg = rest[i]
                    
                    if arg.startswith("text:"):
                        # Extract text after "text:"
                        new_text = arg[5:]  # Remove "text:" prefix
                    
                    elif arg.startswith("link:"):
                        # Parse comma-separated list of IDs to link
                        ids_str = arg[5:]  # Remove "link:" prefix
                        ids = ids_str.split(",")
                        link_ids = [int(id_str) for id_str in ids if id_str.isdigit()]
                    
                    elif arg.startswith("unlink:"):
                        # Parse comma-separated list of IDs to unlink
                        ids_str = arg[7:]  # Remove "unlink:" prefix
                        ids = ids_str.split(",")
                        unlink_ids = [int(id_str) for id_str in ids if id_str.isdigit()]
                
                # Perform operations in order: edit text, then unlink, then link
                if new_text:
                    edit_note(note_id, new_text)
                
                for unlink_id in unlink_ids:
                    unlink_notes(note_id, unlink_id)
                
                for link_id in link_ids:
                    link_notes(note_id, link_id)
            else:
                # Handle legacy format (if needed) or error
                print(f"Error: Unknown command 'jrnl note {rest[0]} {rest[1]}'. Use 'edit' for editing notes.")
        elif len(rest) >= 3 and rest[0] in ["link", "unlink"] and all(arg.isdigit() for arg in rest[1:3]):
            # The old link/unlink commands have been replaced with the consolidated command
            print("Error: The 'link' and 'unlink' commands have been removed. Use 'jrnl note <id> edit link:<id>[,<id>,...]' and 'jrnl note <id> edit unlink:<id>[,<id>,...]' instead.")
        elif all(c.isdigit() or c == "," for c in rest[0]):
            # Add note to tasks - this functionality has been replaced with the consolidated command
            print("Error: Adding notes to tasks using 'jrnl note <task_id> <text>' has been removed. Use 'jrnl task <id> edit -note <text>' instead.")
        else:
            # Add standalone note
            text = " ".join(rest)
            if text:
                add_note([], text)
            else:
                print("Error: Please provide note text")
    elif cmd == "edit":
        if rest and len(rest) >= 2:
            item_identifier = rest[0]
            new_text = " ".join(rest[1:])
            
            # Check if the identifier starts with 't' (task)
            if item_identifier.startswith("t") and item_identifier[1:].isdigit():
                print("Error: The 'edit' command for tasks has been removed. Use 'jrnl task <id> edit -text <new text>' instead.")
            else:
                print("Error: The 'edit' command has been removed for tasks. For task editing, use 'jrnl task <id> edit -text <new text>'. For note editing, use 'jrnl note <id> edit text:<new text>'.")
        else:
            print("Error: Please use the consolidated commands: 'jrnl task <id> edit' or 'jrnl note <id> edit'")
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
    elif cmd in ["done", "x"] and rest:
        # Parse task IDs and note text
        ids = []
        note_text = ""
        
        # Look for task IDs in the arguments (numbers and commas)
        for i, arg in enumerate(rest):
            if all(c.isdigit() or c == "," for c in arg):
                ids.extend([int(i) for i in arg.split(",")])
            else:
                # Everything after the task IDs is considered note text
                note_text = " ".join(rest[i:])
                break
        
        if not ids:
            print("Error: Please provide valid task IDs and note text")
            return
            
        if not note_text:
            print("Error: Please provide a note for completing the task(s)")
            return
        
        # Update task status and add the note
        update_task_status(ids, "done", note_text)
    elif cmd in ["status", "s"]:
        show_tasks_by_status()
    elif cmd in ["due", "d"]:
        if rest and all(c.isdigit() or c == "," for c in rest[0]):
            # The 'due' command for changing due dates has been replaced with the consolidated command
            print("Error: The 'due' command for changing due dates has been removed. Use 'jrnl task <id> edit -due <date>' instead.")
        else:
            show_due()
    elif cmd == "recur":
        # The 'recur' command has been replaced with the consolidated command
        print("Error: The 'recur' command has been removed. Use 'jrnl task <id> edit -recur <Nd|Nw|Nm|Ny>' instead.")
    elif cmd in ["waiting", "start", "restart"]:  # Removed "done" from here
        if rest:
            ids = []
            for arg in rest:
                if all(c.isdigit() or c == "," for c in arg):
                    ids.extend([int(i) for i in arg.split(",")])
                else:
                    print(f"Error: Invalid task ID '{arg}'")
                    return
            if ids:
                # "restart" should set status back to "todo"
                # "start" should set status to "doing"
                status = "todo" if cmd == "restart" else ("doing" if cmd == "start" else cmd)
                update_task_status(ids, status)
            else:
                print("Error: Please provide valid task IDs")
        else:
            print("Error: Please provide task IDs")
    elif cmd in ["find", "f"]:
        if rest:
            search_text = " ".join(rest)
            grouped, tasks, notes = search_tasks_and_notes(search_text)
            display_search_results(grouped)
        else:
            print("Error: Please provide search text")
    elif cmd in ["help", "h"]:
        print("""jrnl - Command Line Journal and Task Manager

USAGE:
    jrnl [command] [arguments...]

COMMANDS:
    jrnl                    Show tasks grouped by due date (default view) (Overdue / Due Today / This Week / This Month / Future / No Due Date)
    jrnl page|p        Show journal (grouped by creation date)
    jrnl task|t <text>[,<text>...]     Add tasks
    jrnl task|t <id> edit [-text <text>] [-due <text>] [-note <text>] [-recur <Nd|Nw|Nm|Ny>]  Edit task with optional parameters
    jrnl note|n        Show all notes
    jrnl note|n <text>          Add standalone note (to add note to task, use 'jrnl task <id> edit -note <text>')
    jrnl note|n <id>          Show specific note with linked notes
    jrnl note|n <id> edit [text:<text>] [link:<id>[,<id>,...]] [unlink:<id>[,<id>,...]]  Edit note with optional text, linking, unlinking
    jrnl task|t        Show all unfinished tasks
    jrnl done               Show all completed tasks grouped by completion date
    jrnl status|s      Show tasks grouped by status (Todo, Doing, Waiting)
    jrnl due|d                Show tasks grouped by due date (Overdue / Due Today / This Week / This Month / Future / No Due Date)
    jrnl restart <id>[,<id>...]   Mark tasks as not done
    jrnl start <id>[,<id>...]     Mark tasks as in progress
    jrnl waiting <id>[,<id>...]   Mark tasks as waiting
    jrnl done|x <id>[,<id>...] <note text>      Mark tasks as done with a completion note
    jrnl find|f <text>        Search for tasks and notes containing text
    jrnl rm t<id>[,n<id>...]      Delete tasks (t) or notes (n)
    jrnl help|h        Show this help message
""")

if __name__ == "__main__":
    main()
