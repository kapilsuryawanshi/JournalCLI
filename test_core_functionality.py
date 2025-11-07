import tempfile
import sys
import os
from datetime import datetime
from io import StringIO
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jrnl_app

# Setup temporary database
DB_FILE = tempfile.mktemp()
jrnl_app.DB_FILE = DB_FILE
jrnl_app.init_db()

print('Testing the core functionality: hiding completed root tasks')

# Create a task and complete it
jrnl_app.add_task(['Completed task'])

# Create another task that remains incomplete
jrnl_app.add_task(['Incomplete task'])

import sqlite3
with sqlite3.connect(DB_FILE) as conn:
    tasks = conn.execute('SELECT id, title FROM tasks ORDER BY creation_date').fetchall()
    print('Created tasks:', tasks)
    
    completed_task_id = tasks[0][0]  # First task
    incomplete_task_id = tasks[1][0]  # Second task

# Mark first task as completed
jrnl_app.update_task_status([completed_task_id], 'done')
print('Marked first task as completed')

# Test show_due - should only show incomplete task
f = StringIO()
with redirect_stdout(f):
    jrnl_app.show_due()
show_due_output = f.getvalue()
print('show_due() output:')
print(show_due_output)

print('Check if completed task is hidden:')
print("'Completed task' in output:", 'Completed task' in show_due_output)
print("'Incomplete task' in output:", 'Incomplete task' in show_due_output)