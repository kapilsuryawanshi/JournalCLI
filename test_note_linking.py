"""Pytest unit tests for the note linking functionality in jrnl application."""

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

def test_link_notes_successfully():
    """Test linking two notes together"""
    # Add two notes
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")
    
    # Get the note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()
        assert len(notes) == 2
        note1_id = notes[0][0]
        note2_id = notes[1][0]
    
    # Link the notes
    result = jrnl_app.link_notes(note1_id, note2_id)
    assert result is True
    
    # Verify the link exists in the database
    with sqlite3.connect(DB_FILE) as conn:
        link = conn.execute("SELECT note1_id, note2_id FROM note_links WHERE (note1_id=? AND note2_id=?) OR (note1_id=? AND note2_id=?)", 
                            (note1_id, note2_id, note2_id, note1_id)).fetchone()
        assert link is not None
        # The link should be stored with the smaller ID first
        expected_note1_id = min(note1_id, note2_id)
        expected_note2_id = max(note1_id, note2_id)
        assert link[0] == expected_note1_id
        assert link[1] == expected_note2_id

def test_link_notes_already_linked():
    """Test linking two notes that are already linked"""
    # Add two notes
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")
    
    # Get the note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()
        assert len(notes) == 2
        note1_id = notes[0][0]
        note2_id = notes[1][0]
    
    # Link the notes for the first time
    result1 = jrnl_app.link_notes(note1_id, note2_id)
    assert result1 is True
    
    # Capture output to verify the message
    f = StringIO()
    with redirect_stdout(f):
        # Link the notes again (should succeed with message)
        result2 = jrnl_app.link_notes(note1_id, note2_id)
    output = f.getvalue()
    
    assert result2 is True
    assert f"Notes {note1_id} and {note2_id} are already linked" in output

def test_link_notes_nonexistent_note():
    """Test linking when one note doesn't exist"""
    # Add one note
    jrnl_app.add_note([], "First note")
    
    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM notes").fetchone()
        assert note is not None
        note1_id = note[0]
    
    # Try to link with a non-existent note ID
    f = StringIO()
    with redirect_stdout(f):
        result = jrnl_app.link_notes(note1_id, 999)  # Non-existent note
    output = f.getvalue()
    
    assert result is False
    assert "Error: Note with ID 999 does not exist" in output

def test_link_notes_self():
    """Test that a note can't be linked to itself"""
    # Add one note
    jrnl_app.add_note([], "Test note")
    
    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM notes").fetchone()
        assert note is not None
        note_id = note[0]
    
    # Try to link the note to itself
    f = StringIO()
    with redirect_stdout(f):
        result = jrnl_app.link_notes(note_id, note_id)
    output = f.getvalue()
    
    assert result is False
    assert f"Error: Cannot link a note to itself (id: {note_id})" in output

def test_unlink_notes_successfully():
    """Test unlinking two notes that are linked"""
    # Add two notes
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")
    
    # Get the note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()
        assert len(notes) == 2
        note1_id = notes[0][0]
        note2_id = notes[1][0]
    
    # Link the notes first
    result1 = jrnl_app.link_notes(note1_id, note2_id)
    assert result1 is True
    
    # Verify the link exists
    with sqlite3.connect(DB_FILE) as conn:
        link = conn.execute("SELECT * FROM note_links WHERE (note1_id=? AND note2_id=?) OR (note1_id=? AND note2_id=?)", 
                            (note1_id, note2_id, note2_id, note1_id)).fetchone()
        assert link is not None
    
    # Unlink the notes
    f = StringIO()
    with redirect_stdout(f):
        result2 = jrnl_app.unlink_notes(note1_id, note2_id)
    output = f.getvalue()
    
    assert result2 is True
    assert f"Unlinked notes {note1_id} and {note2_id}" in output
    
    # Verify the link no longer exists
    with sqlite3.connect(DB_FILE) as conn:
        link = conn.execute("SELECT * FROM note_links WHERE (note1_id=? AND note2_id=?) OR (note1_id=? AND note2_id=?)", 
                            (note1_id, note2_id, note2_id, note1_id)).fetchone()
        assert link is None

def test_unlink_notes_not_linked():
    """Test unlinking two notes that are not linked"""
    # Add two notes
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")
    
    # Get the note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()
        assert len(notes) == 2
        note1_id = notes[0][0]
        note2_id = notes[1][0]
    
    # Try to unlink notes that aren't linked
    f = StringIO()
    with redirect_stdout(f):
        result = jrnl_app.unlink_notes(note1_id, note2_id)
    output = f.getvalue()
    
    assert result is True  # Should return True even if not linked
    assert f"Notes {note1_id} and {note2_id} were not linked" in output

def test_unlink_notes_nonexistent_note():
    """Test unlinking when one note doesn't exist"""
    # Add one note
    jrnl_app.add_note([], "First note")
    
    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM notes").fetchone()
        assert note is not None
        note1_id = note[0]
    
    # Try to unlink with a non-existent note ID
    f = StringIO()
    with redirect_stdout(f):
        result = jrnl_app.unlink_notes(note1_id, 999)  # Non-existent note
    output = f.getvalue()
    
    assert result is False
    assert "Error: Note with ID 999 does not exist" in output

def test_show_note_details_with_links():
    """Test viewing a note and its linked notes"""
    # Add three notes
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")
    jrnl_app.add_note([], "Third note")
    
    # Get the note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()
        assert len(notes) == 3
        note1_id = notes[0][0]
        note2_id = notes[1][0]
        note3_id = notes[2][0]
    
    # Link notes 1 and 2
    result1 = jrnl_app.link_notes(note1_id, note2_id)
    assert result1 is True
    
    # Link notes 1 and 3
    result2 = jrnl_app.link_notes(note1_id, note3_id)
    assert result2 is True
    
    # Show details for note 1 (should show linked notes)
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_note_details(note1_id)
    output = f.getvalue()
    
    # Check that the note itself is displayed
    assert f"Note {note1_id}: First note" in output
    
    # Check that both linked notes are displayed
    assert f"Note {note2_id}: Second note" in output
    assert f"Note {note3_id}: Third note" in output

def test_show_note_details_no_links():
    """Test viewing a note that has no linked notes"""
    # Add one note
    jrnl_app.add_note([], "Single note")
    
    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM notes").fetchone()
        assert note is not None
        note_id = note[0]
    
    # Show details for the note (should show no links message)
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_note_details(note_id)
    output = f.getvalue()
    
    # Check that the note itself is displayed
    assert f"Note {note_id}: Single note" in output
    
    # Check that no linked notes message is displayed
    assert "No linked notes found." in output

def test_show_note_details_nonexistent_note():
    """Test viewing a note that doesn't exist"""
    # Try to show details for a non-existent note ID
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_note_details(999)
    output = f.getvalue()
    
    assert "Error: Note with ID 999 does not exist" in output

def test_delete_note_removes_links():
    """Test that deleting a note also removes its links"""
    # Add two notes
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")
    
    # Get the note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()
        assert len(notes) == 2
        note1_id = notes[0][0]
        note2_id = notes[1][0]
    
    # Link the notes
    result1 = jrnl_app.link_notes(note1_id, note2_id)
    assert result1 is True
    
    # Verify the link exists
    with sqlite3.connect(DB_FILE) as conn:
        links_before = conn.execute("SELECT * FROM note_links").fetchall()
        assert len(links_before) == 1
    
    # Delete one of the notes
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.delete_note([note1_id])
    output = f.getvalue()
    
    # Verify that the note was deleted
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT * FROM notes WHERE id=?", (note1_id,)).fetchone()
        assert note is None
    
    # Verify that the link was also deleted
    with sqlite3.connect(DB_FILE) as conn:
        links_after = conn.execute("SELECT * FROM note_links").fetchall()
        assert len(links_after) == 0

def test_show_note_details_with_task():
    """Test viewing a note that is associated with a task"""
    # Add a task
    jrnl_app.add_task(["Test task"])
    
    # Get the task ID
    with sqlite3.connect(DB_FILE) as conn:
        task = conn.execute("SELECT id FROM tasks").fetchone()
        assert task is not None
        task_id = task[0]
    
    # Add a note to the task
    jrnl_app.add_note([task_id], "Note for task")
    
    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM notes WHERE task_id=?", (task_id,)).fetchone()
        assert note is not None
        note_id = note[0]
    
    # Link with another note
    jrnl_app.add_note([], "Other note")
    with sqlite3.connect(DB_FILE) as conn:
        other_note = conn.execute("SELECT id FROM notes WHERE text='Other note'").fetchone()
        assert other_note is not None
        other_note_id = other_note[0]
    
    # Link the notes
    result = jrnl_app.link_notes(note_id, other_note_id)
    assert result is True
    
    # Show details for the note linked to the task
    f = StringIO()
    with redirect_stdout(f):
        jrnl_app.show_note_details(note_id)
    output = f.getvalue()
    
    # Check that the note with task association is displayed
    assert f"Note {note_id}: Note for task (for task: {task_id}. Test task)" in output
    
    # Check that the linked note is displayed
    assert f"Note {other_note_id}: Other note" in output

if __name__ == "__main__":
    test_link_notes_successfully()
    test_link_notes_already_linked()
    test_link_notes_nonexistent_note()
    test_link_notes_self()
    test_unlink_notes_successfully()
    test_unlink_notes_not_linked()
    test_unlink_notes_nonexistent_note()
    test_show_note_details_with_links()
    test_show_note_details_no_links()
    test_show_note_details_nonexistent_note()
    test_delete_note_removes_links()
    test_show_note_details_with_task()
    print("All note linking tests passed!")