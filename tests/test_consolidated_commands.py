"""Pytest unit tests for the new consolidated commands in jrnl application:
- jrnl note <text> [-link <id>[,<id>,...]]
- jrnl task <text> [-due @<YYYY-MM-DD|today|tomorrow|eow|eom|eoy>] [-recur <Nd|Nw|Nm|Ny>]
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

def test_consolidated_new_note_basic():
    """Test adding a basic standalone note with the new command."""
    # Simulate command line arguments for "jrnl note Test note text"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "note", "Test note text"]
    
    try:
        # Capture stdout to check output
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        assert "Added standalone note" in output
        
        # Verify the note was actually added to the database
        with sqlite3.connect(DB_FILE) as conn:
            note = conn.execute("SELECT text, task_id FROM notes WHERE text='Test note text'").fetchone()
            assert note is not None
            assert note[0] == "Test note text"
            assert note[1] is None  # Should not be associated with any task
    finally:
        sys.argv = original_argv

def test_consolidated_new_note_with_links():
    """Test adding a note and linking it to existing notes."""
    # First add two existing notes to link to
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")
    
    # Get note IDs
    with sqlite3.connect(DB_FILE) as conn:
        note_ids = [row[0] for row in conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()]
        assert len(note_ids) == 2
        note1_id = note_ids[0]
        note2_id = note_ids[1]
    
    # Simulate command line arguments for "jrnl note Test note -link <id>,<id>"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "note", "Test note with links", "-link", f"{note1_id},{note2_id}"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        assert "Added standalone note" in output
        
        # Verify the new note was added
        with sqlite3.connect(DB_FILE) as conn:
            new_note = conn.execute("SELECT id, text FROM notes WHERE text='Test note with links'").fetchone()
            assert new_note is not None
            new_note_id = new_note[0]
        
        # Verify links were created
        with sqlite3.connect(DB_FILE) as conn:
            links = conn.execute(
                "SELECT note1_id, note2_id FROM note_links WHERE ? IN (note1_id, note2_id) OR ? IN (note1_id, note2_id)",
                (new_note_id, new_note_id)
            ).fetchall()
            assert len(links) == 2  # Should be linked to both existing notes
    finally:
        sys.argv = original_argv

def test_consolidated_new_task_basic():
    """Test adding a basic task with the new command."""
    # Simulate command line arguments for "jrnl task Test task text"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "task", "Test task text"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        assert "Added 1 task(s)" in output
        
        # Verify the task was added with today's date
        with sqlite3.connect(DB_FILE) as conn:
            task = conn.execute("SELECT title, due_date FROM tasks WHERE title='Test task text'").fetchone()
            assert task is not None
            assert task[0] == "Test task text"
            # Due date should be today
            today = datetime.now().date().strftime("%Y-%m-%d")
            assert task[1] == today
    finally:
        sys.argv = original_argv

def test_consolidated_new_task_with_due_date():
    """Test adding a task with a due date."""
    # Simulate command line arguments for "jrnl task Test task -due @tomorrow"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "task", "Test task with due date", "-due", "@tomorrow"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        assert "Added 1 task(s)" in output
        
        # Verify the task was added with tomorrow's date
        tomorrow = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
        with sqlite3.connect(DB_FILE) as conn:
            task = conn.execute("SELECT title, due_date FROM tasks WHERE title='Test task with due date'").fetchone()
            assert task is not None
            assert task[0] == "Test task with due date"
            assert task[1] == tomorrow
    finally:
        sys.argv = original_argv

def test_consolidated_new_task_with_explicit_due_date():
    """Test adding a task with an explicit due date."""
    # Simulate command line arguments for "jrnl task Test task -due @2025-12-25"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "task", "Test task with explicit due date", "-due", "@2025-12-25"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        assert "Added 1 task(s)" in output
        
        # Verify the task was added with the specified date
        with sqlite3.connect(DB_FILE) as conn:
            task = conn.execute("SELECT title, due_date FROM tasks WHERE title='Test task with explicit due date'").fetchone()
            assert task is not None
            assert task[0] == "Test task with explicit due date"
            assert task[1] == "2025-12-25"
    finally:
        sys.argv = original_argv

def test_consolidated_new_task_with_recurrence():
    """Test adding a task with recurrence."""
    # Simulate command line arguments for "jrnl task Test task -recur 2w"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "task", "Test recurring task", "-recur", "2w"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        assert "Added 1 task(s)" in output
        
        # Verify the task was added with the recurrence pattern
        with sqlite3.connect(DB_FILE) as conn:
            task = conn.execute("SELECT title, recur FROM tasks WHERE title='Test recurring task'").fetchone()
            assert task is not None
            assert task[0] == "Test recurring task"
            assert task[1] == "2w"
    finally:
        sys.argv = original_argv

def test_consolidated_new_task_with_due_date_and_recurrence():
    """Test adding a task with both due date and recurrence."""
    # Simulate command line arguments for "jrnl task Test task -due @tomorrow -recur 1w"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "task", "Test recurring task with due date", "-due", "@tomorrow", "-recur", "1w"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        assert "Added 1 task(s)" in output
        
        # Verify the task was added with both due date and recurrence
        tomorrow = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
        with sqlite3.connect(DB_FILE) as conn:
            task = conn.execute("SELECT title, due_date, recur FROM tasks WHERE title='Test recurring task with due date'").fetchone()
            assert task is not None
            assert task[0] == "Test recurring task with due date"
            assert task[1] == tomorrow
            assert task[2] == "1w"
    finally:
        sys.argv = original_argv

def test_new_note_command_works():
    """Test that the new 'jrnl note <text>' command is now available."""
    # Simulate command line arguments for "jrnl note Test note text"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "note", "Test note text"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # The new command should work and add a standalone note
        assert "Added standalone note" in output
        
        # Verify the note was actually added to the database
        with sqlite3.connect(DB_FILE) as conn:
            note = conn.execute("SELECT text, task_id FROM notes WHERE text='Test note text'").fetchone()
            assert note is not None
            assert note[0] == "Test note text"
            assert note[1] is None  # Should not be associated with any task
    finally:
        sys.argv = original_argv

def test_new_task_command_works():
    """Test that the new 'jrnl task <text>' command is now available."""
    # Simulate command line arguments for "jrnl task Test task text"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "task", "Test task text"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # The new command should work and add a task
        assert "Added 1 task(s)" in output
        
        # Verify the task was added with today's date
        with sqlite3.connect(DB_FILE) as conn:
            task = conn.execute("SELECT title, due_date FROM tasks WHERE title='Test task text'").fetchone()
            assert task is not None
            assert task[0] == "Test task text"
            # Due date should be today
            today = datetime.now().date().strftime("%Y-%m-%d")
            assert task[1] == today
    finally:
        sys.argv = original_argv

if __name__ == "__main__":
    test_consolidated_new_note_basic()
    test_consolidated_new_note_with_links()
    test_consolidated_new_task_basic()
    test_consolidated_new_task_with_due_date()
    test_consolidated_new_task_with_explicit_due_date()
    test_consolidated_new_task_with_recurrence()
    test_consolidated_new_task_with_due_date_and_recurrence()
    test_old_note_command_removed()
    test_old_task_command_removed()
    print("All consolidated command tests passed!")