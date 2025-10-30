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
            recur TEXT,
            pid INTEGER
        )""")
        
        # Check if recur column exists, and add it if it doesn't
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN recur TEXT")
        except sqlite3.OperationalError:
            # Column already exists, which is fine
            pass
        
        # Check if pid column exists, and add it if it doesn't
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN pid INTEGER")
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

def format_task(task, prefix=""):
    # task now has 8 elements: id, title, status, creation_date, due_date, completion_date, recur, pid
    tid, title, status, creation_date, due_date, completion_date, recur, pid = task
    checkbox = "[x]" if status == "done" else "[ ]"

    # Color based on status
    if status == "doing":
        text = prefix + Back.YELLOW + Fore.BLACK + f"{checkbox} {title} (id:{tid})" + Style.RESET_ALL
    elif status == "waiting":
        text = prefix + Back.LIGHTBLACK_EX + Fore.WHITE + f"{checkbox} {title} (id:{tid})" + Style.RESET_ALL
    elif status == "done":
        text = prefix + Fore.GREEN + f"{checkbox} {title} (id:{tid})" + Style.RESET_ALL
    else:  # todo
        text = prefix + f"{checkbox} {title}  (id:{tid})"

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

def build_task_tree(tasks_list):
    """
    Build a tree structure from a list of tasks.
    Returns a dictionary with root tasks as keys and their children as values.
    """
    # Create a dictionary to store tasks by ID for easy lookup
    task_dict = {task[0]: task for task in tasks_list}  # task[0] is id
    
    # Create a dictionary to store children for each task
    children = {task[0]: [] for task in tasks_list}  # task[0] is id
    
    # Build the tree structure
    root_tasks = []
    for task in tasks_list:
        task_id = task[0]  # task[0] is id
        parent_id = task[7]  # task[7] is pid
        
        if parent_id is None or parent_id == 0:
            # This is a root task
            root_tasks.append(task)
        else:
            # This is a child task, add it to its parent's children
            if parent_id in children:
                children[parent_id].append(task)
    
    return root_tasks, children, task_dict

def print_task_tree(task, children, task_dict, is_last=True, prefix="", is_root=True):
    """
    Recursively print a task and its children in a tree structure using ASCII characters.
    """
    task_id = task[0]  # task[0] is id
    
    # For root tasks (at the very beginning), we don't use tree characters
    if is_root:
        prefix_str = "\t"  # Regular indent for root tasks
        print(format_task(task, prefix_str))
    else:
        # For child tasks, use tree characters
        if is_last:
            prefix_str = prefix + "└─ "
        else:
            prefix_str = prefix + "├─ "
        print(format_task(task, prefix_str))
    
    # For notes under this task, we need to determine the appropriate prefix
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute(
            "SELECT id,text,creation_date,task_id FROM notes WHERE task_id=?", 
            (task[0],)  # task[0] is id
        ).fetchall()
        
    # Determine note prefix based on whether this is the last child
    if is_root:
        note_prefix = "\t\t"
    else:
        note_prefix = prefix + ("    " if is_last else "│   ")
        
    for i, note in enumerate(notes):
        is_last_note = (i == len(notes) - 1) and (task_id not in children or len(children[task_id]) == 0)
        note_prefix_for_note = note_prefix + ("└─ " if is_last_note else "├─ ")
        print(format_note(note, note_prefix_for_note))
    
    # Recursively print children with appropriate prefixes
    if task_id in children and children[task_id]:
        child_count = len(children[task_id])
        for i, child in enumerate(children[task_id]):
            is_last_child = (i == child_count - 1)
            if is_root:
                child_prefix = "\t"  # For root level, children will start with tab
            else:
                child_prefix = prefix + ("    " if is_last else "│   ")
            print_task_tree(child, children, task_dict, is_last_child, child_prefix, is_root=False)

def build_task_tree(tasks_list):
    """
    Build a tree structure from a list of tasks.
    Returns a dictionary with root tasks as keys and their children as values.
    """
    # Create a dictionary to store tasks by ID for easy lookup
    task_dict = {task[0]: task for task in tasks_list}  # task[0] is id
    
    # Create a dictionary to store children for each task
    children = {task[0]: [] for task in tasks_list}  # task[0] is id
    
    # Build the tree structure
    root_tasks = []
    for task in tasks_list:
        task_id = task[0]  # task[0] is id
        parent_id = task[7]  # task[7] is pid
        
        if parent_id is None or parent_id == 0:
            # This is a root task
            root_tasks.append(task)
        else:
            # This is a child task, add it to its parent's children
            if parent_id in children:
                children[parent_id].append(task)
    
    return root_tasks, children, task_dict

def print_task_tree(task, children, task_dict, is_last=True, prefix="", is_root=True):
    """
    Recursively print a task and its children in a tree structure using ASCII characters.
    """
    task_id = task[0]  # task[0] is id
    
    # For root tasks (at the very beginning), we don't use tree characters
    if is_root:
        prefix_str = "\t"  # Regular indent for root tasks
        print(format_task(task, prefix_str))
    else:
        # For child tasks, use tree characters
        if is_last:
            prefix_str = prefix + " └─ "
        else:
            prefix_str = prefix + " ├─ "
        print(format_task(task, prefix_str))
    
    # For notes under this task, we need to determine the appropriate prefix
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute(
            "SELECT id,text,creation_date,task_id FROM notes WHERE task_id=?", 
            (task[0],)  # task[0] is id
        ).fetchall()
        
    # Determine note prefix based on whether this is the last child
    if is_root:
        note_prefix = "\t    "
    else:
        note_prefix = prefix + ("    " if is_last else "│   ")
        
    for i, note in enumerate(notes):
        is_last_note = (i == len(notes) - 1) and (task_id not in children or len(children[task_id]) == 0)
        note_prefix_for_note = note_prefix + ("└─ " if is_last_note else "├─ ")
        print(format_note(note, note_prefix_for_note))
    
    # Recursively print children with appropriate prefixes
    if task_id in children and children[task_id]:
        child_count = len(children[task_id])
        for i, child in enumerate(children[task_id]):
            is_last_child = (i == child_count - 1)
            if is_root:
                child_prefix = "\t"  # For root level, children will start with tab
            else:
                child_prefix = prefix + ("    " if is_last else " │  ")
            print_task_tree(child, children, task_dict, is_last_child, child_prefix, is_root=False)

def format_note(note, indent="\t"):
    nid, text, creation_date, task_id = note
    return Fore.YELLOW + indent + f"{text} (id:{nid}) ({creation_date})" + Style.RESET_ALL

def search_tasks_and_notes(search_text):
    """Search for tasks and notes containing the search text (supports wildcards: * and ?)"""
    # Convert user-friendly wildcards to SQL LIKE patterns
    # * -> % (matches any sequence of characters)
    # ? -> _ (matches any single character)
    sql_search_text = search_text.replace("*", "%").replace("?", "_")
    
    with sqlite3.connect(DB_FILE) as conn:
        # Search in tasks (title column)
        tasks = conn.execute(
            """
            SELECT id,title,status,creation_date,due_date,completion_date,recur,pid 
            FROM tasks 
            WHERE title LIKE ? 
            ORDER BY creation_date ASC,id ASC
            """,
            (f"%{sql_search_text}%",)
        ).fetchall()

        # Search in notes (text column)
        notes = conn.execute(
            """
            SELECT id,text,creation_date,task_id 
            FROM notes 
            WHERE text LIKE ? 
            ORDER BY creation_date ASC,id ASC
            """,
            (f"%{sql_search_text}%",)
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
                SELECT id,title,status,creation_date,due_date,completion_date,recur,pid 
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
            "SELECT id,title,status,creation_date,due_date,completion_date,recur,pid FROM tasks ORDER BY creation_date ASC,id ASC"
        ).fetchall()
        all_notes = conn.execute(
            "SELECT id,text,creation_date,task_id FROM notes ORDER BY creation_date ASC,id ASC"
        ).fetchall()

    for day in sorted(grouped.keys()):
        tasks_for_day = grouped[day]["tasks"]
        notes_for_day = grouped[day]["notes"]
        
        if tasks_for_day or notes_for_day:
            print()
            print(format_date_with_day(day))
            
            # Build and print task tree for this day
            if tasks_for_day:
                root_tasks, children, task_dict = build_task_tree(tasks_for_day)
                for i, root_task in enumerate(root_tasks):
                    is_last = (i == len(root_tasks) - 1)
                    print_task_tree(root_task, children, task_dict, is_last, "", is_root=True)
            
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
            # Check if trying to mark a parent task as done when children are not completed
            if status == "done":
                # Check if this task has any children that are not done
                children = conn.execute(
                    "SELECT id, status FROM tasks WHERE pid = ? AND status != 'done'", (tid,)
                ).fetchall()
                
                if children:
                    print(f"Error: Cannot mark task {tid} as done because it has {len(children)} incomplete child task(s)")
                    continue  # Skip updating this task
            
            # If marking as done, check if it's a recurring task
            if status == "done":
                # Get the task's recur pattern
                task = conn.execute(
                    "SELECT id, title, due_date, recur FROM tasks WHERE id=?", (tid,)
                ).fetchone()
                today = datetime.now().date().strftime("%Y-%m-%d")                
                if task and task[3]:  # If task has a recur pattern (task[3] is recur)
                    # Create a new task with the same details but new due date

                    old_task_id, title, due_date, recur = task
                    new_due_date = calculate_next_due_date(today, recur)
                    
                    # Insert the new recurring parent task
                    new_parent_id = conn.execute(
                        "INSERT INTO tasks (title,status,creation_date,due_date,recur) VALUES (?,?,?,?,?)",
                        (title, "todo", today, new_due_date, recur)
                    ).lastrowid
                    print(f"Created recurring task for '{title}'")
                    
                    # Recreate child tasks for the new parent task
                    child_tasks = conn.execute(
                        "SELECT title, status, creation_date, due_date, completion_date, recur FROM tasks WHERE pid = ?",
                        (old_task_id,)
                    ).fetchall()
                    
                    for child_task in child_tasks:
                        child_title, child_status, child_creation_date, child_due_date, child_completion_date, child_recur = child_task
                        # Insert the child task with the new parent ID
                        conn.execute(
                            "INSERT INTO tasks (title, status, creation_date, due_date, completion_date, recur, pid) VALUES (?,?,?,?,?,?,?)",
                            (child_title, child_status, today, child_due_date, child_completion_date, child_recur, new_parent_id)
                        )
                    print(f"  Recreated {len(child_tasks)} child task(s) for the recurring task")
                
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
    elif status == "done" and task_ids:
        print(f"No tasks were updated to done (likely due to incomplete child tasks)")

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
    """Delete tasks from the database along with their child tasks recursively"""
    if not task_ids:
        print("No tasks to delete")
        return
    
    # Get all tasks that need to be deleted (including children)
    all_tasks_to_delete = set(task_ids)
    
    with sqlite3.connect(DB_FILE) as conn:
        # Find all child tasks recursively using a loop
        current_tasks = list(task_ids)
        while current_tasks:
            # Get children of current tasks
            placeholders = ",".join("?" * len(current_tasks))
            children = conn.execute(
                f"SELECT id FROM tasks WHERE pid IN ({placeholders})",
                current_tasks
            ).fetchall()
            
            # Add children to the deletion list
            current_tasks = [child[0] for child in children]
            all_tasks_to_delete.update(current_tasks)
    
    # Ask for confirmation before deletion
    total_tasks = len(all_tasks_to_delete)
    if total_tasks == 0:
        print("No tasks to delete")
        return
    
    print(f"Warning: You are about to delete {total_tasks} task(s) (including children). This action cannot be undone.")
    confirmation = input("Type 'yes' to confirm deletion: ").strip().lower()
    
    if confirmation != 'yes':
        print("Deletion cancelled.")
        return
    
    # Now delete all tasks and their associated notes
    deleted_count = 0
    with sqlite3.connect(DB_FILE) as conn:
        for tid in all_tasks_to_delete:
            # Delete associated notes
            conn.execute("DELETE FROM notes WHERE task_id=?", (tid,))
            # Delete the task
            cursor = conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
            if cursor.rowcount > 0:
                deleted_count += 1
    
    if deleted_count > 0:
        print(f"Deleted {deleted_count} task(s) (including children)")
    else:
        print("No tasks were deleted")

def delete_note(note_ids):
    """Delete notes from the database"""
    if not note_ids:
        print("No notes to delete")
        return
    
    # Ask for confirmation before deletion
    total_notes = len(note_ids)
    print(f"Warning: You are about to delete {total_notes} note(s). This action cannot be undone.")
    confirmation = input("Type 'yes' to confirm deletion: ").strip().lower()
    
    if confirmation != 'yes':
        print("Deletion cancelled.")
        return
    
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
        # get tasks with pid column
        tasks = conn.execute(
            "SELECT id,title,status,creation_date,due_date,completion_date,recur,pid FROM tasks ORDER BY creation_date ASC,id ASC"
        ).fetchall()

        # get notes
        notes = conn.execute(
            "SELECT id,text,creation_date,task_id FROM notes ORDER BY creation_date ASC,id ASC"
        ).fetchall()

    # group tasks/notes by creation_date
    grouped = defaultdict(lambda: {"tasks": [], "notes": []})
    for t in tasks:
        grouped[t[3]]["tasks"].append(t)  # t[3] is creation_date
    for n in notes:
        if n[3]:  # attached to task
            # handled under task display
            pass
        else:
            grouped[n[2]]["notes"].append(n)

    for day in sorted(grouped.keys()):
        print()
        print(format_date_with_day(day))
        
        # Build and print task tree for this day
        day_tasks = grouped[day]["tasks"]
        if day_tasks:
            root_tasks, children, task_dict = build_task_tree(day_tasks)
            for i, root_task in enumerate(root_tasks):
                is_last = (i == len(root_tasks) - 1)
                print_task_tree(root_task, children, task_dict, is_last, "", is_root=True)
        
        # show standalone notes
        for n in grouped[day]["notes"]:
            if not n[3]:
                print(format_note(n, indent="\t"))

def show_due():
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute(
            "SELECT id,title,status,creation_date,due_date,completion_date,recur,pid FROM tasks WHERE status != 'done' ORDER BY due_date ASC"
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
    tomorrow = today + timedelta(days=1)
    # Calculate the end of this week (Sunday) and end of this month
    end_of_week = today + timedelta(days=(6 - today.weekday()))
    # For end of month, we get the last day of the current month
    if today.month == 12:
        end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    
    # Updated to include pid in bucketing
    buckets = {"Overdue": [], "Due Today": [], "Due Tomorrow": [], "This Week": [], "This Month": [], "Future": [], "No Due Date": []}

    for t in tasks:
        # t[4] is due_date
        if t[4]:  # Check if due date exists
            due = datetime.strptime(t[4], "%Y-%m-%d").date()
            if due < today:  # No need to check status since we filtered in query
                buckets["Overdue"].append(t)
            elif due == today:
                buckets["Due Today"].append(t)
            elif due == tomorrow:
                buckets["Due Tomorrow"].append(t)
            elif due <= end_of_week:
                buckets["This Week"].append(t)
            elif due <= end_of_month:
                buckets["This Month"].append(t)
            else:
                buckets["Future"].append(t)
        else:
            buckets["No Due Date"].append(t)

    # Updated order: Future, This Month, This Week, Due Tomorrow, Due Today, Overdue, No Due Date
    for label in ["Future", "This Month", "This Week", "Due Tomorrow", "Due Today", "Overdue", "No Due Date"]:
        if buckets[label]:
            print(f"\n{label}")
            # Build and print task tree for this bucket
            bucket_tasks = buckets[label]
            root_tasks, children, task_dict = build_task_tree(bucket_tasks)
            for i, root_task in enumerate(root_tasks):
                is_last = (i == len(root_tasks) - 1)
                print_task_tree(root_task, children, task_dict, is_last, "", is_root=True)

def show_task():
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute(
            "SELECT id,title,status,creation_date,due_date,completion_date,recur,pid FROM tasks WHERE status != 'done' ORDER BY creation_date ASC"
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
        
        # Build and print task tree for this day
        day_tasks = grouped[day]
        root_tasks, children, task_dict = build_task_tree(day_tasks)
        for i, root_task in enumerate(root_tasks):
            is_last = (i == len(root_tasks) - 1)
            print_task_tree(root_task, children, task_dict, is_last, "", is_root=True)

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
            SELECT id, title, status, creation_date, due_date, completion_date, recur, pid
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

    # Group tasks by completion date
    grouped = defaultdict(list)
    for t in tasks:
        completion_date = t[5]  # completion_date
        grouped[completion_date].append(t)
    
    # Display tasks grouped by completion date
    for completion_date in sorted(grouped.keys()):
        print()
        print(format_date_with_day(completion_date))
        
        # Build and print task tree for this completion date
        date_tasks = grouped[completion_date]
        root_tasks, children, task_dict = build_task_tree(date_tasks)
        for i, root_task in enumerate(root_tasks):
            is_last = (i == len(root_tasks) - 1)
            print_task_tree(root_task, children, task_dict, is_last, "", is_root=True)


def show_tasks_by_status():
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute("""
            SELECT id, title, status, creation_date, due_date, completion_date, recur, pid
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
            
            # Build and print task tree for this status
            status_tasks = grouped[status]
            root_tasks, children, task_dict = build_task_tree(status_tasks)
            for i, root_task in enumerate(root_tasks):
                is_last = (i == len(root_tasks) - 1)
                print_task_tree(root_task, children, task_dict, is_last, "", is_root=True)


# --- CLI Parser ---

def main():
    init_db()

    # Parse command line arguments manually to avoid argparse interpreting flags as its own arguments
    import sys
    if len(sys.argv) == 1:
        cmd = None
        rest = []
    elif len(sys.argv) == 2:
        cmd = sys.argv[1]
        rest = []
    else:
        cmd = sys.argv[1]
        rest = sys.argv[2:]

    if cmd is None:
        show_due()
    elif cmd == "new" and len(rest) >= 2:  # Handle new consolidated commands
        sub_cmd = rest[0]  # "note" or "task"
        cmd_args = rest[1:]
        
        if sub_cmd == "note":  # Handle "jrnl new note <text> [-link <id>[,<id>,...]]"
            # Find the note text (everything before the first option flag)
            note_text = []
            link_ids = []
            i = 0
            while i < len(cmd_args):
                if cmd_args[i].startswith("-"):
                    if cmd_args[i] == "-link" and i + 1 < len(cmd_args):
                        # Parse comma-separated list of IDs to link
                        ids_str = cmd_args[i + 1]
                        ids = ids_str.split(",")
                        link_ids = [int(id_str) for id_str in ids if id_str.isdigit()]
                        i += 2
                    else:
                        # Unknown option
                        i += 1
                else:
                    note_text.append(cmd_args[i])
                    i += 1
            
            if not note_text:
                print("Error: Please provide note text")
                return
            
            text = " ".join(note_text)
            if text:
                # Add the note first
                add_note([], text)
                
                # Then create links if specified
                if link_ids:
                    # Get the ID of the newly added note
                    with sqlite3.connect(DB_FILE) as conn:
                        new_note_id = conn.execute("SELECT id FROM notes WHERE text=? ORDER BY id DESC LIMIT 1", (text,)).fetchone()
                    
                    if new_note_id:
                        note_id = new_note_id[0]
                        for link_id in link_ids:
                            link_notes(note_id, link_id)
            else:
                print("Error: Please provide note text")
        
        elif sub_cmd == "task":  # Handle "jrnl new task [@<pid>] <text> [-due <YYYY-MM-DD|today|tomorrow|eow|eom|eoy>] [-recur <Nd|Nw|Nm|Ny>]"
            # Check if the first argument is a parent task ID in the format @<number>
            parent_id = None
            start_idx = 0
            
            if cmd_args and cmd_args[0].startswith("@") and cmd_args[0][1:].isdigit():
                parent_id = int(cmd_args[0][1:])  # Remove @ and convert to int
                start_idx = 1  # Skip the first argument as it's the parent ID
            
            # Find the task text (everything before the first option flag)
            task_text = []
            due_date = None
            recur_pattern = None
            i = start_idx
            while i < len(cmd_args):
                if cmd_args[i].startswith("-"):
                    if cmd_args[i] == "-due" and i + 1 < len(cmd_args):
                        due_kw = cmd_args[i + 1]  # No need to remove @ as it's handled separately now
                        due_date = parse_due(due_kw)
                        i += 2
                    elif cmd_args[i] == "-recur" and i + 1 < len(cmd_args):
                        recur_pattern = cmd_args[i + 1]
                        # Validate the recurrence pattern
                        if not set_task_recur([0], recur_pattern):  # Use 0 as placeholder, we'll update later
                            print("Error: Invalid recurrence pattern. Use format: <number><unit> (e.g., 4w, 2d, 1m, 1y)")
                            return
                        i += 2
                    else:
                        # Unknown option
                        i += 1
                else:
                    task_text.append(cmd_args[i])
                    i += 1
            
            if not task_text:
                print("Error: Please provide task text")
                return
            
            text = " ".join(task_text)
            if text:
                # Check if parent_id exists if provided
                if parent_id is not None:
                    with sqlite3.connect(DB_FILE) as conn:
                        cursor = conn.execute("SELECT id FROM tasks WHERE id = ?", (parent_id,))
                        if not cursor.fetchone():
                            print(f"Error: Parent task with ID {parent_id} does not exist")
                            return
                
                # Add the task with due date if specified
                if due_date:
                    # Create a temporary task with due date
                    today = datetime.now().date().strftime("%Y-%m-%d")
                    with sqlite3.connect(DB_FILE) as conn:
                        task_id = conn.execute(
                            "INSERT INTO tasks (title,status,creation_date,due_date,recur,pid) VALUES (?,?,?,?,?,?)",
                            (text, "todo", today, due_date.strftime("%Y-%m-%d"), recur_pattern, parent_id)
                        ).lastrowid
                        print(f"Added 1 task(s)")
                else:
                    # Add task without due date (default to today)
                    if recur_pattern:  # Need to call add_task with proper due date handling
                        # Use today as default due date when recurrence is specified but due date isn't
                        today = datetime.now().date()
                        formatted_today = today.strftime("%Y-%m-%d")
                        with sqlite3.connect(DB_FILE) as conn:
                            task_id = conn.execute(
                                "INSERT INTO tasks (title,status,creation_date,due_date,recur,pid) VALUES (?,?,?,?,?,?)",
                                (text, "todo", formatted_today, formatted_today, recur_pattern, parent_id)
                            ).lastrowid
                        print(f"Added 1 task(s)")
                    else:
                        # Call original add_task function for simple tasks but with parent ID
                        today = datetime.now().date().strftime("%Y-%m-%d")
                        with sqlite3.connect(DB_FILE) as conn:
                            conn.execute(
                                "INSERT INTO tasks (title,status,creation_date,due_date,pid) VALUES (?,?,?,?,?)",
                                (text, "todo", today, today, parent_id)
                            )
                        print(f"Added 1 task(s)")
            else:
                print("Error: Please provide task text")
    
    elif cmd in ["page", "p"]:
        # The old 'jrnl page|p' command has been removed
        print("Error: The 'jrnl page|p' command has been removed. Use 'jrnl list page' instead.")
    elif cmd in ["task", "t"] and rest:  # Handle task commands
        # The old task command (jrnl task <text>) has been removed
        print("Error: The 'jrnl task <text>' command has been removed. Use 'jrnl new task <text> [-due @<date>] [-recur <Nd|Nw|Nm|Ny>]' instead.")
    elif cmd in ["note", "n"] and rest:  # Handle note commands with arguments
        # Check if first argument is a single digit/number (for note lookup)
        if len(rest) == 1 and rest[0].isdigit():
            # The old note command (jrnl note <id>) has been removed
            print("Error: The 'jrnl note <id>' command has been removed. Use 'jrnl show note <id>' instead.")
        else:
            # The old note command (jrnl note <text>) and edit command (jrnl note <id> edit) have been removed
            print("Error: The 'jrnl note <text>' and 'jrnl note <id> edit' commands have been removed. Use 'jrnl new note <text> [-link <id>[,<id>,...]]' for new notes or 'jrnl edit note <id> [-text <text>] [-link <id>[,<id>,...]] [-unlink <id>[,<id>,...]]' for editing.")
    elif cmd == "view" and len(rest) >= 2:
        # New consolidated command: jrnl view task <due|status|done>
        if rest[0] == "task" and rest[1] == "due":
            show_due()
        elif rest[0] == "task" and rest[1] == "status":
            show_tasks_by_status()
        elif rest[0] == "task" and rest[1] == "done":
            show_completed_tasks()
        else:
            print("Error: Invalid syntax. Use 'jrnl view task <due|status|done>'")
    elif cmd in ["start", "restart", "waiting"] and len(rest) >= 2 and rest[0] == "task":
        # New consolidated command: jrnl <start|restart|waiting> task <id>[,<id>,...]
        ids_str = rest[1]
        ids = [int(id_str) for id_str in ids_str.split(",") if id_str.isdigit()]
        
        if cmd == "start":
            update_task_status(ids, "doing")
        elif cmd == "restart":
            update_task_status(ids, "todo")
        elif cmd == "waiting":
            update_task_status(ids, "waiting")
    elif cmd == "done" and len(rest) >= 2 and rest[0] == "task":
        # New consolidated command: jrnl done task <id>[,<id>,...] [note text]
        ids_str = rest[1]
        ids = [int(id_str) for id_str in ids_str.split(",") if id_str.isdigit()]
        
        # Everything after the task IDs is considered note text (optional)
        note_text = " ".join(rest[2:]) if len(rest) > 2 else ""
        if not ids:
            print("Error: Please provide valid task IDs")
            return
        
        update_task_status(ids, "done", note_text)
    elif cmd == "show" and len(rest) >= 2 and rest[0] in ["note", "task"]:
        # New consolidated command: jrnl show <note|task> <id>
        item_type = rest[0]
        item_id = int(rest[1]) if rest[1].isdigit() else None
        
        if item_type == "note" and item_id is not None:
            show_note_details(item_id)
        elif item_type == "task" and item_id is not None:
            # For showing a specific task and its children
            with sqlite3.connect(DB_FILE) as conn:
                task = conn.execute(
                    "SELECT id,title,status,creation_date,due_date,completion_date,recur,pid FROM tasks WHERE id=?", 
                    (item_id,)
                ).fetchone()
                
            if task:
                # Get all related tasks to build the tree
                with sqlite3.connect(DB_FILE) as conn:
                    all_related_tasks = conn.execute(
                        """
                        WITH RECURSIVE task_tree AS (
                            -- Base case: the selected task
                            SELECT id, title, status, creation_date, due_date, completion_date, recur, pid
                            FROM tasks
                            WHERE id = ?
                            
                            UNION ALL
                            
                            -- Recursive case: child tasks
                            SELECT t.id, t.title, t.status, t.creation_date, t.due_date, t.completion_date, t.recur, t.pid
                            FROM tasks t
                            JOIN task_tree tt ON t.pid = tt.id
                        )
                        SELECT * FROM task_tree
                        ORDER BY id;
                        """, 
                        (item_id,)
                    ).fetchall()
                
                # Build and print the tree for this specific task and its children
                root_tasks, children, task_dict = build_task_tree(all_related_tasks)
                if root_tasks:
                    print_task_tree(root_tasks[0], children, task_dict, is_last=True, prefix="", is_root=True)  # No initial indent for top task
            else:
                print(f"Error: Task with ID {item_id} not found")
        else:
            print("Error: Invalid syntax. Use 'jrnl show <note|task> <id>'")
    elif cmd in ["task", "t"]:
        # The old 'jrnl task' command has been removed
        print("Error: The 'jrnl task' command has been removed. Use 'jrnl list task status' instead.")
    elif cmd in ["note", "n"]:
        # The old 'jrnl note' command has been removed
        print("Error: The 'jrnl note' command has been removed. Use 'jrnl list note' instead.")
    elif cmd == "edit" and len(rest) >= 2:
        # New consolidated edit syntax: jrnl edit <note|task> <id> [options]
        item_type = rest[0].lower()
        item_id = int(rest[1]) if rest[1].isdigit() else None
        
        if item_type not in ["note", "task"] or item_id is None:
            print("Error: Invalid syntax. Use 'jrnl edit note <id> [options]' or 'jrnl edit task <id> [options]'")
            return
        
        # Parse options
        options = rest[2:]
        if item_type == "note":
            # Handle note editing options
            new_text = None
            link_ids = []
            unlink_ids = []
            
            i = 0
            while i < len(options):
                if options[i] == "-text" and i + 1 < len(options):
                    new_text = options[i + 1]
                    i += 2
                elif options[i] == "-link" and i + 1 < len(options):
                    # Parse comma-separated list of IDs to link
                    ids_str = options[i + 1]
                    ids = ids_str.split(",")
                    link_ids = [int(id_str) for id_str in ids if id_str.isdigit()]
                    i += 2
                elif options[i] == "-unlink" and i + 1 < len(options):
                    # Parse comma-separated list of IDs to unlink
                    ids_str = options[i + 1]
                    ids = ids_str.split(",")
                    unlink_ids = [int(id_str) for id_str in ids if id_str.isdigit()]
                    i += 2
                else:
                    # Skip unknown option
                    i += 1
            
            # Perform operations in order: edit text, then unlink, then link
            if new_text:
                edit_note(item_id, new_text)
            
            for unlink_id in unlink_ids:
                unlink_notes(item_id, unlink_id)
            
            for link_id in link_ids:
                link_notes(item_id, link_id)
        
        elif item_type == "task":
            # Handle task editing options
            new_title = None
            new_due = None
            note_text = None
            recur_pattern = None
            
            i = 0
            while i < len(options):
                if options[i] == "-text" and i + 1 < len(options):
                    new_title = options[i + 1]
                    i += 2
                elif options[i] == "-due" and i + 1 < len(options):
                    new_due = parse_due(options[i + 1])
                    i += 2
                elif options[i] == "-note" and i + 1 < len(options):
                    note_text = options[i + 1]
                    i += 2
                elif options[i] == "-recur" and i + 1 < len(options):
                    recur_pattern = options[i + 1]
                    i += 2
                else:
                    # Skip unknown option
                    i += 1
            
            # Perform operations
            if new_title:
                edit_task(item_id, new_title)
            
            if new_due:
                with sqlite3.connect(DB_FILE) as conn:
                    conn.execute(
                        "UPDATE tasks SET due_date=? WHERE id=?",
                        (new_due.strftime("%Y-%m-%d"), item_id)
                    )
                    print(f"Updated due date for task {item_id} to {new_due.strftime('%Y-%m-%d')}")
            
            if note_text:
                # Add note to the task
                add_note([item_id], note_text)
                
            if recur_pattern:
                # Validate and set recur pattern
                if set_task_recur([item_id], recur_pattern):
                    print(f"Set recur pattern '{recur_pattern}' for task {item_id}")
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
    elif cmd == "edit":
        if rest and len(rest) >= 2:
            item_identifier = rest[0]
            new_text = " ".join(rest[1:])
            
            # Check if the identifier starts with 't' (task)
            if item_identifier.startswith("t") and item_identifier[1:].isdigit():
                print("Error: The 'edit' command for tasks has been removed. Use 'jrnl edit task <id> [-text <text>] [-due <text>] [-note <text>] [-recur <Nd|Nw|Nm|Ny>]' instead.")
            else:
                print("Error: The 'edit' command has been removed for tasks. For task editing, use 'jrnl edit task <id> [-text <text>] [-due <text>] [-note <text>] [-recur <Nd|Nw|Nm|Ny>]'. For note editing, use 'jrnl edit note <id> [-text <text>] [-link <id>[,<id>,...]] [-unlink <id>[,<id>,...]]'.")
        else:
            print("Error: Please use the consolidated commands: 'jrnl edit task <id> [options]' or 'jrnl edit note <id> [options]'")
    elif cmd == "rm":
        if rest and len(rest) >= 2:
            # Consolidated syntax: jrnl rm <note|task> <id>[,<id>,...]
            item_type = rest[0].lower()
            ids_str = rest[1]
            ids = [int(id_str) for id_str in ids_str.split(",") if id_str.isdigit()]
            
            if item_type == "note":
                delete_note(ids)
            elif item_type == "task":
                delete_task(ids)
            else:
                print("Error: Invalid item type. Use 'note' or 'task'")
                return
        else:
            print("Error: Please use the consolidated command: 'jrnl rm <note|task> <id>[,<id>,...]'. The old syntax 'jrnl rm t<id>[,n<id>...] has been removed.'")
    elif cmd in ["task", "t"]:
        show_task()
    elif cmd in ["note", "n"]:
        show_note()
    elif cmd == "done" and not rest:  # Only if no additional arguments (to distinguish from 'done' status command)
        # The old done command has been removed
        print("Error: The 'jrnl done' command has been removed. Use 'jrnl list task done' instead.")
    elif cmd in ["done", "x"] and rest:
        # The old done command has been removed
        print("Error: The 'jrnl done <id> <note>' command has been removed. Use 'jrnl done task <id>[,<id>...] <note text>' instead.")
    elif cmd in ["status", "s"]:
        # The old status command has been removed
        print("Error: The 'jrnl status' command has been removed. Use 'jrnl list task status' instead.")
    elif cmd in ["due", "d"]:
        # The old due command has been removed
        print("Error: The 'jrnl due' command has been removed. Use 'jrnl list task due' instead.")
    elif cmd == "recur":
        # The 'recur' command has been replaced with the consolidated command
        print("Error: The 'recur' command has been removed. Use 'jrnl task <id> edit -recur <Nd|Nw|Nm|Ny>' instead.")
    elif cmd in ["waiting", "start", "restart"]:
        # The old status commands have been removed
        print(f"Error: The 'jrnl {cmd}' command has been removed. Use 'jrnl {cmd} task <id>[,<id>...]' instead.")
    elif cmd == "delete":
        # The delete command should be handled by 'jrnl rm task ...'
        print("Error: The 'jrnl delete' command has been removed. Use 'jrnl rm task <id>[,<id>...]' instead.")
    elif cmd == "list" and len(rest) >= 1:
        # New consolidated command: jrnl list <page|note|task> <optional: due|status|done>
        if rest[0] == "page":
            show_journal()
        elif rest[0] == "note":
            show_note()
        elif rest[0] == "task" and len(rest) == 1:
            # Default to showing tasks grouped by creation date (similar to notes)
            show_task()
        elif rest[0] == "task" and len(rest) >= 2:
            if rest[1] == "due":
                show_due()
            elif rest[1] == "status":
                show_tasks_by_status()
            elif rest[1] == "done":
                show_completed_tasks()
            else:
                print("Error: Invalid task list option. Use 'due', 'status', or 'done'")
        else:
            print("Error: Invalid syntax. Use 'jrnl list <page|note|task>' or 'jrnl list task <due|status|done>'")
    elif cmd == "search":
        if rest:
            search_text = " ".join(rest)
            grouped, tasks, notes = search_tasks_and_notes(search_text)
            display_search_results(grouped)
        else:
            print("Error: Please provide search text")
    elif cmd == "help":
        print("""j - Command Line Journal and Task Manager

USAGE:
    j [command] [arguments...]

COMMANDS:
    j
        Show tasks grouped by due date (default view) (Overdue / Due Today / Due Tomorrow / This Week / This Month / Future / No Due Date)
    j new note <text> [-link <id>[,<id>,...]]
        Add a new note with optional links
    j new task [@<pid>] <text> [-due <YYYY-MM-DD|today|tomorrow|eow|eom|eoy>] [-recur <Nd|Nw|Nm|Ny>]
        Add a new task with optional parent task, due date and recurrence
    j edit note <id> [-text <text>] [-link <id>[,<id>,...]] [-unlink <id>[,<id>,...]]
        Edit note with optional text, linking, unlinking
    j edit task <id> [-text <text>] [-due <date>] [-note <text>] [-recur <pattern>]
        Edit task with optional parameters
    j rm <note|task> <id>[,<id>,...]
        Delete notes or tasks by ID
    j list <page|note|task> [due|status|done]
        List items with optional grouping
    j show <note|task> <id>
        Show specific note or task
    j <start|restart|waiting|done> task <id>[,<id>,...]
        Task status operations
    j done task <id>[,<id>,...] [note text]
        Mark task(s) as done with optional note
    j search <text>
        Search for tasks and notes containing text (supports wildcards: * = any chars, ? = single char)
    j help
        Show this help message
""")
    else:
        print(f"Error: Unknown command '{cmd}'. Use 'j help' to see available commands.")

if __name__ == "__main__":
    main()
