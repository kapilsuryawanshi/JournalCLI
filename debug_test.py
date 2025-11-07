import sqlite3
import tempfile
import os
import sys
from datetime import datetime, timedelta
from io import StringIO
from contextlib import redirect_stdout
import argparse

# Add the project directory to sys.path so we can import jrnl_app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jrnl_app

# Setup temporary database
DB_FILE = tempfile.mktemp()
jrnl_app.DB_FILE = DB_FILE
jrnl_app.init_db()

# Create multiple tasks: some completed root tasks, some incomplete root tasks, and child tasks
# Root task 1 - incomplete
jrnl_app.add_task(["Incomplete root task"])

# Root task 2 - completed
jrnl_app.add_task(["Completed root task"])

with sqlite3.connect(DB_FILE) as conn:
    tasks = conn.execute("SELECT id, title FROM tasks ORDER BY creation_date").fetchall()
    print(f"Initial tasks: {tasks}")
    incomplete_task_id = tasks[0][0]
    completed_task_id = tasks[1][0]

# Complete the second task
jrnl_app.update_task_status([completed_task_id], "done")

# Add a child task under the completed root task (need to use direct DB insertion)
today = datetime.now().date().strftime("%Y-%m-%d")
with sqlite3.connect(DB_FILE) as conn:
    cursor = conn.execute(
        "INSERT INTO tasks (title,status,creation_date,due_date,pid) VALUES (?,?,?,?,?)",
        ("Child task under completed root", "todo", today, today, completed_task_id)
    )
    child_task_completed_id = cursor.lastrowid
    print(f"Added task with id {child_task_completed_id}")

# Add a child task under the incomplete root task (need to use direct DB insertion)
with sqlite3.connect(DB_FILE) as conn:
    cursor = conn.execute(
        "INSERT INTO tasks (title,status,creation_date,due_date,pid) VALUES (?,?,?,?,?)",
        ("Child task under incomplete root", "todo", today, today, incomplete_task_id)
    )
    child_task_incomplete_id = cursor.lastrowid
    print(f"Added task with id {child_task_incomplete_id}")

# Check what's in the database now
with sqlite3.connect(DB_FILE) as conn:
    all_tasks = conn.execute("SELECT id, title, status, pid, parent_note_id FROM tasks ORDER BY id").fetchall()
    print(f"All tasks in DB: {all_tasks}")

# Check what our exclusion logic would find
with sqlite3.connect(DB_FILE) as conn:
    # First, find all completed root tasks
    completed_roots = conn.execute("""
        SELECT id FROM tasks 
        WHERE status = 'done' AND pid IS NULL AND parent_note_id IS NULL
    """).fetchall()
    
    print(f"Completed root tasks: {completed_roots}")
    
    completed_root_ids = [str(row[0]) for row in completed_roots]
    print(f"Completed root IDs: {completed_root_ids}")
    
    # Find all descendants of these completed roots using recursive CTE
    if completed_root_ids:
        exclude_query = """
            WITH RECURSIVE task_descendants AS (
                -- Base case: the completed root tasks themselves
                SELECT id FROM tasks WHERE id IN ({})
                
                UNION ALL
                -- Recursive case: child tasks of tasks in the descendants
                SELECT t.id 
                FROM tasks t
                JOIN task_descendants td ON t.pid = td.id
            )
            SELECT id FROM task_descendants
        """.format(",".join("?" * len(completed_root_ids)))
        
        excluded_task_ids = conn.execute(exclude_query, completed_root_ids).fetchall()
        print(f"Tasks to exclude: {excluded_task_ids}")
        excluded_ids_set = set(row[0] for row in excluded_task_ids)
    else:
        excluded_ids_set = set()

    # Get all tasks 
    all_tasks = conn.execute(
        "SELECT id,title,status,creation_date,due_date,completion_date,recur,pid FROM tasks ORDER BY id ASC"
    ).fetchall()
    print(f"All tasks before filter: {[task[0] for task in all_tasks]}")
    
    # Filter out tasks that are descendants of completed root tasks
    tasks = [task for task in all_tasks if task[0] not in excluded_ids_set]
    print(f"Tasks after filter: {[task[0] for task in tasks]}")

# Now test the actual show function
print("\n--- show_due output ---")
f = StringIO()
with redirect_stdout(f):
    jrnl_app.show_due()
output = f.getvalue()
print(output)