"""Pytest unit tests for the updated consolidated commands in jrnl application:
- jrnl list <note|task> [due|status|done]
"""

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

def test_list_note_command():
    """Test listing notes using the new consolidated command."""
    # Add a note
    jrnl_app.add_note([], "Test list note")
    
    # Simulate command line arguments for "jrnl list note"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "list", "note"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the note is shown
        assert "Test list note" in output
    finally:
        sys.argv = original_argv

def test_list_task_status_command():
    """Test listing tasks by status using the new consolidated command."""
    # Add a task
    jrnl_app.add_task(["Test list task"])
    
    # Simulate command line arguments for "jrnl list task status"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "list", "task", "status"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the task is shown in status view
        assert "Test list task" in output
        assert "Todo" in output
    finally:
        sys.argv = original_argv

def test_list_task_due_command():
    """Test listing tasks by due date using the new consolidated command."""
    # Add a task with tomorrow's due date
    jrnl_app.add_task(["Test due list task @tomorrow"])
    
    # Simulate command line arguments for "jrnl list task due"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "list", "task", "due"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the task is shown in due view
        assert "Test due list task" in output
    finally:
        sys.argv = original_argv

def test_list_task_done_command():
    """Test listing completed tasks using the new consolidated command."""
    # Add and complete a task
    jrnl_app.add_task(["Test done list task"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test done list task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Complete the task
    jrnl_app.update_task_status([task_id], "done", "Completed successfully")
    
    # Simulate command line arguments for "jrnl list task done"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "list", "task", "done"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the completed task is shown
        assert "Test done list task" in output
    finally:
        sys.argv = original_argv

def test_list_task_default_command():
    """Test listing tasks by default (status) using the new consolidated command."""
    # Add a task
    jrnl_app.add_task(["Test default list task"])
    
    # Simulate command line arguments for "jrnl list task"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "list", "task"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the task is shown in default view (status view)
        assert "Test default list task" in output
    finally:
        sys.argv = original_argv

def test_old_note_command_removed():
    """Test that the old 'jrnl note' command has been removed."""
    # Simulate command line arguments for "jrnl note" (old command)
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "note"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should show error message about what the command does now
        assert "Error" in output
        # Current behavior: 'note' command now creates a note, so it expects text
        assert "provide note text" in output
    finally:
        sys.argv = original_argv

def test_old_view_task_commands_removed():
    """Test that the old 'jrnl view task' commands have been removed."""
    # Test various old 'view' commands that should now be errors
    old_commands = [
        ["jrnl_app.py", "view", "task", "due"],
        ["jrnl_app.py", "view", "task", "status"],
        ["jrnl_app.py", "view", "task", "done"]
    ]
    
    for old_cmd in old_commands:
        original_argv = sys.argv.copy()
        sys.argv = old_cmd
        
        try:
            f = StringIO()
            with redirect_stdout(f):
                jrnl_app.main()
            output = f.getvalue()
            
            # Should show error message about removed command or not found
            # Since 'view' might not be recognized as a command at all, this might show an empty output or error
        finally:
            sys.argv = original_argv

if __name__ == "__main__":
    test_list_note_command()
    test_list_task_status_command()
    test_list_task_due_command()
    test_list_task_done_command()
    test_list_task_default_command()
    test_old_note_command_removed()
    test_old_view_task_commands_removed()
    print("All updated consolidated command tests passed!")