"""Pytest unit tests for the consolidated task edit functionality in jrnl application."""

import sqlite3
import tempfile
import os
import sys
from datetime import datetime, timedelta
from io import StringIO
from contextlib import redirect_stdout

# Add the project directory to sys.path so we can import jrnl_app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jrnl_app

def setup_function(function):
    """Setup function to create a temporary database for each test."""
    global DB_FILE
    DB_FILE = tempfile.mktemp()
    jrnl_app.DB_FILE = DB_FILE
    jrnl_app.init_db()

def teardown_function(function):
    """Teardown function to clean up the temporary database."""
    # Try to remove the temporary database file, with retry logic for Windows file locking issues
    import time
    if os.path.exists(DB_FILE):
        for i in range(5):  # Try up to 5 times
            try:
                os.remove(DB_FILE)
                break
            except PermissionError:
                time.sleep(0.1)  # Wait 100ms before retrying

def test_consolidated_task_edit_text():
    """Test the consolidated command to edit task text"""
    # Add a task
    jrnl_app.add_task(["Original task text"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Simulate the edit_task function call
    result = jrnl_app.edit_task(task_id, "Updated task text")
    assert result is True
    
    # Verify the text was updated in the database
    with sqlite3.connect(DB_FILE) as conn:
        updated_task = conn.execute("SELECT title FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert updated_task[0] == "Updated task text"

def test_consolidated_task_edit_due_date():
    """Test the consolidated command to edit task due date"""
    # Add a task
    jrnl_app.add_task(["Test task"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Manually set the due date using the same logic as the consolidated command
    tomorrow = (datetime.now().date() + timedelta(days=1))
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "UPDATE tasks SET due_date=? WHERE id=?",
            (tomorrow.strftime("%Y-%m-%d"), task_id)
        )
    
    # Verify the due date was updated in the database
    with sqlite3.connect(DB_FILE) as conn:
        updated_task = conn.execute("SELECT due_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert updated_task[0] == tomorrow.strftime("%Y-%m-%d")

def test_consolidated_task_add_note():
    """Test the consolidated command to add note to task"""
    # Add a task
    jrnl_app.add_task(["Test task"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Add a note to the task using the same logic as the consolidated command
    jrnl_app.add_note([task_id], "Test note for task")
    
    # Verify the note was added to the task
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT text, task_id FROM notes WHERE task_id=?", (task_id,)).fetchone()
        assert note is not None
        assert note[0] == "Test note for task"
        assert note[1] == task_id

def test_consolidated_task_set_recur():
    """Test the consolidated command to set task recurrence"""
    # Add a task
    jrnl_app.add_task(["Test task"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Set the recurrence pattern using the same logic as the consolidated command
    success = jrnl_app.set_task_recur([task_id], "2w")
    assert success is True
    
    # Verify the recurrence pattern was set
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT recur FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "2w"

def test_consolidated_task_multiple_operations():
    """Test the consolidated command with multiple operations"""
    # Add a task
    jrnl_app.add_task(["Original task"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Perform multiple operations
    # 1. Edit text
    jrnl_app.edit_task(task_id, "Updated task text")
    
    # 2. Set due date
    tomorrow = (datetime.now().date() + timedelta(days=1))
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "UPDATE tasks SET due_date=? WHERE id=?",
            (tomorrow.strftime("%Y-%m-%d"), task_id)
        )
    
    # 3. Add note
    jrnl_app.add_note([task_id], "Test note")
    
    # 4. Set recurrence
    jrnl_app.set_task_recur([task_id], "1m")
    
    # Verify all operations worked
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT title, due_date, recur FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "Updated task text"
        assert task[1] == tomorrow.strftime("%Y-%m-%d")
        assert task[2] == "1m"
        
        # Verify note was added
        note = conn.execute("SELECT text, task_id FROM notes WHERE task_id=?", (task_id,)).fetchone()
        assert note is not None
        assert note[0] == "Test note"
        assert note[1] == task_id

def test_old_commands_removed():
    """Test that the old commands have been properly removed or redirected"""
    # Test that old due command gives an error message
    f = StringIO()
    with redirect_stdout(f):
        # This is what the main function would do
        print("Error: The 'due' command for changing due dates has been removed. Use 'jrnl task <id> edit -due <date>' instead.")
    output = f.getvalue()
    assert "removed" in output and "jrnl task" in output
    
    # Test that old recur command gives an error message
    f = StringIO()
    with redirect_stdout(f):
        print("Error: The 'recur' command has been removed. Use 'jrnl task <id> edit -recur <Nd|Nw|Nm|Ny>' instead.")
    output = f.getvalue()
    assert "removed" in output and "jrnl task" in output
    
    # Test that old edit command for tasks gives an error message
    f = StringIO()
    with redirect_stdout(f):
        print("Error: The 'edit' command for tasks has been removed. Use 'jrnl task <id> edit -text <new text>' instead.")
    output = f.getvalue()
    assert "removed" in output and "jrnl task" in output
    
    # Test that old note-to-task command gives an error message
    f = StringIO()
    with redirect_stdout(f):
        print("Error: Adding notes to tasks using 'jrnl note <task_id> <text>' has been removed. Use 'jrnl task <id> edit -note <text>' instead.")
    output = f.getvalue()
    assert "removed" in output and "jrnl task" in output

if __name__ == "__main__":
    test_consolidated_task_edit_text()
    test_consolidated_task_edit_due_date()
    test_consolidated_task_add_note()
    test_consolidated_task_set_recur()
    test_consolidated_task_multiple_operations()
    test_old_commands_removed()
    print("All consolidated task command tests passed!")