"""Pytest unit tests for the new 'j list task today' command in jrnl application."""

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

def test_list_task_today_command():
    """Test the 'j list task today' command functionality."""
    # Add tasks with different due dates
    # Add an overdue task (yesterday)
    yesterday = (datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO items (title, status, creation_date, due_date, pid) VALUES (?, ?, ?, ?, ?)",
            ("Overdue task", "todo", yesterday, yesterday, None)
        )
    
    # Add a task due today
    today = datetime.now().date().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO items (title, status, creation_date, due_date, pid) VALUES (?, ?, ?, ?, ?)",
            ("Today task", "todo", today, today, None)
        )
    
    # Add a task due tomorrow
    tomorrow = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO items (title, status, creation_date, due_date, pid) VALUES (?, ?, ?, ?, ?)",
            ("Tomorrow task", "todo", today, tomorrow, None)
        )
    
    # Add a completed task due today (should not show)
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO items (title, status, creation_date, due_date, completion_date, pid) VALUES (?, ?, ?, ?, ?, ?)",
            ("Completed today task", "done", today, today, today, None)
        )
    
    # Test the 'j list task today' command
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "list", "task", "today"]

    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()

        # Check that the output contains the today and overdue tasks
        assert "Today task" in output
        assert "Overdue task" in output

        # Check that the output does NOT contain the future task (tomorrow) or completed task
        assert "Tomorrow task" not in output
        assert "Completed today task" not in output
    finally:
        sys.argv = original_argv

def test_list_task_today_command_with_completed_tasks():
    """Test the 'j list task today' command excludes completed tasks."""
    today = datetime.now().date().strftime("%Y-%m-%d")
    
    # Add completed task due today
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO items (title, status, creation_date, due_date, completion_date, pid) VALUES (?, ?, ?, ?, ?, ?)",
            ("Completed today task", "done", today, today, today, None)
        )
    
    # Add incomplete task due today
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO items (title, status, creation_date, due_date, pid) VALUES (?, ?, ?, ?, ?)",
            ("Incomplete today task", "todo", today, today, None)
        )
    
    # Test the 'j list task today' command
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "list", "task", "today"]

    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()

        # Check that the incomplete task is shown
        assert "Incomplete today task" in output

        # Check that the completed task is NOT shown
        assert "Completed today task" not in output
    finally:
        sys.argv = original_argv

def test_list_task_today_command_with_no_tasks():
    """Test the 'j list task today' command when there are no today/overdue tasks."""
    today = datetime.now().date().strftime("%Y-%m-%d")
    
    # Add only future tasks
    future_date = (datetime.now().date() + timedelta(days=2)).strftime("%Y-%m-%d")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO items (title, status, creation_date, due_date, pid) VALUES (?, ?, ?, ?, ?)",
            ("Future task", "todo", today, future_date, None)
        )
    
    # Test the 'j list task today' command
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "list", "task", "today"]

    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()

        # Check that the output does NOT contain the future task
        assert "Future task" not in output
    finally:
        sys.argv = original_argv

if __name__ == "__main__":
    test_list_task_today_command()
    test_list_task_today_command_with_completed_tasks()
    test_list_task_today_command_with_no_tasks()
    print("All 'j list task today' command tests passed!")