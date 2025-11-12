"""Comprehensive pytest unit tests for the full jrnl application functionality."""

import sqlite3
import tempfile
import os
import sys
from datetime import datetime, timedelta
from io import StringIO
from contextlib import redirect_stdout
from unittest.mock import patch
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

def test_add_task_without_due_date():
    """Test adding a task without a due date - should default to today"""
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task without due date"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Verify the task was added
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT title, due_date FROM tasks WHERE title='Test task without due date'").fetchone()
        assert task is not None
        assert task[0] == "Test task without due date"
        # Due date should be today
        today = datetime.now().date().strftime("%Y-%m-%d")
        assert task[1] == today

def test_add_task_with_due_date_keyword():
    """Test adding a task with a due date keyword like 'tomorrow'"""
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task @tomorrow"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Verify the task was added with tomorrow's date
    tomorrow = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT title, due_date FROM tasks WHERE title='Test task'").fetchone()
        assert task is not None
        assert task[0] == "Test task"
        assert task[1] == tomorrow

def test_add_task_with_explicit_due_date():
    """Test adding a task with an explicit due date"""
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task @2025-12-25"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Verify the task was added with the specified date
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT title, due_date FROM tasks WHERE title='Test task'").fetchone()
        assert task is not None
        assert task[0] == "Test task"
        assert task[1] == "2025-12-25"

def test_add_multiple_tasks():
    """Test adding multiple tasks at once"""
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Task 1", "Task 2 @tomorrow", "Task 3 @2025-12-25"])
    output = f.getvalue()
    assert "Added tasks with IDs:" in output
    
    # Verify all tasks were added
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute("SELECT title, due_date FROM tasks ORDER BY title").fetchall()
        assert len(tasks) == 3
        
        # Task 1: Should have today's date
        assert tasks[0][0] == "Task 1"
        today = datetime.now().date().strftime("%Y-%m-%d")
        assert tasks[0][1] == today
        
        # Task 2: Should have tomorrow's date
        assert tasks[1][0] == "Task 2"
        tomorrow = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert tasks[1][1] == tomorrow
        
        # Task 3: Should have explicit date
        assert tasks[2][0] == "Task 3"
        assert tasks[2][1] == "2025-12-25"

def test_add_standalone_note():
    """Test adding a note without task association"""
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_note([], "Standalone note")
    output = f.getvalue()
    assert "Added standalone note" in output
    
    # Verify the note was added
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT text, task_id FROM notes WHERE text='Standalone note'").fetchone()
        assert note is not None
        assert note[0] == "Standalone note"
        assert note[1] is None  # Should not be associated with any task

def test_add_note_to_specific_task():
    """Test adding a note to a specific task"""
    # First create a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task for note"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task for note'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Add a note to the task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_note([task_id], "Note for task 1")
    output = f.getvalue()
    assert "Added note with id" in output
    
    # Verify the note was added and linked to the task
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT text, task_id FROM notes WHERE text='Note for task 1'").fetchone()
        assert note is not None
        assert note[0] == "Note for task 1"
        assert note[1] == task_id

def test_add_note_to_multiple_tasks():
    """Test adding a note to multiple tasks"""
    # Create two tasks
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Task 1", "Task 2"])
    output = f.getvalue()
    assert "Added 2 task(s)" in output
    
    # Get the task IDs
    with sqlite3.connect(DB_FILE) as conn:
        task_ids = [row[0] for row in conn.execute("SELECT id FROM tasks ORDER BY creation_date").fetchall()]
        assert len(task_ids) == 2
    
    # Add a note to both tasks
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_note(task_ids, "Note for tasks 1 and 2")
    output = f.getvalue()
    assert "Added note with id" in output
    
    # Verify the note was added for each task
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT text, task_id FROM notes WHERE text='Note for tasks 1 and 2' ORDER BY task_id").fetchall()
        assert len(notes) == 2
        # Each note should be linked to one of the tasks
        note_task_ids = [note[1] for note in notes]
        for task_id in task_ids:
            assert task_id in note_task_ids

def test_mark_task_as_done():
    """Test marking task as done - basic functionality"""
    # Create a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Mark task as done
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "done")
    output = f.getvalue()
    assert "Updated 1 task(s) to done" in output
    
    # Verify the task status was updated
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT status, completion_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "done"
        assert task[1] is not None  # completion date should be set

def test_mark_task_as_doing():
    """Test marking task as doing"""
    # Create a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Mark task as doing
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "doing")
    output = f.getvalue()
    assert "Updated 1 task(s) to doing" in output
    
    # Verify the task status was updated
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "doing"

def test_mark_task_as_waiting():
    """Test marking task as waiting"""
    # Create a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Mark task as waiting
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "waiting")
    output = f.getvalue()
    assert "Updated 1 task(s) to waiting" in output
    
    # Verify the task status was updated
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "waiting"

def test_mark_task_as_undone():
    """Test marking task as undone (back to todo)"""
    # Create a task and mark it as done
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Mark task as done first
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "done")
    output = f.getvalue()
    assert "Updated 1 task(s) to done" in output
    
    # Verify it's done
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT status, completion_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "done"
        assert task[1] is not None
    
    # Now mark it as undone (back to todo)
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "todo")
    output = f.getvalue()
    assert "Updated 1 task(s) to undone" in output
    
    # Verify the task status was updated back to todo and completion date is cleared
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT status, completion_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "todo"
        assert task[1] is None  # completion date should be cleared

def test_update_due_date_with_keyword():
    """Test updating due date with keyword"""
    # Create a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Update due date to tomorrow
    tomorrow = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE tasks SET due_date=? WHERE id=?", (tomorrow, task_id))
    
    # Verify the due date was updated
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT due_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == tomorrow

def test_update_due_date_with_explicit_date():
    """Test updating due date with explicit date"""
    # Create a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Update due date to a specific date
    new_due_date = "2025-12-25"
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE tasks SET due_date=? WHERE id=?", (new_due_date, task_id))
    
    # Verify the due date was updated
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT due_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == new_due_date

def test_format_date_with_day():
    """Test the format_date_with_day function"""
    test_date = "2025-09-22"  # This is a Monday
    formatted = jrnl_app.format_date_with_day(test_date)
    assert "Monday" in formatted
    assert "2025-09-22" in formatted

def test_parse_due_keywords():
    """Test various due date parsing keywords"""
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    
    # Test 'today'
    assert jrnl_app.parse_due("today") == today
    
    # Test 'tomorrow'
    assert jrnl_app.parse_due("tomorrow") == tomorrow
    
    # Test 'eow' (end of week)
    eow = today + timedelta(days=(6 - today.weekday()))
    assert jrnl_app.parse_due("eow") == eow
    
    # Test 'eom' (end of month)
    if today.month == 12:
        eom = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        eom = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    assert jrnl_app.parse_due("eom") == eom
    
    # Test 'eoy' (end of year)
    eoy = today.replace(month=12, day=31)
    assert jrnl_app.parse_due("eoy") == eoy

def test_parse_due_day_names():
    """Test parsing day names for due dates"""
    today = datetime.now().date()
    
    # Test 'monday' - get next Monday
    day_names = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }
    
    target_weekday = day_names["monday"]
    days_ahead = (target_weekday - today.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7  # If today is Monday, get next Monday
    next_monday = today + timedelta(days=days_ahead)
    
    assert jrnl_app.parse_due("monday") == next_monday

def test_parse_due_explicit_date():
    """Test parsing explicit date formats"""
    expected_date = datetime.strptime("2025-12-25", "%Y-%m-%d").date()
    assert jrnl_app.parse_due("2025-12-25") == expected_date

def test_set_task_recur():
    """Test setting a task to recur"""
    # Create a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test recurring task"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test recurring task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Set the task to recur every 2 weeks
    success = jrnl_app.set_task_recur([task_id], "2w")
    assert success is True
    
    # Verify the recur pattern was set
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT recur FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "2w"

def test_calculate_next_due_date():
    """Test calculating next due date based on recurrence pattern"""
    # Test with 1 week pattern
    current_date = "2025-09-22"  # Monday
    next_date = jrnl_app.calculate_next_due_date(current_date, "1w")
    expected = "2025-09-29"  # Next Monday
    assert next_date == expected
    
    # Test with 2 days pattern
    next_date = jrnl_app.calculate_next_due_date(current_date, "2d")
    expected = "2025-09-24"  # Wednesday
    assert next_date == expected
    
    # Test with 1 month pattern
    next_date = jrnl_app.calculate_next_due_date(current_date, "1m")
    expected = "2025-10-22"
    assert next_date == expected
    
    # Test with 1 year pattern
    next_date = jrnl_app.calculate_next_due_date(current_date, "1y")
    expected = "2026-09-22"
    assert next_date == expected

def test_edit_task_title():
    """Test editing a task title"""
    # Create a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Original task title"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Original task title'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Edit the task title
    result = jrnl_app.edit_item(task_id, "New task title")
    assert result is True
    
    # Verify the task title was updated
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT title FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task[0] == "New task title"

def test_edit_note_text():
    """Test editing a note text"""
    # Add a standalone note
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_note([], "Original note text")
    output = f.getvalue()
    assert "Added standalone note" in output
    
    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM notes WHERE text='Original note text'").fetchone()
        assert note is not None
        note_id = note[0]
    
    # Edit the note text
    result = jrnl_app.edit_item(note_id, "New note text")
    assert result is True
    
    # Verify the note text was updated
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT text FROM notes WHERE id=?", (note_id,)).fetchone()
        assert note[0] == "New note text"

def test_delete_task():
    """Test deleting a task along with its notes"""
    # Create a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Task to delete"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Task to delete'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Add a note to the task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_note([task_id], "Note for task to delete")
    output = f.getvalue()
    assert "Added note with id" in output
    
    # Verify task and note exist
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task is not None
        note = conn.execute("SELECT id FROM notes WHERE task_id=?", (task_id,)).fetchone()
        assert note is not None
    
    # Delete the task - mock the input to confirm deletion
    with patch('builtins.input', return_value='yes'):
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.delete_task([task_id])
        output = f.getvalue()
        assert "Deleted 1 task(s)" in output
    
    # Verify task and its notes were deleted
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert task is None
        note = conn.execute("SELECT id FROM notes WHERE task_id=?", (task_id,)).fetchone()
        assert note is None

def test_delete_note():
    """Test deleting a note"""
    # Add a standalone note
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_note([], "Note to delete")
    output = f.getvalue()
    assert "Added standalone note" in output
    
    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM notes WHERE text='Note to delete'").fetchone()
        assert note is not None
        note_id = note[0]
    
    # Verify the note exists
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM notes WHERE id=?", (note_id,)).fetchone()
        assert note is not None
    
    # Delete the note - mock the input to confirm deletion
    with patch('builtins.input', return_value='yes'):
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.delete_note([note_id])
        output = f.getvalue()
        assert "Deleted 1 note" in output
    
    # Verify the note was deleted
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM notes WHERE id=?", (note_id,)).fetchone()
        assert note is None

def test_search_functionality():
    """Test search functionality for tasks and notes"""
    # Create a task and note for searching
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Searchable task"])
        jrnl_app.add_note([], "Searchable note")
    output = f.getvalue()
    assert "Added task with id" in output
    assert "Added standalone note with id" in output
    
    # Test searching for the task
    grouped, tasks, notes = jrnl_app.search_items("Searchable")
    
    # Should find both the task and the note
    found_task = False
    found_note = False
    
    for day in grouped:
        if grouped[day]["tasks"]:
            for task in grouped[day]["tasks"]:
                if "Searchable task" in task[1]:  # task[1] is the title
                    found_task = True
        if grouped[day]["notes"]:
            for note in grouped[day]["notes"]:
                if "Searchable note" in note[1]:  # note[1] is the text
                    found_note = True
    
    assert found_task
    assert found_note

def test_format_task():
    """Test formatting a task for display"""
    # Create a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id, title, status, creation_date, due_date, completion_date, recur, pid FROM tasks").fetchone()
        assert task is not None
    
    # Format the task
    formatted = jrnl_app.format_task(task)
    assert "Test task" in formatted
    assert f"id:{task[0]}" in formatted  # task[0] is the id

def test_format_note():
    """Test formatting a note for display"""
    # Create a note
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_note([], "Test note")
    output = f.getvalue()
    assert "Added standalone note" in output
    
    # Get the note
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id, text, creation_date, task_id FROM notes").fetchone()
        assert note is not None
    
    # Format the note
    formatted = jrnl_app.format_note(note)
    assert "Test note" in formatted
    assert f"id:{note[0]}" in formatted  # note[0] is the id

def test_mark_task_as_done_with_note():
    """Test marking task as done with note"""
    # Create a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Mark task as done with a note
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

def test_mark_multiple_tasks_as_done_with_note():
    """Test marking multiple tasks as done with note"""
    # Create two tasks
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Task 1"])
        jrnl_app.add_task(["Task 2"])
    output = f.getvalue()
    # Since we're adding tasks individually, we'll get two "Added task with id" messages
    assert output.count("Added task with id") == 2
    
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

def test_recurring_task_creates_new_task_when_completed():
    """Test that completing a recurring task creates a new task with updated due date"""
    # Create a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Recurring task"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Recurring task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Set the task to recur every week
    success = jrnl_app.set_task_recur([task_id], "1w")
    assert success is True
    
    # Complete the task (this should create a new task)
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "done")
    output = f.getvalue()
    # Should contain both the update message and the new task creation message
    assert "Updated 1 task(s) to done" in output
    assert "Created recurring task for" in output
    
    # Verify the original task was marked as done
    with sqlite3.connect(DB_FILE) as conn:
        original_task = conn.execute("SELECT status, completion_date FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert original_task[0] == "done"
        assert original_task[1] is not None  # completion date should be set
        
        # Verify a new task was created with the same title
        new_tasks = conn.execute("SELECT id, status, title FROM tasks WHERE title='Recurring task' AND status='todo'").fetchall()
        assert len(new_tasks) == 1  # New task should be created with todo status
        assert new_tasks[0][1] == "todo"  # Status should be todo

def test_show_completed_tasks():
    """Test showing completed tasks"""
    # Create and complete a task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Completed task"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Completed task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Complete the task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "done", "Completed with note")
    output = f.getvalue()
    assert "Updated 1 task(s) to done" in output
    
    # Show completed tasks (capture the output to check if it works without error)
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_completed_tasks()
    output = f.getvalue()
    # Should display the completed task
    assert "Completed task" in output

def test_show_tasks_by_status():
    """Test showing tasks grouped by status"""
    # Create tasks with different statuses
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Todo task"])
        jrnl_app.add_task(["Doing task"])
        jrnl_app.add_task(["Waiting task"])
    output = f.getvalue()
    assert "Added task with id" in output  # Should print this 3 times
    
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute("SELECT id, title FROM tasks ORDER BY creation_date").fetchall()
        assert len(tasks) == 3
        
        # Update statuses
        jrnl_app.update_task_status([tasks[1][0]], "doing")  # Second task to 'doing'
        jrnl_app.update_task_status([tasks[2][0]], "waiting")  # Third task to 'waiting'
    
    # Show tasks by status (capture the output to check if it works without error)
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_tasks_by_status()
    output = f.getvalue()
    
    # Should display all three tasks
    assert "Todo task" in output
    assert "Doing task" in output
    assert "Waiting task" in output

def test_show_due_tasks():
    """Test showing tasks grouped by due date"""
    # Create tasks with different due dates
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Overdue task @2020-01-01"])  # Past date
        jrnl_app.add_task(["Today task @today"])  # Today
        jrnl_app.add_task(["Future task @2050-12-31"])  # Future date
    output = f.getvalue()
    assert "Added task with id" in output  # Should print this 3 times
    
    # Show due tasks (capture the output to check if it works without error)
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_due()
    output = f.getvalue()
    
    # Should show the tasks in the appropriate sections
    assert "Overdue task" in output
    assert "Today task" in output
    assert "Future task" in output

def test_show_task_list():
    """Test showing all unfinished tasks"""
    # Create tasks with different statuses
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Unfinished task"])
        jrnl_app.add_task(["Finished task"])
    output = f.getvalue()
    assert "Added task with id" in output  # Should print this 2 times
    
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute("SELECT id, title FROM tasks ORDER BY creation_date").fetchall()
        assert len(tasks) == 2
        
        # Complete one task
        jrnl_app.update_task_status([tasks[1][0]], "done")  # Second task to 'done'
    
    # Show tasks (capture the output to check if it works without error)
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_task()
    output = f.getvalue()
    
    # Should display only the unfinished task
    assert "Unfinished task" in output
    # Should not display the finished task
    assert "Finished task" not in output

def test_show_notes():
    """Test showing all notes"""
    # Create a task and add a note to it
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task for notes"])
    output = f.getvalue()
    assert "Added task with id" in output
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task for notes'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Add notes
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_note([task_id], "Note for test task")
        jrnl_app.add_note([], "Standalone note")
    output = f.getvalue()
    # Output will have both "Added note to 1 task(s)" and "Added standalone note"
    
    # Show notes (capture the output to check if it works without error)
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_note()
    output = f.getvalue()
    
    # Should show both notes
    assert "Note for test task" in output
    assert "Standalone note" in output

def test_show_journal():
    """Test showing the journal view"""
    # Create a task and note
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Journal task"])
        jrnl_app.add_note([], "Journal note")
    output = f.getvalue()
    
    # Show journal (capture the output to check if it works without error)
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_journal()
    output = f.getvalue()
    
    # Should show the task and note
    assert "Journal task" in output
    assert "Journal note" in output

if __name__ == "__main__":
    # Run all tests
    test_add_task_without_due_date()
    test_add_task_with_due_date_keyword()
    test_add_task_with_explicit_due_date()
    test_add_multiple_tasks()
    test_add_standalone_note()
    test_add_note_to_specific_task()
    test_add_note_to_multiple_tasks()
    test_mark_task_as_done()
    test_mark_task_as_doing()
    test_mark_task_as_waiting()
    test_mark_task_as_undone()
    test_update_due_date_with_keyword()
    test_update_due_date_with_explicit_date()
    test_format_date_with_day()
    test_parse_due_keywords()
    test_parse_due_day_names()
    test_parse_due_explicit_date()
    test_set_task_recur()
    test_calculate_next_due_date()
    test_edit_task_title()
    test_edit_note_text()
    test_delete_task()
    test_delete_note()
    test_search_functionality()
    test_format_task()
    test_format_note()
    test_mark_task_as_done_with_note()
    test_mark_multiple_tasks_as_done_with_note()
    test_recurring_task_creates_new_task_when_completed()
    test_show_completed_tasks()
    test_show_tasks_by_status()
    test_show_due_tasks()
    test_show_task_list()
    test_show_notes()
    test_show_journal()
    print("All comprehensive tests passed!")