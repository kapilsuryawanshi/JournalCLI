"""Pytest unit tests for the optimized commands in jrnl application:
- j note <id> [-text <text>] [-link <id>[,<id>,...]] [-unlink <id>[,<id>,...]]
- j task <id> [-text <text>] [-due <date>] [-note <text>] [-recur <pattern>]
- j ls <page|note|task> [due|status|done]
- j <note|task> <id>
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

def test_optimized_note_edit_command():
    """Test the optimized 'j note <id> -text <text>' command (replaces 'j edit note <id> -text <text>')."""
    # Add a note first
    jrnl_app.add_note([], "Original note text")
    
    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM notes WHERE text='Original note text'").fetchone()
        assert note is not None
        note_id = note[0]
    
    # Simulate command line arguments for "j note <id> -text 'Updated note text'"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "note", str(note_id), "-text", "Updated note text"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should update note text
        assert f"Updated note {note_id} text to: Updated note text" in output
        
        # Verify the note was updated
        with sqlite3.connect(DB_FILE) as conn:
            note = conn.execute("SELECT text FROM notes WHERE id=?", (note_id,)).fetchone()
            assert note[0] == "Updated note text"
    finally:
        sys.argv = original_argv

def test_optimized_note_link_command():
    """Test the optimized 'j note <id> -link <id>[,<id>,...]' command."""
    # Add two notes to link
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")
    jrnl_app.add_note([], "Note to link to others")
    
    # Get note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()
        assert len(notes) == 3
        note1_id, note2_id, note3_id = [note[0] for note in notes]
    
    # Simulate command line arguments for "j note <id> -link <id1>,<id2>"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "note", str(note3_id), "-link", f"{note1_id},{note2_id}"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should link the notes
        assert f"Linked notes {min(note3_id, note1_id)} and {max(note3_id, note1_id)}" in output
        assert f"Linked notes {min(note3_id, note2_id)} and {max(note3_id, note2_id)}" in output
        
        # Verify the links were created
        with sqlite3.connect(DB_FILE) as conn:
            # Check if both links exist
            link1 = conn.execute(
                "SELECT * FROM note_links WHERE (note1_id=? AND note2_id=?) OR (note1_id=? AND note2_id=?)",
                (note3_id, note1_id, note1_id, note3_id)
            ).fetchone()
            link2 = conn.execute(
                "SELECT * FROM note_links WHERE (note1_id=? AND note2_id=?) OR (note1_id=? AND note2_id=?)",
                (note3_id, note2_id, note2_id, note3_id)
            ).fetchone()
            assert link1 is not None
            assert link2 is not None
    finally:
        sys.argv = original_argv

def test_optimized_note_unlink_command():
    """Test the optimized 'j note <id> -unlink <id>[,<id>,...]' command."""
    # Add notes and create links
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")
    
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()
        note1_id, note2_id = [note[0] for note in notes]
        
        # Create the link
        jrnl_app.link_notes(note1_id, note2_id)
    
    # Verify the link exists
    with sqlite3.connect(DB_FILE) as conn:
        link = conn.execute(
            "SELECT * FROM note_links WHERE (note1_id=? AND note2_id=?) OR (note1_id=? AND note2_id=?)",
            (note1_id, note2_id, note2_id, note1_id)
        ).fetchone()
        assert link is not None
    
    # Simulate command line arguments for "j note <id> -unlink <id>"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "note", str(note1_id), "-unlink", str(note2_id)]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should unlink the notes
        assert f"Unlinked notes {note1_id} and {note2_id}" in output
        
        # Verify the link was removed
        with sqlite3.connect(DB_FILE) as conn:
            link = conn.execute(
                "SELECT * FROM note_links WHERE (note1_id=? AND note2_id=?) OR (note1_id=? AND note2_id=?)",
                (note1_id, note2_id, note2_id, note1_id)
            ).fetchone()
            assert link is None
    finally:
        sys.argv = original_argv

def test_optimized_task_edit_command():
    """Test the optimized 'j task <id> -text <text>' command (replaces 'j edit task <id> -text <text>')."""
    # Add a task first
    jrnl_app.add_task(["Original task title"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Original task title'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Simulate command line arguments for "j task <id> -text 'Updated task title'"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "task", str(task_id), "-text", "Updated task title"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should update task title
        assert f"Updated task {task_id} title to: Updated task title" in output
        
        # Verify the task was updated
        with sqlite3.connect(DB_FILE) as conn:
            task = conn.execute("SELECT title FROM tasks WHERE id=?", (task_id,)).fetchone()
            assert task[0] == "Updated task title"
    finally:
        sys.argv = original_argv

def test_optimized_task_due_command():
    """Test the optimized 'j task <id> -due <date>' command."""
    # Add a task first
    jrnl_app.add_task(["Test task with due date"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task with due date'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Simulate command line arguments for "j task <id> -due 2025-12-25"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "task", str(task_id), "-due", "2025-12-25"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should update due date
        assert f"Updated due date for task {task_id} to 2025-12-25" in output
        
        # Verify the due date was updated
        with sqlite3.connect(DB_FILE) as conn:
            task = conn.execute("SELECT due_date FROM tasks WHERE id=?", (task_id,)).fetchone()
            assert task[0] == "2025-12-25"
    finally:
        sys.argv = original_argv

def test_optimized_task_note_command():
    """Test the optimized 'j task <id> -note <text>' command."""
    # Add a task first
    jrnl_app.add_task(["Test task"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Simulate command line arguments for "j task <id> -note 'Completion note'"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "task", str(task_id), "-note", "Completion note"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should add a note to the task
        assert f"Added note with id" in output
        
        # Verify the note was added to the task
        with sqlite3.connect(DB_FILE) as conn:
            note = conn.execute("SELECT text FROM notes WHERE task_id=?", (task_id,)).fetchone()
            assert note is not None
            assert note[0] == "Completion note"
    finally:
        sys.argv = original_argv

def test_optimized_task_recur_command():
    """Test the optimized 'j task <id> -recur <pattern>' command."""
    # Add a task first
    jrnl_app.add_task(["Test recurring task"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test recurring task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Simulate command line arguments for "j task <id> -recur 2w"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "task", str(task_id), "-recur", "2w"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should set recurrence pattern
        assert f"Set recur pattern '2w' for task {task_id}" in output
        
        # Verify the recurrence was set
        with sqlite3.connect(DB_FILE) as conn:
            task = conn.execute("SELECT recur FROM tasks WHERE id=?", (task_id,)).fetchone()
            assert task[0] == "2w"
    finally:
        sys.argv = original_argv

def test_optimized_ls_command_for_page():
    """Test the optimized 'j ls page' command (replaces 'j list page')."""
    # Add a task and note
    jrnl_app.add_task(["Test task for page view"])
    jrnl_app.add_note([], "Test note for page view")
    
    # Simulate command line arguments for "j ls page"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "ls", "page"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should display the journal view
        assert "Test task for page view" in output
        assert "Test note for page view" in output
    finally:
        sys.argv = original_argv

def test_optimized_ls_command_for_note():
    """Test the optimized 'j ls note' command (replaces 'j list note')."""
    # Add a note
    jrnl_app.add_note([], "Test note for note list")
    
    # Simulate command line arguments for "j ls note"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "ls", "note"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should display the note
        assert "Test note for note list" in output
    finally:
        sys.argv = original_argv

def test_optimized_ls_command_for_task_due():
    """Test the optimized 'j ls task due' command (replaces 'j list task due')."""
    # Add tasks with different due dates
    jrnl_app.add_task(["Overdue task @2020-01-01"])  # Past date
    jrnl_app.add_task(["Today task @today"])  # Today
    jrnl_app.add_task(["Future task @2050-12-31"])  # Future date
    
    # Simulate command line arguments for "j ls task due"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "ls", "task", "due"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should display tasks grouped by due date
        assert "Overdue task" in output
        assert "Today task" in output
        assert "Future task" in output
    finally:
        sys.argv = original_argv

def test_optimized_ls_command_for_task_status():
    """Test the optimized 'j ls task status' command (replaces 'j list task status')."""
    # Add tasks with different statuses
    jrnl_app.add_task(["Todo task"])
    jrnl_app.add_task(["Doing task"])
    jrnl_app.add_task(["Waiting task"])
    
    with sqlite3.connect(DB_FILE) as conn:
        tasks = conn.execute("SELECT id, title FROM tasks ORDER BY creation_date").fetchall()
        assert len(tasks) == 3
        
        # Update statuses
        jrnl_app.update_task_status([tasks[1][0]], "doing")  # Second task to 'doing'
        jrnl_app.update_task_status([tasks[2][0]], "waiting")  # Third task to 'waiting'
    
    # Simulate command line arguments for "j ls task status"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "ls", "task", "status"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should display tasks grouped by status
        assert "Todo task" in output
        assert "Doing task" in output
        assert "Waiting task" in output
    finally:
        sys.argv = original_argv

def test_optimized_ls_command_for_task_done():
    """Test the optimized 'j ls task done' command (replaces 'j list task done')."""
    # Add and complete a task
    jrnl_app.add_task(["Completed task"])
    
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Completed task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Complete the task
    jrnl_app.update_task_status([task_id], "done", "Completed with note")
    
    # Simulate command line arguments for "j ls task done"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "ls", "task", "done"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should display the completed task
        assert "Completed task" in output
    finally:
        sys.argv = original_argv

def test_optimized_note_show_command():
    """Test the optimized 'j note <id>' command (replaces 'j show note <id>')."""
    # Add a note with links
    jrnl_app.add_note([], "Test note")
    jrnl_app.add_note([], "Linked note")
    
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()
        assert len(notes) == 2
        note1_id, note2_id = [note[0] for note in notes]
        
        # Create the link
        jrnl_app.link_notes(note1_id, note2_id)
    
    # Simulate command line arguments for "j note <id>"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "note", str(note1_id)]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should display the specific note and its linked notes
        assert "Test note" in output
        assert "Linked note" in output
    finally:
        sys.argv = original_argv

def test_optimized_task_show_command():
    """Test the optimized 'j task <id>' command (replaces 'j show task <id>')."""
    # Add a task
    jrnl_app.add_task(["Test task"])
    
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks WHERE title='Test task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Simulate command line arguments for "j task <id>"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "task", str(task_id)]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should display the specific task
        assert "Test task" in output
    finally:
        sys.argv = original_argv

def test_optimized_commands_help():
    """Test that help message reflects the new optimized commands."""
    # Simulate command line arguments for "j help"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "help"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should contain the new command syntax
        assert "j note <id> [-text <text>] [-link <id>[,<id>,...]] [-unlink <id>[,<id>,...]] [-task <text>]" in output
        assert "j task <id> [-text <text>] [-due <date>] [-note <text>] [-recur <pattern>]" in output
        assert "j ls <page|note|task> [due|status|done]" in output
        assert "Edit note with optional text, linking, unlinking, adding subtask or show note details if no options" in output
        assert "Edit task with optional parameters or show task details if no options" in output
    finally:
        sys.argv = original_argv

if __name__ == "__main__":
    test_optimized_note_edit_command()
    test_optimized_note_link_command()
    test_optimized_note_unlink_command()
    test_optimized_task_edit_command()
    test_optimized_task_due_command()
    test_optimized_task_note_command()
    test_optimized_task_recur_command()
    test_optimized_ls_command_for_page()
    test_optimized_ls_command_for_note()
    test_optimized_ls_command_for_task_due()
    test_optimized_ls_command_for_task_status()
    test_optimized_ls_command_for_task_done()
    test_optimized_note_show_command()
    test_optimized_task_show_command()
    test_optimized_commands_help()
    print("All optimized command tests passed!")