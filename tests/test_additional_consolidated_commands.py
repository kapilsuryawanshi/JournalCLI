"""Pytest unit tests for the additional consolidated commands in jrnl application:
- jrnl view task <due|status|done>
- jrnl <start|restart|waiting|done|delete> task <id>[,<id>,...]
- jrnl show <note|task> <id>
"""

import sqlite3
import tempfile
import os
import sys
from datetime import datetime, timedelta
from io import StringIO
from contextlib import redirect_stdout

# Add the project directory to sys.path so we can import jrnl_app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

def test_consolidated_view_task_due():
    """Test viewing tasks by due date using the new consolidated command."""
    # Add a task
    jrnl_app.add_task(["Test due task @tomorrow"])
    
    # Simulate command line arguments for "jrnl ls task due"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "ls", "task", "due"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the due task is shown
        assert "Test due task" in output
        assert "due:" in output  # Check that due date is shown
    finally:
        sys.argv = original_argv

def test_consolidated_view_task_status():
    """Test viewing tasks by status using the new consolidated command."""
    # Add tasks and set their status
    jrnl_app.add_task(["Test status task"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM items WHERE title='Test status task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Update task status to 'doing'
    jrnl_app.update_task_status([task_id], "doing")
    
    # Simulate command line arguments for "jrnl ls task status"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "ls", "task", "status"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the doing task is shown in the appropriate section
        assert "Test status task" in output
        assert "Doing" in output
    finally:
        sys.argv = original_argv

def test_consolidated_view_task_done():
    """Test viewing completed tasks using the new consolidated command."""
    # Add a task and mark it as done
    jrnl_app.add_task(["Test done task"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM items WHERE title='Test done task'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Mark task as done
    jrnl_app.update_task_status([task_id], "done", "Completed successfully")
    
    # Simulate command line arguments for "jrnl ls task done"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "ls", "task", "done"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the completed task is shown
        assert "Test done task" in output
        assert "done" in output.lower()
    finally:
        sys.argv = original_argv

def test_consolidated_task_start():
    """Test starting tasks using the new consolidated command."""
    # Add tasks
    jrnl_app.add_task(["Test task 1"])
    jrnl_app.add_task(["Test task 2"])
    
    # Get the task IDs
    with sqlite3.connect(DB_FILE) as conn:
        task_ids = [row[0] for row in conn.execute("SELECT id FROM items WHERE status IN ('todo', 'doing', 'waiting', 'done') ORDER BY id ASC").fetchall()]
        assert len(task_ids) == 2
        task1_id, task2_id = task_ids
    
    # Simulate command line arguments for "jrnl start task <id>,<id>"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "start", "task", f"{task1_id},{task2_id}"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the tasks were updated to 'doing' status
        assert "Updated 2 tasks to doing" in output
        
        # Verify the status change in DB
        with sqlite3.connect(DB_FILE) as conn:
            tasks = conn.execute("""
                SELECT status 
                FROM items
                WHERE id IN (?,?)
            """, (task1_id, task2_id)).fetchall()
            for task in tasks:
                assert task[0] == "doing"
    finally:
        sys.argv = original_argv

def test_consolidated_task_restart():
    """Test restarting tasks using the new consolidated command."""
    # Add and mark tasks as done
    jrnl_app.add_task(["Test task 1"])
    jrnl_app.add_task(["Test task 2"])
    
    # Get the task IDs
    with sqlite3.connect(DB_FILE) as conn:
        task_ids = [row[0] for row in conn.execute("SELECT id FROM items WHERE status IN ('todo', 'doing', 'waiting', 'done') ORDER BY id ASC").fetchall()]
        assert len(task_ids) == 2
        task1_id, task2_id = task_ids
    
    # Mark tasks as done
    jrnl_app.update_task_status([task1_id, task2_id], "done", "Completed")
    
    # Simulate command line arguments for "jrnl restart task <id>,<id>"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "restart", "task", f"{task1_id},{task2_id}"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the tasks were updated back to 'todo' status
        assert "Updated 2 tasks to undone" in output
        
        # Verify the status change in DB
        with sqlite3.connect(DB_FILE) as conn:
            tasks = conn.execute("""
                SELECT status 
                FROM items
                WHERE id IN (?,?)
            """, (task1_id, task2_id)).fetchall()
            for task in tasks:
                assert task[0] == "todo"
    finally:
        sys.argv = original_argv

def test_consolidated_task_waiting():
    """Test marking tasks as waiting using the new consolidated command."""
    # Add tasks
    jrnl_app.add_task(["Test task 1"])
    jrnl_app.add_task(["Test task 2"])
    
    # Get the task IDs
    with sqlite3.connect(DB_FILE) as conn:
        task_ids = [row[0] for row in conn.execute("SELECT id FROM items WHERE status IN ('todo', 'doing', 'waiting', 'done') ORDER BY id ASC").fetchall()]
        assert len(task_ids) == 2
        task1_id, task2_id = task_ids
    
    # Simulate command line arguments for "jrnl waiting task <id>,<id>"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "waiting", "task", f"{task1_id},{task2_id}"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the tasks were updated to 'waiting' status
        assert "Updated 2 tasks to waiting" in output
        
        # Verify the status change in DB
        with sqlite3.connect(DB_FILE) as conn:
            tasks = conn.execute("""
                SELECT status 
                FROM items
                WHERE id IN (?,?)
            """, (task1_id, task2_id)).fetchall()
            for task in tasks:
                assert task[0] == "waiting"
    finally:
        sys.argv = original_argv

def test_consolidated_task_done_with_note():
    """Test completing tasks with note using the new consolidated command."""
    # Add tasks
    jrnl_app.add_task(["Test task 1"])
    jrnl_app.add_task(["Test task 2"])
    
    # Get the task IDs
    with sqlite3.connect(DB_FILE) as conn:
        task_ids = [row[0] for row in conn.execute("SELECT id FROM items WHERE status IN ('todo', 'doing', 'waiting', 'done') ORDER BY id ASC").fetchall()]
        assert len(task_ids) == 2
        task1_id, task2_id = task_ids
    
    # Simulate command line arguments for "jrnl done task <id>,<id> <note text>"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "done", "task", f"{task1_id},{task2_id}", "Completed successfully"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the tasks were updated to 'done' status
        assert "Updated 2 tasks to done" in output
        
        # Verify the status change in DB
        with sqlite3.connect(DB_FILE) as conn:
            tasks = conn.execute("""
                SELECT status, completion_date
                FROM items
                WHERE id IN (?,?)
            """, (task1_id, task2_id)).fetchall()
            for task in tasks:
                assert task[0] == "done"
                assert task[1] is not None  # Completion date should be set
        
        # Verify the note was added as standalone notes (current behavior)
        with sqlite3.connect(DB_FILE) as conn:
            # Count notes with the expected text
            notes = conn.execute("""
                SELECT title
                FROM items
                WHERE title = 'Completed successfully' AND status = 'note'
            """).fetchall()
            assert len(notes) >= 2  # At least one note for each task
    finally:
        sys.argv = original_argv

def test_delete_task_still_works_with_rm():
    """Test that deleting tasks still works with the rm command."""
    # Add tasks
    jrnl_app.add_task(["Test task 1"])
    jrnl_app.add_task(["Test task 2"])
    
    # Get the task IDs
    with sqlite3.connect(DB_FILE) as conn:
        task_ids = [row[0] for row in conn.execute("SELECT id FROM items WHERE status IN ('todo', 'doing', 'waiting', 'done') ORDER BY id ASC").fetchall()]
        assert len(task_ids) == 2
        task1_id, task2_id = task_ids
    
    # Simulate command line arguments for "jrnl rm task <id>,<id>"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "rm", f"{task1_id},{task2_id}"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the tasks were deleted
        assert "Deleted 2 tasks" in output
        
        # Verify the tasks were deleted from DB
        with sqlite3.connect(DB_FILE) as conn:
            remaining_tasks = conn.execute("SELECT id FROM items WHERE id IN (?,?)", (task1_id, task2_id)).fetchall()
            assert len(remaining_tasks) == 0
    finally:
        sys.argv = original_argv

def test_consolidated_show_note():
    """Test showing a specific note using the new consolidated command."""
    # Add a note
    jrnl_app.add_note([], "Test specific note")
    
    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM items WHERE title='Test specific note' AND status='note'").fetchone()
        assert note is not None
        note_id = note[0]
    
    # Simulate command line arguments for "jrnl show note <id>"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "note", str(note_id)]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the specific note is displayed
        assert "Test specific note" in output
    finally:
        sys.argv = original_argv

def test_consolidated_show_task():
    """Test showing a specific task using the new consolidated command."""
    # Add a task
    jrnl_app.add_task(["Test specific task"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM items WHERE title='Test specific task' AND status='todo'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Simulate command line arguments for "jrnl show task <id>"
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "task", str(task_id)]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Check that the specific task is displayed
        assert "Test specific task" in output
    finally:
        sys.argv = original_argv

def test_old_done_command_removed():
    """Test that the old 'jrnl done' command has been removed."""
    # Simulate command line arguments for "jrnl done" (old command)
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "done"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should show error message about removed command
        assert "Error" in output or "help" in output
    finally:
        sys.argv = original_argv

def test_old_status_command_removed():
    """Test that the old 'jrnl status' command has been removed."""
    # Simulate command line arguments for "jrnl status" (old command)
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "status"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should show error message about removed command
        assert "Error" in output or "help" in output
    finally:
        sys.argv = original_argv

def test_old_due_command_removed():
    """Test that the old 'jrnl due' command has been removed."""
    # Simulate command line arguments for "jrnl due" (old command)
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "due"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should show error message about removed command
        assert "Error" in output or "help" in output
    finally:
        sys.argv = original_argv

def test_old_restart_command_removed():
    """Test that the old 'jrnl restart' command has been removed."""
    # Simulate command line arguments for "jrnl restart 1" (old command)
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "restart", "1"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should show error message about removed command
        assert "Error" in output or "help" in output
    finally:
        sys.argv = original_argv

def test_old_start_command_removed():
    """Test that the old 'jrnl start' command has been removed."""
    # Simulate command line arguments for "jrnl start 1" (old command)
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "start", "1"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should show error message about removed command
        assert "Error" in output or "help" in output
    finally:
        sys.argv = original_argv

def test_old_waiting_command_removed():
    """Test that the old 'jrnl waiting' command has been removed."""
    # Simulate command line arguments for "jrnl waiting 1" (old command)
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "waiting", "1"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should show error message about removed command
        assert "Error" in output or "help" in output
    finally:
        sys.argv = original_argv

def test_old_done_with_text_command_removed():
    """Test that the old 'jrnl done 1 note text' command has been removed."""
    # Simulate command line arguments for "jrnl done 1 note text" (old command)
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "done", "1", "Test completion note"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should show error message about removed command
        assert "Error" in output or "help" in output
    finally:
        sys.argv = original_argv

def test_delete_command_removed():
    """Test that the 'jrnl delete task' command has been removed."""
    # Add a task first
    jrnl_app.add_task(["Test task to delete"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM items WHERE title='Test task to delete' AND status='todo'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Simulate command line arguments for "jrnl delete task <id>" (old command)
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "delete", "task", str(task_id)]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should show error message about removed command
        assert "Error" in output or "help" in output
    finally:
        sys.argv = original_argv

def test_old_rm_task_command_removed():
    """Test that the old 'jrnl rm t<id>' command has been removed."""
    # Add a task first
    jrnl_app.add_task(["Test task to delete"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM items WHERE title='Test task to delete' AND status='todo'").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Simulate command line arguments for "jrnl rm t<id>" (old command)
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "rm", f"t{task_id}"]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should show error message about removed command
        assert "Old syntax 'j rm t<id>" in output
        assert "has been removed" in output
    finally:
        sys.argv = original_argv

def test_note_id_command_shows_details():
    """Test that 'jrnl note <id>' command shows note details."""
    # Add a note first
    jrnl_app.add_note([], "Test note to view")
    
    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM items WHERE title='Test note to view' AND status='note'").fetchone()
        assert note is not None
        note_id = note[0]
    
    # Simulate command line arguments for "jrnl note <id>" (old command)
    original_argv = sys.argv.copy()
    sys.argv = ["jrnl_app.py", "-d", DB_FILE, "note", str(note_id)]
    
    try:
        f = StringIO()
        with redirect_stdout(f):
            jrnl_app.main()
        output = f.getvalue()
        
        # Should show error message about removed command
        assert "Error" in output or "help" in output
    finally:
        sys.argv = original_argv

if __name__ == "__main__":
    test_consolidated_view_task_due()
    test_consolidated_view_task_status()
    test_consolidated_view_task_done()
    test_consolidated_task_start()
    test_consolidated_task_restart()
    test_consolidated_task_waiting()
    test_consolidated_task_done_with_note()
    test_delete_task_still_works_with_rm()
    test_consolidated_show_note()
    test_consolidated_show_task()
    test_old_done_command_removed()
    test_old_status_command_removed()
    test_old_due_command_removed()
    test_old_restart_command_removed()
    test_old_start_command_removed()
    test_old_waiting_command_removed()
    test_old_done_with_text_command_removed()
    test_delete_command_removed()
    test_old_rm_task_command_removed()
    test_old_note_id_command_removed()
    print("All additional consolidated command tests passed!")