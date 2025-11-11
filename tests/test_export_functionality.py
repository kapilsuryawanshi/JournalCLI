"""Test suite for the export functionality."""

import sqlite3
import tempfile
import os
import sys
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

def test_export_single_note():
    """Test exporting a single note."""
    # Add a single note
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_note([], "Test note")
    output = f.getvalue()
    assert "Added standalone note" in output

    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM items WHERE title='Test note'").fetchone()
        assert note is not None
        note_id = note[0]

    # Export the note to a temporary file
    export_file = tempfile.mktemp()
    jrnl_app.export_to_file(note_id, export_file)

    # Verify the exported content
    with open(export_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "- Test note" in content

    # Clean up
    if os.path.exists(export_file):
        os.remove(export_file)

def test_export_single_todo():
    """Test exporting a single todo."""
    # Add a single todo
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_task(["Test task"])
    output = f.getvalue()
    assert "Added task" in output

    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM items WHERE title='Test task'").fetchone()
        assert task is not None
        task_id = task[0]

    # Export the task to a temporary file
    export_file = tempfile.mktemp()
    jrnl_app.export_to_file(task_id, export_file)

    # Verify the exported content
    with open(export_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert ". Test task" in content

    # Clean up
    if os.path.exists(export_file):
        os.remove(export_file)

def test_export_hierarchy():
    """Test exporting a hierarchy of items."""
    # Add a root note
    f = StringIO()
    with redirect_stdout(f):
        note_ids = jrnl_app.add_note([], "Root note")
    output = f.getvalue()
    assert "Added standalone note" in output
    root_note_id = note_ids[0]

    # Add a child note under the root note using parent_note_id parameter
    f = StringIO()
    with redirect_stdout(f):
        child_note_ids = jrnl_app.add_note_under_note(root_note_id, "Child note")
    output = f.getvalue()
    assert "Added note" in output
    child_note_id = child_note_ids

    # Add a grandchild note under the child note
    f = StringIO()
    with redirect_stdout(f):
        grandchild_note_id = jrnl_app.add_note_under_note(child_note_id, "Grandchild note")
    output = f.getvalue()
    assert "Added note" in output

    # Export the hierarchy to a temporary file
    export_file = tempfile.mktemp()
    jrnl_app.export_to_file(root_note_id, export_file)

    # Verify the exported content has proper indentation
    with open(export_file, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.strip().split('\n')
        
        # Should have 3 lines
        assert len(lines) == 3
        
        # First line: Root note with no indentation
        assert lines[0].strip() == "- Root note"
        assert lines[0].startswith("- ")
        
        # Second line: Child note with one level of indentation
        assert lines[1].strip() == "- Child note"
        assert lines[1].startswith('\t- ')
        
        # Third line: Grandchild note with two levels of indentation
        assert lines[2].strip() == "- Grandchild note"
        assert lines[2].startswith('\t\t- ')

    # Clean up
    if os.path.exists(export_file):
        os.remove(export_file)

def test_export_mixed_hierarchy():
    """Test exporting a hierarchy with mixed todo and note items."""
    # Add root todo
    f = StringIO()
    with redirect_stdout(f):
        task_ids = jrnl_app.add_task(["Root task"])
    output = f.getvalue()
    assert "Added task" in output
    root_task_id = task_ids[0]

    # Add a child note under the root task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.add_note([root_task_id], "Child note")
    output = f.getvalue()
    assert "Added note with id" in output

    # Add a child todo under the root task
    f = StringIO()
    with redirect_stdout(f):
        child_task_ids = jrnl_app.add_task(["Child task"])
    output = f.getvalue()
    assert "Added task" in output
    child_task_id = child_task_ids[0]

    # Link the child task to the root task as a child
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE items SET pid=? WHERE id=?", (root_task_id, child_task_id))

    # Export the hierarchy to a temporary file
    export_file = tempfile.mktemp()
    jrnl_app.export_to_file(root_task_id, export_file)

    # Verify the exported content
    with open(export_file, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.strip().split('\n')
        
        # Should have 3 lines
        assert len(lines) == 3
        
        # First line: Root task
        assert lines[0].strip() == ". Root task"
        assert lines[0].startswith(". ")
        
        # Second and third lines: Children with proper indentation
        child_lines = [line for line in lines[1:] if line.strip()]
        assert len(child_lines) == 2
        
        # Check that both children have proper indentation
        for line in child_lines:
            assert line.startswith('\t'), f"Line should start with tab: '{line}'"

    # Clean up
    if os.path.exists(export_file):
        os.remove(export_file)

def test_export_completed_task():
    """Test exporting a completed task."""
    # Add a task and mark it as done
    f = StringIO()
    with redirect_stdout(f):
        task_ids = jrnl_app.add_task(["Completed task"])
    output = f.getvalue()
    assert "Added task" in output
    task_id = task_ids[0]

    # Mark the task as done
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "done")
    output = f.getvalue()
    assert "Updated task" in output

    # Export the completed task to a temporary file
    export_file = tempfile.mktemp()
    jrnl_app.export_to_file(task_id, export_file)

    # Verify the exported content shows it as completed
    with open(export_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "x Completed task" in content

    # Clean up
    if os.path.exists(export_file):
        os.remove(export_file)

def test_export_doing_task():
    """Test exporting a doing task."""
    # Add a task and mark it as doing
    f = StringIO()
    with redirect_stdout(f):
        task_ids = jrnl_app.add_task(["Doing task"])
    output = f.getvalue()
    assert "Added task" in output
    task_id = task_ids[0]

    # Mark the task as doing
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "doing")
    output = f.getvalue()
    assert "Updated task" in output

    # Export the doing task to a temporary file
    export_file = tempfile.mktemp()
    jrnl_app.export_to_file(task_id, export_file)

    # Verify the exported content shows it as doing
    with open(export_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "/ Doing task" in content

    # Clean up
    if os.path.exists(export_file):
        os.remove(export_file)

def test_export_waiting_task():
    """Test exporting a waiting task."""
    # Add a task and mark it as waiting
    f = StringIO()
    with redirect_stdout(f):
        task_ids = jrnl_app.add_task(["Waiting task"])
    output = f.getvalue()
    assert "Added task" in output
    task_id = task_ids[0]

    # Mark the task as waiting
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.update_task_status([task_id], "waiting")
    output = f.getvalue()
    assert "Updated task" in output

    # Export the waiting task to a temporary file
    export_file = tempfile.mktemp()
    jrnl_app.export_to_file(task_id, export_file)

    # Verify the exported content shows it as waiting
    with open(export_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "\\ Waiting task" in content

    # Clean up
    if os.path.exists(export_file):
        os.remove(export_file)

def test_export_nonexistent_id():
    """Test exporting with a non-existent ID."""
    export_file = tempfile.mktemp()
    
    # Try to export with a non-existent ID
    result = jrnl_app.export_to_file(99999, export_file)
    
    # Should return False since the item doesn't exist
    assert result is False

    # Clean up
    if os.path.exists(export_file):
        os.remove(export_file)