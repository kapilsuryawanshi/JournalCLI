"""Pytest unit tests for hiding completed root tasks in 'j', 'j ls task due', and 'j ls task status' commands."""

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

def test_show_due_hides_completed_root_tasks():
    """Test that show_due() hides completed root tasks but shows other tasks."""
    # Create multiple tasks: some completed root tasks, some incomplete root tasks, and child tasks
    # Root task 1 - incomplete
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Incomplete root task"])
    output = f.getvalue()
    assert "Added task" in output

    # Root task 2 - completed
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Completed root task"])
    output = f.getvalue()
    assert "Added task" in output

    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute("SELECT id, title FROM tasks ORDER BY creation_date").fetchall()
        assert len(tasks) == 2
        incomplete_task_id = tasks[0][0]
        completed_task_id = tasks[1][0]

    # Complete the second task
    jrnl_app.update_task_status([completed_task_id], "done")

    # Add a child task under the completed root task (to test if it still appears)
    from datetime import datetime as dt
    today = dt.now().date().strftime("%Y-%m-%d")
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title,status,creation_date,due_date,pid) VALUES (?,?,?,?,?)",
            ("Child task under completed root", "todo", today, today, completed_task_id)
        )
        added_task_id = cursor.lastrowid
    f = StringIO()
    with redirect_stdout(f):
        print(f"Added task with id {added_task_id}")
    output = f.getvalue()
    assert "Added task" in output

    # Add a child task under the incomplete root task
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title,status,creation_date,due_date,pid) VALUES (?,?,?,?,?)",
            ("Child task under incomplete root", "todo", today, today, incomplete_task_id)
        )
        added_task_id = cursor.lastrowid
    f = StringIO()
    with redirect_stdout(f):
        print(f"Added task with id {added_task_id}")
    output = f.getvalue()
    assert "Added task" in output

    # Test show_due - capture output to check what's displayed
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_due()
    output = f.getvalue()

    # The completed root task should NOT be displayed
    assert "Completed root task" not in output
    # The incomplete root task SHOULD be displayed
    assert "Incomplete root task" in output
    # The child under the incomplete root SHOULD be displayed
    assert "Child task under incomplete root" in output
    # The child under the completed root should NOT be displayed since the parent is hidden
    assert "Child task under completed root" not in output


def test_show_tasks_by_status_hides_completed_root_tasks():
    """Test that show_tasks_by_status() hides completed root tasks."""
    # Create tasks: some completed root tasks, some incomplete root tasks
    # Root task 1 - incomplete
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Incomplete root task"])
    output = f.getvalue()
    assert "Added task" in output

    # Root task 2 - completed
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Completed root task"])
    output = f.getvalue()
    assert "Added task" in output

    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute("SELECT id, title FROM tasks ORDER BY creation_date").fetchall()
        assert len(tasks) == 2
        incomplete_task_id = tasks[0][0]
        completed_task_id = tasks[1][0]

    # Complete the second task
    jrnl_app.update_task_status([completed_task_id], "done")

    # Add a child task under the completed root task
    from datetime import datetime as dt
    today = dt.now().date().strftime("%Y-%m-%d")
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title,status,creation_date,due_date,pid) VALUES (?,?,?,?,?)",
            ("Child task under completed root", "todo", today, today, completed_task_id)
        )
        added_task_id = cursor.lastrowid
    f = StringIO()
    with redirect_stdout(f):
        print(f"Added task with id {added_task_id}")
    output = f.getvalue()
    assert "Added task" in output

    # Add a child task under the incomplete root task
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title,status,creation_date,due_date,pid) VALUES (?,?,?,?,?)",
            ("Child task under incomplete root", "todo", today, today, incomplete_task_id)
        )
        added_task_id = cursor.lastrowid
    f = StringIO()
    with redirect_stdout(f):
        print(f"Added task with id {added_task_id}")
    output = f.getvalue()
    assert "Added task" in output

    # Test show_tasks_by_status - capture output to check what's displayed
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_tasks_by_status()
    output = f.getvalue()

    # The completed root task should NOT be displayed (in any section)
    assert "Completed root task" not in output
    # The incomplete root task SHOULD be displayed in its appropriate section
    assert "Incomplete root task" in output
    # The child under the incomplete root SHOULD be displayed
    assert "Child task under incomplete root" in output
    # The child under the completed root should NOT be displayed
    assert "Child task under completed root" not in output


def test_show_journal_hides_completed_root_tasks():
    """Test that show_journal() does not display completed root tasks."""
    # Create tasks: some completed root tasks, some incomplete root tasks
    # Root task 1 - incomplete
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Incomplete root task"])
    output = f.getvalue()
    assert "Added task" in output

    # Root task 2 - completed
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Completed root task"])
    output = f.getvalue()
    assert "Added task" in output

    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute("SELECT id, title FROM tasks ORDER BY creation_date").fetchall()
        assert len(tasks) == 2
        incomplete_task_id = tasks[0][0]
        completed_task_id = tasks[1][0]

    # Complete the second task
    jrnl_app.update_task_status([completed_task_id], "done")

    # Add a child task under the completed root task
    from datetime import datetime as dt
    today = dt.now().date().strftime("%Y-%m-%d")
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title,status,creation_date,due_date,pid) VALUES (?,?,?,?,?)",
            ("Child task under completed root", "todo", today, today, completed_task_id)
        )
        added_task_id = cursor.lastrowid
    f = StringIO()
    with redirect_stdout(f):
        print(f"Added task with id {added_task_id}")
    output = f.getvalue()
    assert "Added task" in output

    # Add a child task under the incomplete root task
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title,status,creation_date,due_date,pid) VALUES (?,?,?,?,?)",
            ("Child task under incomplete root", "todo", today, today, incomplete_task_id)
        )
        added_task_id = cursor.lastrowid
    f = StringIO()
    with redirect_stdout(f):
        print(f"Added task with id {added_task_id}")
    output = f.getvalue()
    assert "Added task" in output

    # Test show_journal - capture output to check what's displayed
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_journal()
    output = f.getvalue()

    # The completed root task should NOT be displayed
    assert "Completed root task" not in output
    # The incomplete root task SHOULD be displayed
    assert "Incomplete root task" in output
    # The child under the incomplete root SHOULD be displayed
    assert "Child task under incomplete root" in output
    # The child under the completed root should NOT be displayed
    assert "Child task under completed root" not in output


def test_show_task_hides_completed_root_tasks():
    """Test that show_task() hides completed root tasks."""
    # Create tasks: some completed root tasks, some incomplete root tasks
    # Root task 1 - incomplete
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Incomplete root task"])
    output = f.getvalue()
    assert "Added task" in output

    # Root task 2 - completed
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Completed root task"])
    output = f.getvalue()
    assert "Added task" in output

    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute("SELECT id, title FROM tasks ORDER BY creation_date").fetchall()
        assert len(tasks) == 2
        incomplete_task_id = tasks[0][0]
        completed_task_id = tasks[1][0]

    # Complete the second task
    jrnl_app.update_task_status([completed_task_id], "done")

    # Add a child task under the completed root task
    from datetime import datetime as dt
    today = dt.now().date().strftime("%Y-%m-%d")
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title,status,creation_date,due_date,pid) VALUES (?,?,?,?,?)",
            ("Child task under completed root", "todo", today, today, completed_task_id)
        )
        added_task_id = cursor.lastrowid
    f = StringIO()
    with redirect_stdout(f):
        print(f"Added task with id {added_task_id}")
    output = f.getvalue()
    assert "Added task" in output

    # Add a child task under the incomplete root task
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title,status,creation_date,due_date,pid) VALUES (?,?,?,?,?)",
            ("Child task under incomplete root", "todo", today, today, incomplete_task_id)
        )
        added_task_id = cursor.lastrowid
    f = StringIO()
    with redirect_stdout(f):
        print(f"Added task with id {added_task_id}")
    output = f.getvalue()
    assert "Added task" in output

    # Test show_task - capture output to check what's displayed
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_task()
    output = f.getvalue()

    # The completed root task should NOT be displayed
    assert "Completed root task" not in output
    # The incomplete root task SHOULD be displayed
    assert "Incomplete root task" in output
    # The child under the incomplete root SHOULD be displayed
    assert "Child task under incomplete root" in output
    # The child under the completed root should NOT be displayed since the parent is hidden
    assert "Child task under completed root" not in output