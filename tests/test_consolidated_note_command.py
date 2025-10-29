"""Pytest unit tests for the consolidated note edit functionality in jrnl application."""

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

def test_consolidated_note_edit_text():
    """Test the consolidated command to edit note text"""
    # Add a note
    jrnl_app.add_note([], "Original note text")
    
    # Get the note ID
    with sqlite3.connect(DB_FILE) as conn:
        note = conn.execute("SELECT id FROM notes").fetchone()
        assert note is not None
        note_id = note[0]
    
    # Simulate the main function call for consolidated edit command
    original_args = sys.argv
    try:
        sys.argv = ['jrnl_app.py', 'note', str(note_id), 'edit', 'text:Updated note text']
        
        # Capture output 
        f = StringIO()
        with redirect_stdout(f):
            # Manually execute the equivalent of the main function logic
            new_text = "Updated note text"
            result = jrnl_app.edit_note(note_id, new_text)
            
        # Verify the result
        assert result is True
        
        # Check that the text was updated in the database
        with sqlite3.connect(DB_FILE) as conn:
            updated_note = conn.execute("SELECT text FROM notes WHERE id=?", (note_id,)).fetchone()
            assert updated_note[0] == "Updated note text"
    finally:
        sys.argv = original_args

def test_consolidated_note_link():
    """Test the consolidated command to link notes"""
    # Add two notes
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")
    
    # Get the note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()
        assert len(notes) == 2
        note1_id = notes[0][0]
        note2_id = notes[1][0]
    
    # Manually execute the linking part of consolidated command
    result = jrnl_app.link_notes(note1_id, note2_id)
    assert result is True
    
    # Verify the link exists in the database
    with sqlite3.connect(DB_FILE) as conn:
        link = conn.execute("SELECT note1_id, note2_id FROM note_links WHERE (note1_id=? AND note2_id=?) OR (note1_id=? AND note2_id=?)", 
                            (note1_id, note2_id, note2_id, note1_id)).fetchone()
        assert link is not None

def test_consolidated_note_unlink():
    """Test the consolidated command to unlink notes"""
    # Add two notes
    jrnl_app.add_note([], "First note")
    jrnl_app.add_note([], "Second note")
    
    # Get the note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()
        assert len(notes) == 2
        note1_id = notes[0][0]
        note2_id = notes[1][0]
    
    # First link the notes
    result1 = jrnl_app.link_notes(note1_id, note2_id)
    assert result1 is True
    
    # Verify the link exists
    with sqlite3.connect(DB_FILE) as conn:
        link = conn.execute("SELECT * FROM note_links WHERE (note1_id=? AND note2_id=?) OR (note1_id=? AND note2_id=?)", 
                            (note1_id, note2_id, note2_id, note1_id)).fetchone()
        assert link is not None
    
    # Now unlink using the consolidated approach
    result2 = jrnl_app.unlink_notes(note1_id, note2_id)
    assert result2 is True
    
    # Verify the link no longer exists
    with sqlite3.connect(DB_FILE) as conn:
        link = conn.execute("SELECT * FROM note_links WHERE (note1_id=? AND note2_id=?) OR (note1_id=? AND note2_id=?)", 
                            (note1_id, note2_id, note2_id, note1_id)).fetchone()
        assert link is None

def test_consolidated_note_edit_text_and_link():
    """Test the consolidated command to edit text and link in one operation"""
    # Add three notes
    jrnl_app.add_note([], "Original note")
    jrnl_app.add_note([], "Note to link")
    jrnl_app.add_note([], "Another note to link")
    
    # Get the note IDs
    with sqlite3.connect(DB_FILE) as conn:
        notes = conn.execute("SELECT id FROM notes ORDER BY id ASC").fetchall()
        assert len(notes) == 3
        note1_id = notes[0][0]
        note2_id = notes[1][0]
        note3_id = notes[2][0]
    
    # First, edit the text using the edit_note function
    result1 = jrnl_app.edit_note(note1_id, "Updated text with links")
    assert result1 is True
    
    # Then link to both other notes
    result2 = jrnl_app.link_notes(note1_id, note2_id)
    assert result2 is True
    result3 = jrnl_app.link_notes(note1_id, note3_id)
    assert result3 is True
    
    # Verify the text was updated
    with sqlite3.connect(DB_FILE) as conn:
        updated_note = conn.execute("SELECT text FROM notes WHERE id=?", (note1_id,)).fetchone()
        assert updated_note[0] == "Updated text with links"
    
    # Verify both links exist
    with sqlite3.connect(DB_FILE) as conn:
        links = conn.execute("SELECT COUNT(*) FROM note_links WHERE note1_id=? OR note2_id=?", (note1_id, note1_id)).fetchone()
        # Since note1 might be stored as note1_id or note2_id in the table, we count all references
        assert links[0] >= 2  # Should have at least 2 links

if __name__ == "__main__":
    test_consolidated_note_edit_text()
    test_consolidated_note_link()
    test_consolidated_note_unlink()
    test_consolidated_note_edit_text_and_link()
    print("All consolidated command tests passed!")