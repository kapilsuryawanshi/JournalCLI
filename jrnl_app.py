import argparse
import sqlite3
import os
import sys
from datetime import datetime, timedelta, date
from collections import defaultdict
from colorama import Fore, Back, Style, init

# Placeholder for database file path - will be set by command line arguments
DB_FILE = None
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
        # Drop old tables if they exist
        conn.execute("DROP TABLE IF EXISTS tasks")
        conn.execute("DROP TABLE IF EXISTS notes")
        conn.execute("DROP TABLE IF EXISTS note_links")
        
        # Create new simplified schema tables
        conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT CHECK(type IN ('todo','note')) DEFAULT 'todo',
            title TEXT NOT NULL,
            creation_date TEXT NOT NULL,
            pid INTEGER,
            FOREIGN KEY(pid) REFERENCES items(id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS todo_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            status TEXT CHECK(status IN ('todo','doing','waiting','done')) DEFAULT 'todo',
            due_date TEXT NOT NULL,
            completion_date TEXT,
            recur TEXT,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS item_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item1_id INTEGER NOT NULL,
            item2_id INTEGER NOT NULL,
            FOREIGN KEY(item1_id) REFERENCES items(id),
            FOREIGN KEY(item2_id) REFERENCES items(id),
            UNIQUE(item1_id, item2_id)
        )
        """)

def get_item_by_id(item_id):
    """Retrieve an item by ID
    
    Args:
        item_id (int): The ID of the item to retrieve
    
    Returns:
        tuple: (id, type, title, creation_date, pid) or None if not found
    """
    with sqlite3.connect(DB_FILE) as conn:
        item = conn.execute(
            "SELECT id, type, title, creation_date, pid FROM items WHERE id=?",
            (item_id,)
        ).fetchone()
        return item


def get_todo_info(item_id):
    """Retrieve todo information by item ID
    
    Args:
        item_id (int): The ID of the item to get todo info for
    
    Returns:
        tuple: (id, item_id, status, due_date, completion_date, recur) or None if not found
    """
    with sqlite3.connect(DB_FILE) as conn:
        todo_info = conn.execute(
            "SELECT id, item_id, status, due_date, completion_date, recur FROM todo_info WHERE item_id=?",
            (item_id,)
        ).fetchone()
        return todo_info


def get_item_links(item_id):
    """Get all links for an item
    
    Args:
        item_id (int): The ID of the item to get links for
    
    Returns:
        list: List of tuples containing (item1_id, item2_id) for links
    """
    with sqlite3.connect(DB_FILE) as conn:
        links = conn.execute(
            "SELECT item1_id, item2_id FROM item_links WHERE item1_id=? OR item2_id=?",
            (item_id, item_id)
        ).fetchall()
        return links

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


def calculate_next_due_date(original_due_date_str, recur_pattern):
    """
    Calculate the next due date based on the original due date and recurrence pattern.
    
    Args:
        original_due_date_str (str): Original due date in 'YYYY-MM-DD' format
        recur_pattern (str): Recurrence pattern like '2d', '1w', '3m', '1y'
    
    Returns:
        str: New due date in 'YYYY-MM-DD' format
    """
    # Parse the original due date
    original_date = datetime.strptime(original_due_date_str, "%Y-%m-%d").date()
    
    # Parse the recurrence pattern
    number = int(recur_pattern[:-1])
    unit = recur_pattern[-1].lower()
    
    # Calculate the next date based on the unit
    if unit == 'd':  # Days
        new_date = original_date + timedelta(days=number)
    elif unit == 'w':  # Weeks
        new_date = original_date + timedelta(weeks=number)
    elif unit == 'm':  # Months
        # Adding months is more complex because months have different lengths
        year = original_date.year
        month = original_date.month + number
        
        # Handle year overflow
        while month > 12:
            year += 1
            month -= 12
        
        # Get the day - try to keep the same day, but adjust for shorter months
        day = original_date.day
        max_day = 31
        # Find the maximum day for the target month
        while True:
            try:
                test_date = date(year, month, day)
                new_date = test_date
                break
            except ValueError:
                day -= 1
                if day <= 0:
                    # If the day becomes invalid, use the last day of the month
                    # Find last day of previous month and add 1 to get to target month
                    if month == 1:
                        last_day_of_prev_month = date(year - 1, 12, 31) - date(year - 1, 11, 30)
                        day = 30  # Use 30 as fallback
                    else:
                        last_day_prev_month = date(year, month - 1, 1) - timedelta(days=1)
                        day = last_day_prev_month.day
                    try:
                        new_date = date(year, month, day)
                        break
                    except ValueError:
                        # If still invalid, reduce day further
                        day -= 1
                        if day <= 0:
                            day = 1
                        new_date = date(year, month, day)
                        break
    
    elif unit == 'y':  # Years
        year = original_date.year + number
        month = original_date.month
        day = original_date.day
        
        # Handle leap year edge cases
        try:
            new_date = date(year, month, day)
        except ValueError:
            # If date is not valid (e.g., Feb 29 on a non-leap year), use Feb 28
            if month == 2 and day == 29:
                new_date = date(year, 2, 28)
            else:
                # This shouldn't happen in normal cases, but just in case
                new_date = date(year, month, min(day, [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1]))
    
    else:
        # Default to original date if unit is unknown
        new_date = original_date
    
    return new_date.strftime("%Y-%m-%d")

# --- Display Helpers ---

def format_item(item, prefix=""):
    """Format an item (todo or note) for display"""
    # item has: id, type, title, creation_date, pid
    item_id, item_type, title, creation_date, pid = item
    
    if item_type == 'todo':
        # Get todo info
        with sqlite3.connect(DB_FILE) as conn:
            todo_info = conn.execute(
                "SELECT status, due_date, completion_date, recur FROM todo_info WHERE item_id=?",
                (item_id,)
            ).fetchone()
            
        if todo_info:
            status, due_date, completion_date, recur = todo_info
        else:
            # Default values for todo if not in todo_info table
            status, due_date, completion_date, recur = 'todo', creation_date, None, None
        
        checkbox = "[x]" if status == "done" else "[ ]"

        # Color based on status
        if status == "doing":
            text = prefix + Back.YELLOW + Fore.BLACK + f"{checkbox} {title} (id:{item_id})" + Style.RESET_ALL
        elif status == "waiting":
            text = prefix + Back.LIGHTBLACK_EX + Fore.WHITE + f"{checkbox} {title} (id:{item_id})" + Style.RESET_ALL
        elif status == "done":
            text = prefix + Fore.GREEN + f"{checkbox} {title} (id:{item_id})" + Style.RESET_ALL
        else:  # todo
            text = prefix + f"{checkbox} {title}  (id:{item_id})"

        # Show recur pattern if it exists
        if recur:
            text += f" (recur: {recur})"

        # Show due date
        if status != "done":
            due = datetime.strptime(due_date, "%Y-%m-%d").date()
            today = datetime.now().date()
            if due < today:
                text += Fore.RED + f" (due: {format_date_with_day(due_date)})"
            elif due == today:
                text += Fore.CYAN + f" (due: {format_date_with_day(due_date)})"
            else:
                text += f" (due: {format_date_with_day(due_date)})"

        return text + Style.RESET_ALL
    else:  # note
        # For notes, simply return the formatted text
        return prefix + Fore.YELLOW + f"> {title} (id:{item_id}) ({creation_date})" + Style.RESET_ALL

def build_item_tree(items_list):
    """
    Build a tree structure from a list of items.
    Returns root items and children mapping.
    """
    # Create a dictionary to store items by ID for easy lookup
    item_dict = {item[0]: item for item in items_list}  # item[0] is id

    # Create a dictionary to store children for each item
    children = {item[0]: [] for item in items_list}  # item[0] is id

    # Build the tree structure
    root_items = []
    # Create a set of all item IDs in this list for quick lookup
    item_ids = {item[0] for item in items_list}
    
    for item in items_list:
        item_id = item[0]  # item[0] is id
        parent_id = item[4]  # item[4] is pid

        if parent_id is None or parent_id == 0 or parent_id not in item_ids:
            # This is a root item (no parent, or parent is 0, or parent is not in this subset)
            root_items.append(item)
        else:
            # This is a child item, add it to its parent's children
            if parent_id in children:
                children[parent_id].append(item)

    return root_items, children, item_dict

def print_item_tree(item, children, item_dict, is_last=True, prefix="", is_root=True):
    """
    Recursively print an item and its children in a tree structure using tab indentation.
    """
    item_id = item[0]  # item[0] is id

    # For root items, use one tab
    if is_root:
        prefix_str = "\t"
        print(format_item(item, prefix_str))
    else:
        # For child items, use prefix with tab
        print(format_item(item, prefix + "\t"))

    # Recursively print children with appropriate prefixes - add one more tab for children
    if item_id in children and children[item_id]:
        for i, child in enumerate(children[item_id]):
            is_last_child = (i == len(children[item_id]) - 1)
            # For children, we need to add an additional tab level
            child_prefix = prefix + "\t"
            print_item_tree(child, children, item_dict, is_last_child, child_prefix, is_root=False)

# --- Command Handlers ---

def add_item(title, item_type, parent_id=None):
    """Add a new item (todo or note) to the database
    
    Args:
        title (str): The title/text of the item
        item_type (str): 'todo' or 'note'
        parent_id (int, optional): ID of parent item if this is a child
    
    Returns:
        int: The ID of the newly created item
    """
    today = datetime.now().date().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute(
            "INSERT INTO items (type, title, creation_date, pid) VALUES (?, ?, ?, ?)",
            (item_type, title, today, parent_id)
        )
        item_id = cursor.lastrowid
        
        # For todo items, add default entry in todo_info table
        if item_type == 'todo':
            conn.execute(
                "INSERT INTO todo_info (item_id, status, due_date) VALUES (?, 'todo', ?)",
                (item_id, today)  # Default due date to today
            )
    
    return item_id
    
def add_task(texts):
    """Add a new task (todo item)"""
    added_task_ids = []
    for raw in texts:
        raw = raw.strip()
        if "@" in raw:
            title, due_kw = raw.split("@", 1)
            due = parse_due(due_kw.strip())
            item_id = add_item_with_details(title.strip(), "todo", due.strftime("%Y-%m-%d"))
        else:
            title = raw
            item_id = add_item(title.strip(), "todo")
        added_task_ids.append(item_id)

    if added_task_ids:
        if len(added_task_ids) == 1:
            print(f"Added task with id {added_task_ids[0]}")
        else:
            print(f"Added tasks with IDs: {', '.join(map(str, added_task_ids))}")

    return added_task_ids

def add_note_under_note(parent_note_id, text):
    """Add a note under another specific note"""
    # Verify the parent note exists
    with sqlite3.connect(DB_FILE) as conn:
        parent_note = conn.execute("SELECT id FROM items WHERE id=? AND type='note'", (parent_note_id,)).fetchone()
        if not parent_note:
            print(f"Error: Parent note with ID {parent_note_id} does not exist")
            return False

    # Add the note with parent_id
    item_id = add_item(text, "note", parent_note_id)
    print(f"Added note with id {item_id} under parent note {parent_note_id}")
    return item_id

def add_note(task_ids, text, parent_note_id=None):
    """Add a note, either standalone, under a task, or under another note"""
    added_note_ids = []
    
    if not task_ids and parent_note_id is None:
        # Add standalone note
        item_id = add_item(text, "note")
        added_note_ids.append(item_id)
    elif parent_note_id is not None:
        # Add note under parent note
        item_id = add_item(text, "note", parent_note_id)
        added_note_ids.append(item_id)
    elif task_ids:
        # Add note under tasks - for each task ID, create a note with that task as parent
        for tid in task_ids:
            # Verify the parent task exists
            with sqlite3.connect(DB_FILE) as conn:
                parent_task = conn.execute("SELECT id FROM items WHERE id=? AND type='todo'", (tid,)).fetchone()
                if not parent_task:
                    print(f"Error: Parent task with ID {tid} does not exist")
                    continue
            
            item_id = add_item(text, "note", tid)  # Using tid as parent id
            added_note_ids.append(item_id)

    if added_note_ids:
        if len(added_note_ids) == 1:
            note_id = added_note_ids[0]
            if parent_note_id is not None:
                print(f"Added note with id {note_id} under parent note {parent_note_id}")
            elif task_ids:
                print(f"Added note with id {note_id} to task {task_ids[0]}")
            else:
                print(f"Added standalone note with id {note_id}")
        else:
            # Multiple notes added
            if task_ids:
                print(f"Added notes with IDs {', '.join(map(str, added_note_ids))} to tasks {', '.join(map(str, task_ids))}")
            else:
                print(f"Added notes with IDs: {', '.join(map(str, added_note_ids))}")

    return added_note_ids

def update_task_status(task_ids, status, note_text=None):
    """Update the status of task items"""
    updated_count = 0
    for tid in task_ids:
        # Get the current task details before updating the status
        with sqlite3.connect(DB_FILE) as conn:
            task_details = conn.execute("""
                SELECT i.title, i.pid, t.recur, t.due_date 
                FROM items i
                JOIN todo_info t ON i.id = t.item_id
                WHERE i.id = ?
            """, (tid,)).fetchone()
        
        # Update todo status
        update_todo_status(tid, status)
        updated_count += 1
        
        # Add note to the completed task if provided
        if status == 'done' and note_text:
            add_note([], note_text)

        # Handle recurring tasks: create a new task if this one has a recurrence pattern
        if status == 'done' and task_details:
            title, parent_id, recur_pattern, original_due_date = task_details
            if recur_pattern:
                # Calculate the next due date based on the recurrence pattern
                next_due_date = calculate_next_due_date(original_due_date, recur_pattern)
                
                # Get the original task's details to create a new one
                with sqlite3.connect(DB_FILE) as conn:
                    original_task = conn.execute(
                        "SELECT type, title, creation_date FROM items WHERE id=?",
                        (tid,)
                    ).fetchone()

                if original_task:
                    task_type, task_title, creation_date = original_task
                    # Create a new task with the same title and parent, but updated due date
                    new_task_id = add_item_with_details(task_title, task_type, next_due_date, parent_id)
                    
                    # Set the recurrence pattern for the new task
                    with sqlite3.connect(DB_FILE) as conn:
                        # Since todo_info entry was created by add_item_with_details, update the recur field
                        conn.execute(
                            "UPDATE todo_info SET recur=? WHERE item_id=?",
                            (recur_pattern, new_task_id)
                        )
                    
                    print(f"Created recurring task (id:{new_task_id}) due: {next_due_date}")
    
    if updated_count > 0:
        status_display = "undone" if status == "todo" else status
        if updated_count == 1:
            print(f"Updated task {task_ids[0]} to {status_display}")
        else:
            print(f"Updated {updated_count} tasks to {status_display}")

def update_todo_status(item_id, status):
    """Update the status of a todo item"""
    today = datetime.now().date().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_FILE) as conn:
        # Check if there's already an entry in todo_info
        existing = conn.execute(
            "SELECT item_id FROM todo_info WHERE item_id=?",
            (item_id,)
        ).fetchone()
        
        if existing:
            # Update the existing record
            if status == 'done':
                conn.execute(
                    "UPDATE todo_info SET status=?, completion_date=? WHERE item_id=?",
                    (status, today, item_id)
                )
            else:
                conn.execute(
                    "UPDATE todo_info SET status=?, completion_date=NULL WHERE item_id=?",
                    (status, item_id)
                )
        else:
            # Insert new record
            conn.execute(
                "INSERT INTO todo_info (item_id, status, due_date) VALUES (?, ?, ?)",
                (item_id, status, today)
            )

def set_task_recur(task_ids, recur_pattern):
    """Set the recur pattern for tasks"""
    # Validate the recur pattern
    if not recur_pattern or len(recur_pattern) < 2:
        print("Error: Invalid recur pattern. Use...")
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
            # Check if a record exists in todo_info, if not create one
            existing = conn.execute(
                "SELECT item_id FROM todo_info WHERE item_id=?",
                (tid,)
            ).fetchone()
            
            if not existing:
                # Create a new record with default values
                conn.execute(
                    "INSERT INTO todo_info (item_id, status, due_date) VALUES (?, 'todo', ?)",
                    (tid, datetime.now().date().strftime("%Y-%m-%d"))
                )
            
            # Update the recur field
            conn.execute(
                "UPDATE todo_info SET recur=? WHERE item_id=?",
                (recur_pattern, tid)
            )
    return True

def edit_task(task_id, new_title):
    """Edit the title of a task"""
    with sqlite3.connect(DB_FILE) as conn:
        # Check if item exists
        cursor = conn.execute("SELECT id FROM items WHERE id=? AND type='todo'", (task_id,))
        if not cursor.fetchone():
            print(f"Error: Task with ID {task_id} not found")
            return False

        # Update the item title
        conn.execute(
            "UPDATE items SET title=? WHERE id=?",
            (new_title, task_id)
        )
        print(f"Updated task {task_id} title to: {new_title}")
        return True

def edit_note(note_id, new_text):
    """Edit the text of a note"""
    with sqlite3.connect(DB_FILE) as conn:
        # Check if item exists
        cursor = conn.execute("SELECT id FROM items WHERE id=? AND type='note'", (note_id,))
        if not cursor.fetchone():
            print(f"Error: Note with ID {note_id} not found")
            return False

        # Update the item text (stored in title field)
        conn.execute(
            "UPDATE items SET title=? WHERE id=?",
            (new_text, note_id)
        )
        print(f"Updated note {note_id} text to: {new_text}")
        return True


def add_task_under_note(note_id, text):
    """Add a task under a specific note"""
    # Verify the note exists
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM items WHERE id=? AND type='note'", (note_id,)).fetchone()
        if not note:
            print(f"Error: Note with ID {note_id} does not exist")
            return False

    # Add the task with parent_id
    today = datetime.now().date().strftime("%Y-%m-%d")
    item_id = add_item_with_details(text, "todo", today, note_id)
    print(f"Added task with id {item_id} to note {note_id}")
    return item_id


def delete_item(item_ids):
    """Delete items (both notes and todos) from the database"""
    if not item_ids:
        print("No items to delete")
        return

    # Get all items that need to be deleted (including children)
    all_items_to_delete = set(item_ids)

    with sqlite3.connect(DB_FILE) as conn:
        # Find all child items recursively using a loop
        current_items = list(item_ids)
        while current_items:
            # Get children of current items
            placeholders = ",".join("?" * len(current_items))
            children = conn.execute(
                f"SELECT id FROM items WHERE pid IN ({placeholders})",
                current_items
            ).fetchall()

            # Add children to the deletion list
            current_items = [child[0] for child in children]
            all_items_to_delete.update(current_items)

    # Ask for confirmation before deletion
    total_items = len(all_items_to_delete)
    if total_items == 0:
        print("No items to delete")
        return

    print(f"Warning: You are about to delete {total_items} item(s) (including children). This action cannot be undone.")
    confirmation = input("Type 'yes' to confirm deletion: ").strip().lower()

    if confirmation != 'yes':
        print("Deletion cancelled.")
        return

    # Now delete all items and their associated data
    deleted_count = 0
    with sqlite3.connect(DB_FILE) as conn:
        for item_id in all_items_to_delete:
            # First delete any links associated with this item
            conn.execute("DELETE FROM item_links WHERE item1_id=? OR item2_id=?", (item_id, item_id))
            # Then delete the todo_info record if it exists
            conn.execute("DELETE FROM todo_info WHERE item_id=?", (item_id,))
            # Then delete the item
            cursor = conn.execute("DELETE FROM items WHERE id=?", (item_id,))
            if cursor.rowcount > 0:
                deleted_count += 1

    if deleted_count > 0:
        if deleted_count == 1:
            print(f"Deleted 1 item (including children if any)")
        else:
            print(f"Deleted {deleted_count} items (including children if any)")
    else:
        print("No items were deleted")

def clear_all():
    """Clear all data from the database after confirmation"""
    # First, count existing items
    with sqlite3.connect(DB_FILE) as conn:
        total_items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        total_links = conn.execute("SELECT COUNT(*) FROM item_links").fetchone()[0]
        total_todo_info = conn.execute("SELECT COUNT(*) FROM todo_info").fetchone()[0]
    
    total_data_points = total_items + total_links + total_todo_info
    
    if total_data_points == 0:
        print("Database is already empty.")
        return
    
    print(f"WARNING: You are about to permanently delete ALL data from the database.")
    print(f"This will remove {total_items} items, {total_links} links, and {total_todo_info} todo info records.")
    print("THIS ACTION CANNOT BE UNDONE.")
    print()
    
    confirmation = input("To confirm, type 'DELETE ALL DATA NOW': ").strip()
    
    if confirmation == 'DELETE ALL DATA NOW':
        with sqlite3.connect(DB_FILE) as conn:
            # Delete all records from all tables
            conn.execute("DELETE FROM item_links")
            conn.execute("DELETE FROM todo_info")
            conn.execute("DELETE FROM items")
        
        print(f"Successfully deleted {total_data_points} data points. Database is now empty.")
    else:
        print("Operation cancelled. No data was deleted.")

def link_notes(note1_id, note2_id):
    """Create a link between two notes"""
    # Verify both items are notes
    with sqlite3.connect(DB_FILE) as conn:
        item1 = conn.execute("SELECT id, type FROM items WHERE id=?", (note1_id,)).fetchone()
        item2 = conn.execute("SELECT id, type FROM items WHERE id=?", (note2_id,)).fetchone()

        if not item1:
            print(f"Error: Note with ID {note1_id} does not exist")
            return False
        if not item2:
            print(f"Error: Note with ID {note2_id} does not exist")
            return False
            
        if item1[1] != 'note' or item2[1] != 'note':
            print(f"Error: Both IDs must be notes")
            return False

    return link_items(note1_id, note2_id)

def unlink_notes(note1_id, note2_id):
    """Remove a link between two notes"""
    with sqlite3.connect(DB_FILE) as conn:
        # Check if both notes exist
        item1 = conn.execute("SELECT id FROM items WHERE id=? AND type='note'", (note1_id,)).fetchone()
        item2 = conn.execute("SELECT id FROM items WHERE id=? AND type='note'", (note2_id,)).fetchone()

        if not item1:
            print(f"Error: Note with ID {note1_id} does not exist")
            return False
        if not item2:
            print(f"Error: Note with ID {note2_id} does not exist")
            return False

        # Delete the link (handle it in either direction)
        cursor = conn.execute(
            "DELETE FROM item_links WHERE (item1_id=? AND item2_id=?) OR (item1_id=? AND item2_id=?)",
            (note1_id, note2_id, note2_id, note1_id)
        )

        if cursor.rowcount > 0:
            print(f"Unlinked notes {note1_id} and {note2_id}")
            return True
        else:
            print(f"Notes {note1_id} and {note2_id} were not linked")
            return True

def link_items(item1_id, item2_id):
    """Create a link between two items"""
    if item1_id == item2_id:
        print(f"Error: Cannot link an item to itself (id: {item1_id})")
        return False

    with sqlite3.connect(DB_FILE) as conn:
        # Check if both items exist
        item1_exists = conn.execute("SELECT id FROM items WHERE id=?", (item1_id,)).fetchone()
        item2_exists = conn.execute("SELECT id FROM items WHERE id=?", (item2_id,)).fetchone()

        if not item1_exists:
            print(f"Error: Item with ID {item1_id} does not exist")
            return False
        if not item2_exists:
            print(f"Error: Item with ID {item2_id} does not exist")
            return False

        # Check if the link already exists (in either direction)
        link_exists = conn.execute(
            "SELECT id FROM item_links WHERE (item1_id=? AND item2_id=?) OR (item1_id=? AND item2_id=?)",
            (item1_id, item2_id, item2_id, item1_id)
        ).fetchone()

        if link_exists:
            print(f"Items {item1_id} and {item2_id} are already linked")
            return True

        # Create the link (order items in ascending order for consistency)
        if item1_id > item2_id:
            item1_id, item2_id = item2_id, item1_id

        conn.execute(
            "INSERT INTO item_links (item1_id, item2_id) VALUES (?, ?)",
            (item1_id, item2_id)
        )
        print(f"Linked items {item1_id} and {item2_id}")
        return True

def show_journal():
    with sqlite3.connect(DB_FILE) as conn:
        # Get all items ordered by creation date
        all_items = conn.execute(
            "SELECT id, type, title, creation_date, pid FROM items ORDER BY creation_date ASC, id ASC"
        ).fetchall()

    # group items by creation_date
    grouped = defaultdict(lambda: {"items": []})
    for item in all_items:
        creation_date = item[3]  # item[3] is creation_date
        grouped[creation_date]["items"].append(item)

    for day in sorted(grouped.keys()):
        print()
        print(format_date_with_day(day))

        # Build and print item tree for this day
        day_items = grouped[day]["items"]
        if day_items:
            root_items, children, item_dict = build_item_tree(day_items)
            for i, root_item in enumerate(root_items):
                is_last = (i == len(root_items) - 1)
                print_item_tree(root_item, children, item_dict, is_last, "", is_root=True)

def show_due():
    with sqlite3.connect(DB_FILE) as conn:
        # First, find all completed root tasks
        completed_roots = conn.execute("""
            SELECT i.id FROM items i
            JOIN todo_info t ON i.id = t.item_id
            WHERE t.status = 'done' AND i.pid IS NULL
        """).fetchall()

        completed_root_ids = [str(row[0]) for row in completed_roots]

        # Find all descendants of these completed roots using recursive CTE
        if completed_root_ids:
            exclude_query = """
                WITH RECURSIVE item_descendants AS (
                    -- Base case: the completed root tasks themselves
                    SELECT id FROM items WHERE id IN ({})

                    UNION ALL
                    -- Recursive case: child items of items in the descendants
                    SELECT i.id
                    FROM items i
                    JOIN item_descendants idesc ON i.pid = idesc.id
                )
                SELECT id FROM item_descendants
            """.format(",".join("?" * len(completed_root_ids)))

            excluded_item_ids = conn.execute(exclude_query, completed_root_ids).fetchall()
            excluded_ids_set = set(row[0] for row in excluded_item_ids)
        else:
            excluded_ids_set = set()

        # Get root tasks (tasks with no parent or with note as parent) that are not completed, grouped by due date
        # Use the same root task definition as in show_task() - tasks with no parent or note as parent
        root_items = conn.execute("""
            SELECT i.id, i.type, i.title, i.creation_date, i.pid
            FROM items i
            JOIN todo_info t ON i.id = t.item_id
            WHERE i.type = 'todo'
              AND (i.pid IS NULL OR i.pid IN (SELECT id FROM items WHERE type = 'note'))
              AND i.id NOT IN ({})
            ORDER BY t.due_date ASC, i.id ASC
        """.format(",".join("?" * len(list(excluded_ids_set))) if excluded_ids_set else "SELECT NULL WHERE 1=0", list(excluded_ids_set) if excluded_ids_set else [])
        ).fetchall()

    # Group root items by their due date buckets
    buckets = {
        "Future": [],
        "This Month": [],
        "This Week": [],
        "Due Tomorrow": [],
        "Due Today": [],
        "Overdue": [],
        "No Due Date": []
    }

    # Helper function to determine which bucket a due date belongs to
    def get_item_bucket(due_date_str):
        if not due_date_str:
            return "No Due Date"

        due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        # Calculate the end of this week (Sunday) and end of this month
        end_of_week = today + timedelta(days=(6 - today.weekday()))
        if today.month == 12:
            end_of_month = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

        if due < today:
            return "Overdue"
        elif due == today:
            return "Due Today"
        elif due == tomorrow:
            return "Due Tomorrow"
        elif due <= end_of_week:
            return "This Week"
        elif due <= end_of_month:
            return "This Month"
        else:
            return "Future"

    # For each root item, get its complete hierarchy and determine its bucket
    for root_item in root_items:
        # Get the bucket for this root item based on its due date
        with sqlite3.connect(DB_FILE) as temp_conn:
            due_date_result = temp_conn.execute(
                "SELECT due_date FROM todo_info WHERE item_id=?",
                (root_item[0],)
            ).fetchone()

        bucket_label = "No Due Date"
        if due_date_result and due_date_result[0]:
            bucket_label = get_item_bucket(due_date_result[0])

        # Get complete hierarchy under this root item (including all children - notes and tasks)
        with sqlite3.connect(DB_FILE) as temp_conn:
            all_descendants = temp_conn.execute("""
                WITH RECURSIVE item_tree AS (
                    -- Base case: the root item itself
                    SELECT id, type, title, creation_date, pid
                    FROM items
                    WHERE id = ?

                    UNION ALL
                    -- Recursive case: all child items (notes and tasks)
                    SELECT i.id, i.type, i.title, i.creation_date, i.pid
                    FROM items i
                    JOIN item_tree it ON i.pid = it.id
                )
                SELECT id, type, title, creation_date, pid
                FROM item_tree
                ORDER BY id ASC
            """, (root_item[0],)).fetchall()

        # Build tree structure for this root with all its descendants
        all_root_nodes, all_children, all_item_dict = build_item_tree(all_descendants)

        # Add the root and its complete hierarchy to the appropriate bucket
        if all_root_nodes:  # Should only have one root node
            root_node = all_root_nodes[0]
            bucket_info = {
                'root_node': root_node,
                'children': all_children,
                'item_dict': all_item_dict
            }
            buckets[bucket_label].append(bucket_info)

    # Print each bucket in the correct order
    for label in ["Future", "This Month", "This Week", "Due Tomorrow", "Due Today", "Overdue", "No Due Date"]:
        if buckets[label]:
            print(f"\n{label}")
            # Print items in this bucket maintaining their tree structure
            for i, bucket_info in enumerate(buckets[label]):
                is_last = (i == len(buckets[label]) - 1)
                print_item_tree(
                    bucket_info['root_node'], 
                    bucket_info['children'], 
                    bucket_info['item_dict'], 
                    is_last, 
                    "", 
                    is_root=True
                
                )
def show_task():
    with sqlite3.connect(DB_FILE) as conn:
        # Get only incomplete root tasks (items that have no parent OR have a note as parent and are not done)
        # A root task is defined as: a task which does not have any parent or which does not have a task as parent
        # So we want tasks where pid IS NULL OR where the parent item has type 'note'
        root_items = conn.execute("""
            SELECT i.id, i.type, i.title, i.creation_date, i.pid
            FROM items i
            LEFT JOIN todo_info t ON i.id = t.item_id
            WHERE i.type = 'todo' 
              AND (i.pid IS NULL OR i.pid IN (SELECT id FROM items WHERE type = 'note'))
              AND (t.status != 'done' OR t.status IS NULL)
            ORDER BY i.creation_date ASC
        """).fetchall()

        # Group root items by creation_date
        grouped = defaultdict(list)
        for item in root_items:
            creation_date = item[3]  # item[3] is creation_date
            grouped[creation_date].append(item)

    for day in sorted(grouped.keys()):
        print()
        print(format_date_with_day(day))

        # For each root item of this day, get its complete hierarchy and print it
        day_root_items = grouped[day]
        for i, root_item in enumerate(day_root_items):
            is_last = (i == len(day_root_items) - 1)

            # Get the complete tree under this root item (including completed children)
            with sqlite3.connect(DB_FILE) as temp_conn:
                all_descendants = temp_conn.execute("""
                    WITH RECURSIVE item_tree AS (
                        -- Base case: the root item itself
                        SELECT id, type, title, creation_date, pid
                        FROM items
                        WHERE id = ?

                        UNION ALL
                        -- Recursive case: all child items
                        SELECT i.id, i.type, i.title, i.creation_date, i.pid
                        FROM items i
                        JOIN item_tree it ON i.pid = it.id
                    )
                    SELECT id, type, title, creation_date, pid
                    FROM item_tree
                    ORDER BY id
                """, (root_item[0],)).fetchall()  # root_item[0] is id

            # Build the tree structure including all items (done and not done)
            root_nodes, children, item_dict = build_item_tree(all_descendants)

            # Print each root node in this hierarchy (should just be the main root we started with)
            for j, item_node in enumerate(root_nodes):
                item_is_last = (j == len(root_nodes) - 1) and is_last
                print_item_tree(item_node, children, item_dict, item_is_last, "\t", True)

def show_note():
    with sqlite3.connect(DB_FILE) as conn:
        # Get all root items (items that have no parent) for the note view
        # This includes both notes and tasks that are root level
        root_items = conn.execute("""
            SELECT id, type, title, creation_date, pid
            FROM items
            WHERE pid IS NULL
            ORDER BY creation_date ASC, id ASC
        """).fetchall()

        # Group root items by creation_date
        grouped = defaultdict(list)
        for item in root_items:
            creation_date = item[3]  # item[3] is creation_date
            grouped[creation_date].append(item)

    for day in sorted(grouped.keys()):
        print()
        print(format_date_with_day(day))

        # For each root item of this day, get its complete hierarchy and print it
        day_root_items = grouped[day]
        for i, root_item in enumerate(day_root_items):
            is_last = (i == len(day_root_items) - 1)

            # Get the complete tree under this root item (including all children)
            with sqlite3.connect(DB_FILE) as temp_conn:
                all_descendants = temp_conn.execute("""
                    WITH RECURSIVE item_tree AS (
                        -- Base case: the root item itself
                        SELECT id, type, title, creation_date, pid
                        FROM items
                        WHERE id = ?

                        UNION ALL
                        -- Recursive case: all child items
                        SELECT i.id, i.type, i.title, i.creation_date, i.pid
                        FROM items i
                        JOIN item_tree it ON i.pid = it.id
                    )
                    SELECT id, type, title, creation_date, pid
                    FROM item_tree
                    ORDER BY id ASC
                """, (root_item[0],)).fetchall()  # root_item[0] is id

            # Build the tree structure including all items (notes and tasks)
            root_nodes, children, item_dict = build_item_tree(all_descendants)

            # Print each root node in this hierarchy (should just be the main root we started with)
            for j, item_node in enumerate(root_nodes):
                item_is_last = (j == len(root_nodes) - 1) and is_last
                print_item_tree(item_node, children, item_dict, item_is_last, "\t", True)

def print_item_children(conn, parent_item_id, indent):
    """Helper function to recursively print child items of an item"""
    # Get child items of this item
    child_items = conn.execute("""
        SELECT id, type, title, creation_date, pid
        FROM items
        WHERE pid = ?
        ORDER BY creation_date ASC, id ASC
    """, (parent_item_id,)).fetchall()

    # Print child items with current indentation
    for child_item in child_items:
        item_id, item_type, title, creation_date, pid = child_item
        if item_type == 'note':
            print(Fore.YELLOW + f"{indent}> {title} (id:{item_id}) ({creation_date})" + Style.RESET_ALL)

            # Recursively print children of this child item (grandchildren, etc.)
            print_item_children(conn, item_id, indent + "\t")
        elif item_type == 'todo':
            # For child todos
            with sqlite3.connect(DB_FILE) as temp_conn:
                todo_info = temp_conn.execute(
                    "SELECT status, due_date, completion_date, recur FROM todo_info WHERE item_id=?",
                    (item_id,)
                ).fetchone()
                
            if todo_info:
                status, due_date, completion_date, recur = todo_info
            else:
                # Default values
                status, due_date, completion_date, recur = 'todo', creation_date, None, None
                
            checkbox = "[x]" if status == "done" else "[ ]"

            # Color based on status
            if status == "doing":
                task_text = Back.YELLOW + Fore.BLACK + f"{checkbox} {title} (id:{item_id})" + Style.RESET_ALL
            elif status == "waiting":
                task_text = Back.LIGHTBLACK_EX + Fore.WHITE + f"{checkbox} {title} (id:{item_id})" + Style.RESET_ALL
            elif status == "done":
                task_text = Fore.GREEN + f"{checkbox} {title} (id:{item_id})" + Style.RESET_ALL
            else:  # todo
                task_text = f"{checkbox} {title}  (id:{item_id})"

            # Show recur pattern if it exists
            if recur:
                task_text += f" (recur: {recur})"

            # Show due date
            due = datetime.strptime(due_date, "%Y-%m-%d").date()
            today = datetime.now().date()
            if status != "done":
                if due < today:
                    task_text += Fore.RED + f" (due: {format_date_with_day(due_date)})"
                elif due == today:
                    task_text += Fore.CYAN + f" (due: {format_date_with_day(due_date)})"
                else:
                    task_text += f" (due: {format_date_with_day(due_date)})"

            print(Fore.YELLOW + f"{indent}{task_text}" + Style.RESET_ALL)

def show_note_details(note_id):
    """Show details of a specific note, including child items and linked items"""
    with sqlite3.connect(DB_FILE) as conn:
        # Get the specific item
        item = conn.execute("""
            SELECT id, type, title, creation_date, pid
            FROM items
            WHERE id=?
        """, (note_id,)).fetchone()

        if not item:
            print(f"Error: Item with ID {note_id} does not exist")
            return

        item_id, item_type, title, creation_date, pid = item

        if item_type != 'note':
            print(f"Error: Item with ID {note_id} is not a note")
            return

        # Print the note text in consistent format
        print(Fore.YELLOW + f"- {title} (id:{item_id}) ({creation_date})" + Style.RESET_ALL)

        # Get child items (items that have this note as parent)
        child_items = conn.execute("""
            SELECT id, type, title, creation_date, pid
            FROM items
            WHERE pid = ?
            ORDER BY creation_date ASC, id ASC
        """, (note_id,)).fetchall()

        # Print child items
        has_children = len(child_items) > 0
        if has_children:
            for child_item in child_items:
                child_item_id, child_item_type, child_title, child_creation_date, child_pid = child_item
                if child_item_type == 'note':
                    print(Fore.YELLOW + f"\t> {child_title} (id:{child_item_id}) ({child_creation_date})" + Style.RESET_ALL)
                    # Recursively display children of this child note (if any)
                    show_child_item_details(conn, child_item_id, "\t\t")
                elif child_item_type == 'todo':
                    # For child todos
                    with sqlite3.connect(DB_FILE) as temp_conn:
                        todo_info = temp_conn.execute(
                            "SELECT status, due_date, completion_date, recur FROM todo_info WHERE item_id=?",
                            (child_item_id,)
                        ).fetchone()
                        
                    if todo_info:
                        status, due_date, completion_date, recur = todo_info
                    else:
                        # Default values
                        status, due_date, completion_date, recur = 'todo', child_creation_date, None, None
                        
                    checkbox = "[x]" if status == "done" else "[ ]"

                    # Color based on status
                    if status == "doing":
                        task_text = Back.YELLOW + Fore.BLACK + f"{checkbox} {child_title} (id:{child_item_id})" + Style.RESET_ALL
                    elif status == "waiting":
                        task_text = Back.LIGHTBLACK_EX + Fore.WHITE + f"{child_title} (id:{child_item_id})" + Style.RESET_ALL
                    elif status == "done":
                        task_text = Fore.GREEN + f"{child_title} (id:{child_item_id})" + Style.RESET_ALL
                    else:  # todo
                        task_text = f"{checkbox} {child_title}  (id:{child_item_id})"

                    # Show recur pattern if it exists
                    if recur:
                        task_text += f" (recur: {recur})"

                    # Show due date
                    due = datetime.strptime(due_date, "%Y-%m-%d").date()
                    today = datetime.now().date()
                    if status != "done":
                        if due < today:
                            task_text += Fore.RED + f" (due: {format_date_with_day(due_date)})"
                        elif due == today:
                            task_text += Fore.CYAN + f" (due: {format_date_with_day(due_date)})"
                        else:
                            task_text += f" (due: {format_date_with_day(due_date)})"

                    print(Fore.YELLOW + f"\t{task_text}" + Style.RESET_ALL)

        # Get linked items
        linked_items = conn.execute("""
            SELECT il.item1_id, il.item2_id, i1.title as item1_title, i2.title as item2_title,
                   i1.type as item1_type, i2.type as item2_type,
                   i1.creation_date as item1_creation_date, i2.creation_date as item2_creation_date
            FROM item_links il
            JOIN items i1 ON (il.item1_id = i1.id)
            JOIN items i2 ON (il.item2_id = i2.id)
            WHERE il.item1_id = ? OR il.item2_id = ?
        """, (note_id, note_id)).fetchall()

        # Print linked items in consistent format
        if linked_items:
            print(Fore.CYAN + f"\nLinked items:" + Style.RESET_ALL)
            for link in linked_items:
                # Determine which item is the other one (not the one we're viewing)
                if link[0] == note_id:  # item1_id is the current note
                    other_item_id = link[1]
                    other_item_title = link[3]  # item2_title
                    other_item_type = link[5]   # item2_type
                    other_creation_date = link[7] # item2_creation_date
                else:  # item2_id is the current note
                    other_item_id = link[0]
                    other_item_title = link[2]  # item1_title
                    other_item_type = link[4]   # item1_type
                    other_creation_date = link[6] # item1_creation_date

                # Format the linked item consistently
                print(Fore.CYAN + f"  - {other_item_title} (id:{other_item_id}, type:{other_item_type}) ({other_creation_date})" + Style.RESET_ALL)
        else:
            if not has_children:
                print(Fore.CYAN + f"\nNo linked items found." + Style.RESET_ALL)

def show_child_item_details(conn, item_id, indent_prefix):
    """Helper function to recursively display child items of an item"""
    # Get child items of this item
    child_items = conn.execute("""
        SELECT id, type, title, creation_date, pid
        FROM items
        WHERE pid = ?
        ORDER BY creation_date ASC, id ASC
    """, (item_id,)).fetchall()

    # Print child items with additional indentation
    for child_item in child_items:
        item_id, item_type, child_title, child_creation_date, child_pid = child_item
        if item_type == 'note':
            print(Fore.YELLOW + f"{indent_prefix}> {child_title} (id:{item_id}) ({child_creation_date})" + Style.RESET_ALL)

            # Recursively display children of this child item (if any)
            show_child_item_details(conn, item_id, indent_prefix + "\t")
        elif item_type == 'todo':
            # For child todos
            with sqlite3.connect(DB_FILE) as temp_conn:
                todo_info = temp_conn.execute(
                    "SELECT status, due_date, completion_date, recur FROM todo_info WHERE item_id=?",
                    (item_id,)
                ).fetchone()
                
            if todo_info:
                status, due_date, completion_date, recur = todo_info
            else:
                # Default values
                status, due_date, completion_date, recur = 'todo', child_creation_date, None, None
                
            checkbox = "[x]" if status == "done" else "[ ]"

            # Color based on status
            if status == "doing":
                task_text = Back.YELLOW + Fore.BLACK + f"{checkbox} {child_title} (id:{item_id})" + Style.RESET_ALL
            elif status == "waiting":
                task_text = Back.LIGHTBLACK_EX + Fore.WHITE + f"{child_title} (id:{item_id})" + Style.RESET_ALL
            elif status == "done":
                task_text = Fore.GREEN + f"{child_title} (id:{item_id})" + Style.RESET_ALL
            else:  # todo
                task_text = f"{checkbox} {child_title}  (id:{item_id})"

            # Show recur pattern if it exists
            if recur:
                task_text += f" (recur: {recur})"

            # Show due date
            due = datetime.strptime(due_date, "%Y-%m-%d").date()
            today = datetime.now().date()
            if status != "done":
                if due < today:
                    task_text += Fore.RED + f" (due: {format_date_with_day(due_date)})"
                elif due == today:
                    task_text += Fore.CYAN + f" (due: {format_date_with_day(due_date)})"
                else:
                    task_text += f" (due: {format_date_with_day(due_date)})"

            print(Fore.YELLOW + f"{indent_prefix}{task_text}" + Style.RESET_ALL)

def add_item_with_details(title, item_type, due_date=None, parent_id=None):
    """Add an item with specific details
    
    Args:
        title (str): The title/text of the item
        item_type (str): 'todo' or 'note'
        due_date (str, optional): Due date in YYYY-MM-DD format for todos
        parent_id (int, optional): ID of parent item if this is a child
    
    Returns:
        int: The ID of the newly created item
    """
    today = datetime.now().date().strftime("%Y-%m-%d")
    if not due_date:
        due_date = today
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute(
            "INSERT INTO items (type, title, creation_date, pid) VALUES (?, ?, ?, ?)",
            (item_type, title, today, parent_id)
        )
        item_id = cursor.lastrowid
        
        # For todo items, add entry in todo_info table with specific due date
        if item_type == 'todo':
            conn.execute(
                "INSERT INTO todo_info (item_id, status, due_date) VALUES (?, 'todo', ?)",
                (item_id, due_date)
            )
    
    return item_id

def show_item_details(item_id):
    """Show details of a specific item (note or task), including child items and linked items"""
    with sqlite3.connect(DB_FILE) as conn:
        # Get the specific item
        item = conn.execute("""
            SELECT id, type, title, creation_date, pid
            FROM items
            WHERE id=?
        """, (item_id,)).fetchone()

        if not item:
            print(f"Error: Item with ID {item_id} does not exist")
            return

        item_id, item_type, title, creation_date, pid = item

        # Get all related items to build the entire tree (this item and all its descendants)
        all_related_items = conn.execute("""
            WITH RECURSIVE item_tree AS (
                -- Base case: the selected item
                SELECT id, type, title, creation_date, pid
                FROM items
                WHERE id = ?

                UNION ALL

                -- Recursive case: child items
                SELECT i.id, i.type, i.title, i.creation_date, i.pid
                FROM items i
                JOIN item_tree it ON i.pid = it.id
            )
            SELECT * FROM item_tree
            ORDER BY id;
            """, (item_id,)).fetchall()

        # Build the tree structure but ensure the requested item is treated as root for display
        item_dict = {item_data[0]: item_data for item_data in all_related_items}
        children = {item_data[0]: [] for item_data in all_related_items}

        # Build the hierarchy - connect children to parents that exist in our result set
        for item_data in all_related_items:
            item_id_data = item_data[0]
            parent_id = item_data[4]  # pid field

            # If parent exists in our subset, establish the relationship
            if parent_id and parent_id in children:
                children[parent_id].append(item_data)

        # The requested item should be displayed as root regardless of its actual parent
        requested_item = item_dict[item_id]

        # Print the requested item with its entire subtree
        print_item_tree(requested_item, children, item_dict, is_last=True, prefix="", is_root=True)

        # Get linked items (separate from the tree structure)
        linked_items = conn.execute("""
            SELECT il.item1_id, il.item2_id, i1.title as item1_title, i2.title as item2_title,
                   i1.type as item1_type, i2.type as item2_type,
                   i1.creation_date as item1_creation_date, i2.creation_date as item2_creation_date
            FROM item_links il
            JOIN items i1 ON (il.item1_id = i1.id)
            JOIN items i2 ON (il.item2_id = i2.id)
            WHERE il.item1_id = ? OR il.item2_id = ?
        """, (item_id, item_id)).fetchall()

        # Print linked items in consistent format
        if linked_items:
            print(Fore.CYAN + f"\nLinked items:" + Style.RESET_ALL)
            for link in linked_items:
                # Determine which item is the other one (not the one we're viewing)
                if link[0] == item_id:  # item1_id is the current item
                    other_item_id = link[1]
                    other_item_title = link[3]  # item2_title
                    other_item_type = link[5]   # item2_type
                    other_creation_date = link[7] # item2_creation_date
                else:  # item2_id is the current item
                    other_item_id = link[0]
                    other_item_title = link[2]  # item1_title
                    other_item_type = link[4]   # item1_type
                    other_creation_date = link[6] # item1_creation_date

                # Format the linked item consistently
                print(Fore.CYAN + f"  - {other_item_title} (id:{other_item_id}, type:{other_item_type}) ({other_creation_date})" + Style.RESET_ALL)
        else:
            print(Fore.CYAN + f"\nNo linked items found." + Style.RESET_ALL)


def add_item_with_parent(title, item_type, parent_id):
    """Add an item with a parent"""
    return add_item(title, item_type, parent_id)

def search_tasks_and_notes(search_text):
    """Search for tasks and notes containing the search text (supports wildcards: * and ?)"""
    # Convert user-friendly wildcards to SQL LIKE patterns
    # * -> % (matches any sequence of characters)
    # ? -> _ (matches any single character)
    sql_search_text = search_text.replace("*", "%").replace("?", "_")

    with sqlite3.connect(DB_FILE) as conn:
        # Search in items (title column)
        items = conn.execute(
            """
            SELECT id, type, title, creation_date, pid
            FROM items
            WHERE title LIKE ?
            ORDER BY creation_date ASC,id ASC
            """,
            (f"%{sql_search_text}%",)
        ).fetchall()

    # Group by creation_date
    grouped = defaultdict(lambda: {"items": []})

    # Add items to grouped dict
    for item in items:
        grouped[item[3]]["items"].append(item)  # item[3] is creation_date

    return grouped, items

def display_search_results(grouped):
    """Display search results in the same format as the default journal view"""
    has_results = any(grouped[day]["items"] for day in grouped)

    if not has_results:
        print("No matching tasks or notes found.")
        return

    # Get all items to properly display them
    with sqlite3.connect(DB_FILE) as conn:
        all_items = conn.execute(
            "SELECT id, type, title, creation_date, pid FROM items ORDER BY creation_date ASC,id ASC"
        ).fetchall()

    for day in sorted(grouped.keys()):
        items_for_day = grouped[day]["items"]

        if items_for_day:
            print()
            print(format_date_with_day(day))

            # Build and print item tree for this day
            if items_for_day:
                root_items, children, item_dict = build_item_tree(items_for_day)
                for i, root_item in enumerate(root_items):
                    is_last = (i == len(root_items) - 1)
                    print_item_tree(root_item, children, item_dict, is_last, "", is_root=True)

def show_completed_tasks():
    with sqlite3.connect(DB_FILE) as conn:
        items = conn.execute("""
            SELECT i.id, i.type, i.title, i.creation_date, i.pid
            FROM items i
            JOIN todo_info t ON i.id = t.item_id
            WHERE i.type = 'todo' AND t.status = 'done' AND t.completion_date IS NOT NULL
            ORDER BY t.completion_date ASC, i.id ASC
        """).fetchall()

        # Group items by completion date
        grouped = defaultdict(list)
        for item in items:
            # Get the completion date for this item
            with sqlite3.connect(DB_FILE) as temp_conn:
                completion_date = temp_conn.execute(
                    "SELECT completion_date FROM todo_info WHERE item_id=?",
                    (item[0],)
                ).fetchone()
                
            if completion_date and completion_date[0]:
                completion_date_str = completion_date[0]
                grouped[completion_date_str].append(item)

    # Display items grouped by completion date
    for completion_date in sorted(grouped.keys()):
        print()
        print(format_date_with_day(completion_date))

        # Build and print item tree for this completion date
        date_items = grouped[completion_date]
        root_items, children, item_dict = build_item_tree(date_items)
        for i, root_item in enumerate(root_items):
            is_last = (i == len(root_items) - 1)
            print_item_tree(root_item, children, item_dict, is_last, "", is_root=True)

def show_tasks_by_status():
    with sqlite3.connect(DB_FILE) as conn:
        # Get only incomplete root tasks to build hierarchies from
        # A root task is defined as: a task which does not have any parent or which does not have a task as parent
        # So we want tasks where pid IS NULL OR where the parent item has type 'note'
        root_items = conn.execute("""
            SELECT i.id, i.type, i.title, i.creation_date, i.pid
            FROM items i
            LEFT JOIN todo_info t ON i.id = t.item_id
            WHERE i.type = 'todo' 
              AND (i.pid IS NULL OR i.pid IN (SELECT id FROM items WHERE type = 'note'))
              AND (t.status != 'done' OR t.status IS NULL)
            ORDER BY
                CASE t.status
                    WHEN 'todo' THEN 1
                    WHEN 'doing' THEN 2
                    WHEN 'waiting' THEN 3
                    ELSE 4
                END,
                t.due_date ASC, i.id ASC
        """).fetchall()

    # Group root items by their status
    grouped_by_status = defaultdict(list)
    for item in root_items:
        item_id = item[0]
        # Get the status for this item
        with sqlite3.connect(DB_FILE) as temp_conn:
            status_result = temp_conn.execute(
                "SELECT status FROM todo_info WHERE item_id=?",
                (item_id,)
            ).fetchone()
        
        status = status_result[0] if status_result else 'todo'
        grouped_by_status[status].append(item)

    # Display items grouped by status in the order: Todo, Doing, Waiting, Done
    status_order = ['todo', 'doing', 'waiting', 'done']
    status_labels = {'todo': 'Todo', 'doing': 'Doing', 'waiting': 'Waiting', 'done': 'Done'}

    for status in status_order:
        if status in grouped_by_status and grouped_by_status[status]:
            print(f"\n{status_labels[status]}")

            # For each root item of this status, get its complete hierarchy and print it
            status_root_items = grouped_by_status[status]
            for i, root_item in enumerate(status_root_items):
                is_last = (i == len(status_root_items) - 1)

                # Get complete hierarchy under this root item (including completed children)
                with sqlite3.connect(DB_FILE) as temp_conn:
                    all_descendants = temp_conn.execute("""
                        WITH RECURSIVE item_tree AS (
                            -- Base case: the root item itself
                            SELECT id, type, title, creation_date, pid
                            FROM items
                            WHERE id = ?

                            UNION ALL
                            -- Recursive case: all child items (including completed ones)
                            SELECT i.id, i.type, i.title, i.creation_date, i.pid
                            FROM items i
                            JOIN item_tree it ON i.pid = it.id
                        )
                        SELECT id, type, title, creation_date, pid
                        FROM item_tree
                        ORDER BY id ASC
                    """, (root_item[0],)).fetchall()  # root_item[0] is id

                # Build tree structure for this root with all its descendants
                all_root_nodes, all_children, all_item_dict = build_item_tree(all_descendants)

                # Print each root node in the hierarchy (should be just the main root we started with)
                for j, item_node in enumerate(all_root_nodes):
                    item_is_last = (j == len(all_root_nodes) - 1) and is_last
                    print_item_tree(item_node, all_children, all_item_dict, item_is_last, "", is_root=True)

# --- CLI Parser ---

def main():
    # Require database file to be specified in command line arguments
    if "-d" not in sys.argv or sys.argv.index("-d") + 1 >= len(sys.argv):
        print("Error: Database file must be specified with -d <database_file>")
        print("Example: python jrnl_app.py -d jrnl.db help")
        sys.exit(1)
    
    # Find and extract the database file from the arguments
    global DB_FILE
    d_index = sys.argv.index("-d")
    if d_index + 1 < len(sys.argv):
        db_filename = sys.argv[d_index + 1]
        # Remove -d and the filename from sys.argv so they're not processed as commands
        sys.argv = sys.argv[:d_index] + sys.argv[d_index+2:]
        
        # If the filename doesn't contain a path separator, put it in the home directory
        if os.sep not in db_filename and "/" not in db_filename and "\\" not in db_filename:
            home_dir = os.path.expanduser("~")
            DB_FILE = os.path.join(home_dir, db_filename)
        else:
            DB_FILE = db_filename
    else:
        print("Error: Database file must be specified after -d flag")
        sys.exit(1)
    
    # Initialize database with the specified DB_FILE
    init_db()
    
    # Now parse the actual command from the modified sys.argv
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
    elif cmd in ["show"] and rest and len(rest) >= 1 and rest[0].isdigit():
        # New consolidated command: j show <id>
        item_id = int(rest[0])
        show_item_details(item_id)
    elif cmd == "edit" and rest and len(rest) >= 1 and rest[0].isdigit():
        # New consolidated command: j edit <id> [-text <text>] [-due <date>] [-recur <pattern>] [-link <id>[,<id>,...]] [-unlink <id>[,<id>,...]] [-parent <id>|none]
        item_id = int(rest[0])
        options = rest[1:] if len(rest) > 1 else []  # Remaining args are options
        
        # Parse options for editing
        new_text = None
        new_due = None
        recur_pattern = None
        link_ids = []
        unlink_ids = []
        new_parent_id = None  # For changing parent
        
        i = 0
        while i < len(options):
            if options[i] == "-text" and i + 1 < len(options):
                new_text = options[i + 1]
                i += 2
            elif options[i] == "-due" and i + 1 < len(options):
                new_due = parse_due(options[i + 1])
                i += 2
            elif options[i] == "-recur" and i + 1 < len(options):
                recur_pattern = options[i + 1]
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
            elif options[i] == "-parent" and i + 1 < len(options):
                # Parse parent ID or 'none'
                parent_value = options[i + 1]
                if parent_value.lower() == 'none':
                    new_parent_id = None
                elif parent_value.isdigit():
                    new_parent_id = int(parent_value)
                i += 2
            else:
                # Skip unknown option
                i += 1
        
        # Get the item type to determine what operations are valid
        with sqlite3.connect(DB_FILE) as conn:
            item = conn.execute("SELECT type FROM items WHERE id=?", (item_id,)).fetchone()
        
        if not item:
            print(f"Error: Item with ID {item_id} does not exist")
            return
        
        item_type = item[0]  # 'note' or 'todo'
        
        # Perform operations
        if new_text:
            if item_type == 'note':
                edit_note(item_id, new_text)
            else:  # task
                edit_task(item_id, new_text)
        
        if new_due and item_type == 'todo':
            with sqlite3.connect(DB_FILE) as conn:
                # Check if a record exists in todo_info, if not create one
                existing = conn.execute(
                    "SELECT item_id FROM todo_info WHERE item_id=?",
                    (item_id,)
                ).fetchone()

                if not existing:
                    # Create a new record with default values
                    conn.execute(
                        "INSERT INTO todo_info (item_id, status, due_date) VALUES (?, 'todo', ?)",
                        (item_id, datetime.now().date().strftime("%Y-%m-%d"))
                    )

                conn.execute(
                    "UPDATE todo_info SET due_date=? WHERE item_id=?",
                    (new_due.strftime("%Y-%m-%d"), item_id)
                )
                print(f"Updated due date for {item_type} {item_id} to {new_due.strftime('%Y-%m-%d')}")
        
        if recur_pattern and item_type == 'todo':
            # Validate and set recur pattern
            if set_task_recur([item_id], recur_pattern):
                print(f"Set recur pattern '{recur_pattern}' for task {item_id}")
        
        if new_parent_id is not None:
            # Update the parent ID (pid) for the item
            with sqlite3.connect(DB_FILE) as conn:
                # Check if the new parent exists (if not None)
                if new_parent_id is not None:
                    parent_exists = conn.execute(
                        "SELECT id FROM items WHERE id=?", (new_parent_id,)
                    ).fetchone()
                    if not parent_exists:
                        print(f"Error: Parent item with ID {new_parent_id} does not exist")
                        return
                
                # Update the parent ID
                conn.execute(
                    "UPDATE items SET pid=? WHERE id=?", (new_parent_id, item_id)
                )
                parent_display = new_parent_id if new_parent_id is not None else "none"
                print(f"Updated parent for item {item_id} to {parent_display}")
        
        if link_ids:
            for link_id in link_ids:
                link_items(item_id, link_id)
        
        if unlink_ids:
            for unlink_id in unlink_ids:
                unlink_notes(item_id, unlink_id)
    elif cmd in ["task", "note"]:  # Handle new consolidated commands
        # Check if the first argument is a numeric ID (for editing/showing)
        if rest and len(rest) >= 1 and rest[0].isdigit():
            # Handle "j note <id> [options...]" or "j task <id> [options...]" (edit/show commands)
            item_type = cmd  # "note" or "task"
            item_id = int(rest[0])
            options = rest[1:] if len(rest) > 1 else []  # Remaining args are options

            if item_type == "note":
                # Parse options for note editing (no more showing, removing -task option)
                # Note editing functionality has been moved to 'j edit <id>' command
                print(f"The 'j note {item_id}' command for editing is deprecated. Use 'j edit {item_id}' instead.")
            elif item_type == "task":
                # Parse options for task editing (no more showing, removing -note option)
                # Task editing functionality has been moved to 'j edit <id>' command
                print(f"The 'j task {item_id}' command for editing is deprecated. Use 'j edit {item_id}' instead.")
        else:
            # Handle "j note <text> [-link <id>[,<id>,...]]" or "j task [@<pid>] <text> [-due XX] [-recur XX]" (add new commands)
            sub_cmd = cmd  # "note" or "task"
            cmd_args = rest

            if sub_cmd == "note":  # Handle "j note <text> [-link <id>[,<id>,...]]" (add new note)
                # Check if the first argument is a parent note ID in the format @<number>
                parent_note_id = None
                start_idx = 0

                if cmd_args and cmd_args[0].startswith("@") and cmd_args[0][1:].isdigit():
                    parent_note_id = int(cmd_args[0][1:])  # Remove @ and convert to int
                    start_idx = 1  # Skip the first argument as it's the parent ID

                # Find the note text (everything before the first option flag)
                note_text = []
                link_ids = []
                i = start_idx
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
                    # Check if parent_note_id exists if provided
                    if parent_note_id is not None:
                        with sqlite3.connect(DB_FILE) as conn:
                            cursor = conn.execute("SELECT id FROM items WHERE id = ?", (parent_note_id,))
                            if not cursor.fetchone():
                                print(f"Error: Parent item with ID {parent_note_id} does not exist")
                                return

                    # Add the note with parent if specified
                    note_ids = add_note([], text, parent_note_id)

                    # Then create links if specified
                    if link_ids and note_ids:
                        # Use the note ID from the add_note function
                        note_id = note_ids[0]  # Since we're adding one note, get the first ID
                        for link_id in link_ids:
                            link_items(note_id, link_id)
                else:
                    print("Error: Please provide note text")
            elif sub_cmd == "task":
                # Check if the first argument is a parent item ID in the format @<number>
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
                            due_kw = cmd_args[i + 1]
                            # Remove @ symbol if present (for due dates like @tomorrow, @2025-12-25)
                            if due_kw.startswith("@"):
                                due_kw = due_kw[1:]
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
                            cursor = conn.execute("SELECT id FROM items WHERE id = ?", (parent_id,))
                            if not cursor.fetchone():
                                print(f"Error: Parent item with ID {parent_id} does not exist")
                                return

                    # For child tasks, recurrence should be ignored
                    if parent_id is not None and recur_pattern is not None:
                        print(f"Warning: Recurrence pattern '{recur_pattern}' is ignored for child tasks")
                        recur_pattern = None  # Don't allow recurrence for child tasks

                    # Add the task with due date if specified
                    if due_date:
                        # Create a temporary task with due date
                        today = datetime.now().date().strftime("%Y-%m-%d")
                        item_id = add_item_with_details(text, "todo", due_date.strftime("%Y-%m-%d"), parent_id)
                        print(f"Added task with id {item_id}")
                    else:
                        # Add task without due date (default to today)
                        if recur_pattern:  # Need to call add_item with proper due date handling
                            # Use today as default due date when recurrence is specified but due date isn't
                            today = datetime.now().date()
                            formatted_today = today.strftime("%Y-%m-%d")
                            item_id = add_item_with_details(text, "todo", formatted_today, parent_id)
                            print(f"Added task with id {item_id}")
                        else:
                            # Call original add_task function for simple tasks but with parent ID
                            item_id = add_item(text, "todo", parent_id)
                            print(f"Added task with id {item_id}")
                else:
                    print("Error: Please provide task text")

    elif cmd in ["page"]:
        # The old 'j page|p' command has been removed
        print("Command 'j page|p' has been removed. Use 'j help' to see available commands.")
    elif cmd in ["task"] and rest:  # Handle task commands
        # The old task command (j task <text>) has been removed
        print("Command 'j task <text>' has been removed. Use 'j help' to see available commands.")
    elif cmd in ["note"] and rest:  # Handle note commands with arguments
        # Check if first argument is a single digit/number (for note lookup)
        if len(rest) == 1 and rest[0].isdigit():
            # The old note command (j note <id>) has been removed
            print("Command 'j note <id>' has been removed. Use 'j help' to see available commands.")
        else:
            # The old note command (j note <text>) and edit command (j note <id> edit) have been removed
            print("Commands 'j note <text>' and 'j note <id> edit' have been removed. Use 'j help' to see available commands.")
    elif cmd in ["start", "restart", "waiting", "done"] and len(rest) >= 1:
        # New consolidated command: j <start|restart|waiting|done> <id>[,<id>,...]
        ids_str = rest[0]
        ids = [int(id_str) for id_str in ids_str.split(",") if id_str.isdigit()]

        if cmd == "start":
            update_task_status(ids, "doing")
        elif cmd == "restart":
            update_task_status(ids, "todo")
        elif cmd == "waiting":
            update_task_status(ids, "waiting")
        elif cmd == "done":
            if not ids:
                print("Error: Please provide valid task IDs")
                return
            update_task_status(ids, "done")



    elif cmd == "rm":
        if rest and len(rest) >= 1:
            # New simplified syntax: j rm <id>[,<id>,...] (no need to specify note/task)
            ids_str = rest[0]
            id_parts = ids_str.split(",")
            
            # Parse the IDs (should be pure numbers)
            ids = [int(id_str) for id_str in id_parts if id_str.isdigit()]

            if not ids:
                print("Error: Please provide valid item IDs")
                return

            # Group IDs by type to make deletion more efficient and count items
            note_ids = []
            task_ids = []
            invalid_ids = []
            
            with sqlite3.connect(DB_FILE) as conn:
                for item_id in ids:
                    item = conn.execute("SELECT type FROM items WHERE id=?", (item_id,)).fetchone()
                    if item:
                        item_type = item[0]
                        if item_type == 'note':
                            note_ids.append(item_id)
                        elif item_type == 'todo':
                            task_ids.append(item_id)
                        else:
                            print(f"Error: Unknown item type for ID {item_id}")
                            invalid_ids.append(item_id)
                    else:
                        print(f"Error: Item with ID {item_id} does not exist")
                        invalid_ids.append(item_id)

            # Determine total count of items to be deleted
            total_items = len(note_ids) + len(task_ids)
            
            if total_items == 0:
                print("No valid items to delete.")
                return
            
            # Ask for confirmation before deletion
            print(f"Warning: You are about to delete {total_items} item(s). This action cannot be undone.")
            confirmation = input("Type 'yes' to confirm deletion: ").strip().lower()
            
            if confirmation != 'yes':
                print("Deletion cancelled.")
                return

            # Use the unified delete_item function with all valid IDs
            delete_item(ids)
        else:
            print("Old syntax 'j rm t<id>[,n<id>...] has been removed. Use 'j help' to see available commands.")
    elif cmd in ["task"]:
        show_task()
    elif cmd in ["note"]:
        show_note()
    elif cmd in ["list", "ls"] and len(rest) >= 1:
        # New consolidated command: j list/ls <page|note|task> <optional: due|status|done>
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
            print("Error: Invalid syntax. Use 'j ls <page|note|task>' or 'j ls task <due|status|done>'")
    elif cmd == "search":
        if rest:
            search_text = " ".join(rest)
            grouped, items = search_tasks_and_notes(search_text)
            display_search_results(grouped)
        else:
            print("Error: Please provide search text")
    elif cmd == "clear":
        if rest and rest[0] == "all":
            clear_all()
        else:
            print("Error: Use 'j clear all' to clear all data from the database")
    elif cmd == "help":
        print("""j - Command Line Journal and Task Manager

USAGE:
    j -d <database_file> [command] [arguments...]
    
OPTIONS:
    -d <database_file>
        Specify the database file to use (required). The file will be created in your home directory if no path is specified.

COMMANDS:
    j
        Show tasks grouped by due date (default view) (Overdue / Due Today / Due Tomorrow / This Week / This Month / Future)
    j note [@<pid>] <text>
        Add a new root note. If <pid> is given then add a note under parent note with ID <pid>
    j task [@<pid>] <text> [-due <YYYY-MM-DD|today|tomorrow|eow|eom|eoy>] [-recur <Nd|Nw|Nm|Ny>]
        Add a new root task if no <pid> is given else add a new task under parent task with ID <pid>, with optional due date and recurrence
    j edit <id> [-text <text>] [-due <date>] [-recur <pattern>] [-link <id>[,<id>,...]] [-unlink <id>[,<id>,...]] [-parent <id>|none]
        Edit any item (note or task) with all available options
    j show <id>
        Show specific note or task details by ID
    j rm <id>[,<id>,...]
        Delete notes or tasks by ID (no need to specify note or task)
    j ls <page|note|task> [due|status|done]
        List items with optional grouping
    j <start|restart|waiting|done> <id>[,<id>,...]
        Task status operations
    j search <text>
        Search for tasks and notes containing text (supports wildcards: * = any chars, ? = single char)
    j clear all
        Remove all data from the database (requires confirmation)
    j help
        Show this help message
""")
    else:
        print(f"Error: Unknown command '{cmd}'. Use 'j help' to see available commands.")

if __name__ == "__main__":
    main()