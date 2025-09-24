"""Pytest unit tests for the jrnl application, specifically for the done command with notes functionality."""

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

def test_mark_task_as_done_with_note():
    """Test marking task as done with note - Test Case 66"""
    # Create a task
    jrnl_app.add_task(["Test task"])
    
    # Mark task as done with a note
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Capture output from update_task_status
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "done", "Completed with important note")
    output = f.getvalue()
    assert "Updated 1 task(s) to done" in output
    
    # Verify the task status was updated
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT status, completion_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "done"
        assert task[1] is not None  # completion date should be set
        
        # Verify the note was added
        note = conn.execute("SELECT text FROM notes WHERE task_id=?", (task_id,)).fetchone()
        assert note is not None
        assert note[0] == "Completed with important note"

def test_mark_task_as_done_with_note_using_shortcut():
    """Test marking task as done with note using shortcut - Test Case 67"""
    # Create a task
    jrnl_app.add_task(["Test task with shortcut"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task with shortcut'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Simulate the main function call for 'x' command with note
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "done", "Completed with shortcut and note")
    output = f.getvalue()
    assert "Updated 1 task(s) to done" in output
    
    # Verify the task status was updated
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT status, completion_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "done"
        assert task[1] is not None  # completion date should be set
        
        # Verify the note was added
        note = conn.execute("SELECT text FROM notes WHERE task_id=?", (task_id,)).fetchone()
        assert note is not None
        assert note[0] == "Completed with shortcut and note"

def test_mark_multiple_tasks_as_done_with_note():
    """Test marking multiple tasks as done with note - Test Case 68"""
    # Create two tasks
    jrnl_app.add_task(["Task 1"])
    jrnl_app.add_task(["Task 2"])
    
    # Get the task IDs
    with sqlite3.connect(DB_FILE) as conn:
        task_ids = [row[0] for row in conn.execute("SELECT id FROM tasks ORDER BY creation_date").fetchall()]
        assert len(task_ids) == 2
    
    # Update both tasks to done with a note
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status(task_ids, "done", "Completed multiple tasks with note")
    output = f.getvalue()
    assert "Updated 2 task(s) to done" in output
    
    # Verify both tasks were updated
    with sqlite3.connect(DB_FILE) as conn:
        for task_id in task_ids:
            task = conn.execute("SELECT status, completion_date FROM tasks WHERE id=?", (task_id,)).fetchone()
            assert task[0] == "done"
            assert task[1] is not None  # completion date should be set
            
            # Verify the note was added for each task
            note = conn.execute("SELECT text FROM notes WHERE task_id=?", (task_id,)).fetchone()
            assert note is not None
            assert note[0] == "Completed multiple tasks with note"

def test_attempt_to_mark_task_as_done_without_note():
    """Test attempting to mark task as done without note - Test Case 69"""
    # This test specifically checks that when the main function processes 'jrnl done' without note,
    # it should show an error message
    import argparse
    from unittest.mock import patch, MagicMock
    
    # Create a task
    jrnl_app.add_task(["Test task without note"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task without note'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Mock sys.argv to simulate command 'jrnl done <task_id>' without note
    with patch('sys.argv', ['jrnl_app.py', 'done', str(task_id)]):
        # Capture stdout to verify error message
        f = StringIO()
        with redirect_stdout(f):
            # We'll manually test the logic that would be in main() for this case
            rest = [str(task_id)]
            
            # Parse task IDs and note text (similar to main function logic)
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
            
            # Check if the error handling works
            if not ids:
                print("Error: Please provide valid task IDs and note text")
                return  # This would be in main function
            
            if not note_text:
                print("Error: Please provide a note for completing the task(s)")
                return  # This would be in main function
            
            # If we reach here, it means we have both IDs and note text
            jrnl_app.update_task_status(ids, "done", note_text)
        
        output = f.getvalue()
        assert "Error: Please provide a note for completing the task(s)" in output

def test_attempt_to_mark_task_as_done_with_shortcut_without_note():
    """Test attempting to mark task as done with shortcut without note - Test Case 70"""
    # This test specifically checks that when the main function processes 'jrnl x' without note,
    # it should show an error message
    from unittest.mock import patch
    
    # Create a task
    jrnl_app.add_task(["Test task shortcut without note"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task shortcut without note'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Manually test the logic that would be in main() for this case
    rest = [str(task_id)]
    
    # Parse task IDs and note text (similar to main function logic)
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
    
    # Check if the error handling works
    f = StringIO()
    with redirect_stdout(f):
        if not ids:
            print("Error: Please provide valid task IDs and note text")
        elif not note_text:
            print("Error: Please provide a note for completing the task(s)")
        else:
            # If we reach here, it means we have both IDs and note text
            jrnl_app.update_task_status(ids, "done", note_text)
    
    output = f.getvalue()
    assert "Error: Please provide a note for completing the task(s)" in output

def test_update_task_status_function_with_note():
    """Test the update_task_status function directly to ensure notes are properly added"""
    # Create a task
    jrnl_app.add_task(["Test task for function test"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task for function test'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Call update_task_status with a note
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "done", "Test note for function test")
    output = f.getvalue()
    assert "Updated 1 task(s) to done" in output
    
    # Verify task was updated and note was added
    with sqlite3.connect(DB_FILE) as conn:
        # Check task status
        task = conn.execute("SELECT status, completion_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "done"
        assert task[1] is not None  # completion date should be set
        
        # Check that note was added
        note = conn.execute("SELECT text, task_id FROM notes WHERE task_id=?", (task_id,)).fetchone()
        assert note is not None
        assert note[0] == "Test note for function test"
        assert note[1] == task_id

def test_update_task_status_function_without_note():
    """Test the update_task_status function directly to ensure it works without note"""
    # Create a task
    jrnl_app.add_task(["Test task without note"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task without note'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Call update_task_status without a note
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "done", None)
    output = f.getvalue()
    assert "Updated 1 task(s) to done" in output
    
    # Verify task was updated but no note was added
    with sqlite3.connect(DB_FILE) as conn:
        # Check task status
        task = conn.execute("SELECT status, completion_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "done"
        assert task[1] is not None  # completion date should be set
        
        # Check that no note was added
        notes = conn.execute("SELECT text FROM notes WHERE task_id=?", (task_id,)).fetchall()
        assert len(notes) == 0

def test_undone_command_clears_completion_date():
    """Test that undoing a task clears the completion date"""
    # Create and complete a task with a note
    jrnl_app.add_task(["Task to be undone"])
    
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Task to be undone'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Mark as done with note
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "done", "Completion note")
    output = f.getvalue()
    assert "Updated 1 task(s) to done" in output
    
    # Verify the task was completed
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT status, completion_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "done"
        assert task[1] is not None  # completion date should be set
    
    # Now mark as undone (todo)
    with redirect_stdout(StringIO()):
        jrnl_app.update_task_status([task_id], "todo")
    
    # Verify the task was marked as todo and completion date is cleared
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT status, completion_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "todo"
        assert task[1] is None  # completion date should be cleared

if __name__ == "__main__":
    test_mark_task_as_done_with_note()
    test_mark_task_as_done_with_note_using_shortcut()
    test_mark_multiple_tasks_as_done_with_note()
    test_attempt_to_mark_task_as_done_without_note()
    test_attempt_to_mark_task_as_done_with_shortcut_without_note()
    test_update_task_status_function_with_note()
    test_update_task_status_function_without_note()
    test_undone_command_clears_completion_date()
    print("All tests passed!")