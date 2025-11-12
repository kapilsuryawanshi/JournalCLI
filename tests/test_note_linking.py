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
        notes = conn.execute("SELECT id FROM items WHERE type='note' ORDER BY id ASC").fetchall()
        assert len(notes) == 2
        note1_id = notes[0][0]
        note2_id = notes[1][0]

    # Link the notes
    result = jrnl_app.link_notes(note1_id, note2_id)
    assert result is True

    # Verify the link exists in the database
    with sqlite3.connect(DB_FILE) as conn:
        link = conn.execute("SELECT item1_id, item2_id FROM item_links WHERE (item1_id=? AND item2_id=?) OR (item1_id=? AND item2_id=?)",
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
        notes = conn.execute("SELECT id FROM items WHERE type='note' ORDER BY id ASC").fetchall()
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
    assert f"Items {note1_id} and {note2_id} are already linked" in output

def test_link_notes_nonexistent_note():
    """Test linking when one note doesn't exist"""
    # Add one note
    jrnl_app.add_note([], "First note")

    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM items WHERE type='note'").fetchone()
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
        note = conn.execute("SELECT id FROM items WHERE type='note'").fetchone()
        assert note is not None
        note_id = note[0]

    # Try to link the note to itself
    f = StringIO()
    with redirect_stdout(f):
        result = jrnl_app.link_notes(note_id, note_id)
    output = f.getvalue()

    assert result is False
    assert f"Error: Cannot link an item to itself (id: {note_id})" in output

def test_unlink_notes_successfully():
    """Test unlinking two notes that are linked"""
    # Add two notes
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")

    # Get the note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM items WHERE type='note' ORDER BY id ASC").fetchall()
        assert len(notes) == 2
        note1_id = notes[0][0]
        note2_id = notes[1][0]

    # Link the notes first
    result1 = jrnl_app.link_notes(note1_id, note2_id)
    assert result1 is True

    # Verify the link exists
    with sqlite3.connect(DB_FILE) as conn:
        link = conn.execute("SELECT * FROM item_links WHERE (item1_id=? AND item2_id=?) OR (item1_id=? AND item2_id=?)",
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
        link = conn.execute("SELECT * FROM item_links WHERE (item1_id=? AND item2_id=?) OR (item1_id=? AND item2_id=?)",
                            (note1_id, note2_id, note2_id, note1_id)).fetchone()
        assert link is None

def test_unlink_notes_not_linked():
    """Test unlinking two notes that are not linked"""
    # Add two notes
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")

    # Get the note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM items WHERE type='note' ORDER BY id ASC").fetchall()
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
        note = conn.execute("SELECT id FROM items WHERE type='note'").fetchone()
        assert note is not None
        note1_id = note[0]

    # Try to unlink with a non-existent note ID
    f = StringIO()
    with redirect_stdout(f):
        result = jrnl_app.unlink_notes(note1_id, 999)  # Non-existent note
    output = f.getvalue()

    assert result is False
    assert "Error: Note with ID 999 does not exist" in output

def test_delete_note_removes_links():
    """Test that deleting a note also removes its links"""
    # Add two notes
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")

    # Get the note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM items WHERE type='note' ORDER BY id ASC").fetchall()
        assert len(notes) == 2
        note1_id = notes[0][0]
        note2_id = notes[1][0]

    # Link the notes
    result1 = jrnl_app.link_notes(note1_id, note2_id)
    assert result1 is True

    # Verify the link exists
    with sqlite3.connect(DB_FILE) as conn:
        links_before = conn.execute("SELECT * FROM item_links").fetchall()
        assert len(links_before) == 1

    # Delete one of the notes
    f = StringIO()
    with redirect_stdout(f):
        # Mock the input() function to return 'yes' for confirmation
        import builtins
        original_input = builtins.input
        builtins.input = lambda prompt: 'yes'
        try:
            jrnl_app.delete_item([note1_id])
        finally:
            builtins.input = original_input
    output = f.getvalue()

    # Verify that the note was deleted
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT * FROM items WHERE id=? AND type='note'", (note1_id,)).fetchone()
        assert note is None

    # Verify that the link was also deleted
    with sqlite3.connect(DB_FILE) as conn:
        links_after = conn.execute("SELECT * FROM item_links").fetchall()
        assert len(links_after) == 0

if __name__ == "__main__":
    test_link_notes_successfully()
    test_link_notes_already_linked()
    test_link_notes_nonexistent_note()
    test_link_notes_self()
    test_unlink_notes_successfully()
    test_unlink_notes_not_linked()
    test_unlink_notes_nonexistent_note()
    test_delete_note_removes_links()
    print("All note linking tests passed!")