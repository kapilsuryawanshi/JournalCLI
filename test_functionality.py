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

# Test basic functionality step by step
print("Step 1: Add a task")
jrnl_app.add_task(['Test task'])

# Get the task ID
import sqlite3
with sqlite3.connect(DB_FILE) as conn:
    tasks = conn.execute('SELECT id FROM tasks WHERE title=?', ("Test task",)).fetchall()
    print("Tasks found:", tasks)
    
    if tasks:
        task_id = tasks[0][0]
        print("Task ID:", task_id)
        
        print("Step 2: Add a note to this task")
        note_ids = jrnl_app.add_note([task_id], 'Test note for task')
        print('Note added with id(s):', note_ids)
        
        # Verify the note was added in the database
        notes = conn.execute('SELECT id, text, task_id FROM notes WHERE text=?', ("Test note for task",)).fetchall()
        print('Notes found in DB:', notes)
        
        print("Step 3: Show all notes")
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.show_note()
        note_output = f.getvalue()
        print('Show note output:')
        print(repr(note_output))
        
        print("Step 4: Show all journal entries")
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.show_journal()
        journal_output = f.getvalue()
        print('Show journal output:')
        print(repr(journal_output))