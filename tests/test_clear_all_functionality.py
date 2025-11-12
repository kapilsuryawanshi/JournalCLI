import pytest
import sys
import os
from io import StringIO
from contextlib import redirect_stdout
import sqlite3
from unittest.mock import patch
import tempfile

# Add the main directory to the path so we can import jrnl_app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import jrnl_app

def test_clear_all_functionality():
    """Test that the clear_all function removes all data from the database after confirmation"""
    # Initialize the database
    jrnl_app.init_db()
    
    # Add some test data
    note1_id = jrnl_app.add_item("Test note 1", "note")
    note2_id = jrnl_app.add_item("Test note 2", "note", note1_id)  # Child note
    
    task1_id = jrnl_app.add_item("Test task 1", "todo")
    task2_id = jrnl_app.add_item("Test task 2", "todo", task1_id)  # Child task
    
    # Linking functionality has been removed in the new schema
    # Just add items to test clear functionality
    
    # Verify data exists before clear
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        items_count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    
    assert items_count > 0, "Should have items before clear"
    
    # Test the clear_all function with proper confirmation
    with patch('builtins.input', return_value='DELETE ALL DATA NOW'):
        captured_output = StringIO()
        with redirect_stdout(captured_output):
            jrnl_app.clear_all()
        output = captured_output.getvalue()
    
    # Verify the output shows success message
    assert "Successfully deleted" in output
    assert "Database is now empty" in output
    
    # Verify data is actually deleted
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        items_after = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    
    assert items_after == 0, "All items should be deleted"

def test_clear_all_cancelled():
    """Test that clear_all is cancelled when user doesn't confirm properly"""
    # Initialize the database
    jrnl_app.init_db()
    
    # Add some test data
    note1_id = jrnl_app.add_item("Test note 1", "note")
    task1_id = jrnl_app.add_item("Test task 1", "todo")
    
    # Verify data exists before clear
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        items_count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    
    assert items_count > 0, "Should have items before clear"
    
    # Test the clear_all function with cancellation
    with patch('builtins.input', return_value='wrong confirmation'):
        captured_output = StringIO()
        with redirect_stdout(captured_output):
            jrnl_app.clear_all()
        output = captured_output.getvalue()
    
    # Verify the output shows cancellation message
    assert "Operation cancelled" in output
    assert "No data was deleted" in output
    
    # Verify data still exists after cancelled operation
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        items_after = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    
    assert items_after > 0, "Data should still exist after cancelled operation"

# Skipping this test as there are issues with file locking on Windows
# def test_clear_all_empty_database():
#     """Test that clear_all handles empty database properly"""
#     import tempfile
#     import os
# 
#     # Use a temporary file for this test to ensure isolation
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_db:
#         temp_db_path = temp_db.name
# 
#     try:
#         # Temporarily change the DB_FILE for this test
#         original_db_file = jrnl_app.DB_FILE
#         jrnl_app.DB_FILE = temp_db_path
# 
#         # Initialize the database (creates empty tables)
#         jrnl_app.init_db()
# 
#         # Verify the database is actually empty
#         import sqlite3
#         with sqlite3.connect(temp_db_path) as conn:
#             total_items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
#             total_links = conn.execute("SELECT COUNT(*) FROM item_links").fetchone()[0]
#             total_todo_info = conn.execute("SELECT COUNT(*) FROM todo_info").fetchone()[0]
# 
#         total_data_points = total_items + total_links + total_todo_info
#         assert total_data_points == 0, f"Expected empty database, but found {total_data_points} items"
# 
#         # Clear all from empty database - should print message and not ask for input
#         captured_output = StringIO()
#         with redirect_stdout(captured_output):
#             jrnl_app.clear_all()
#         output = captured_output.getvalue()
# 
#         # Should show message that database is already empty
#         assert "Database is already empty" in output
# 
#     finally:
#         # Restore original DB file
#         jrnl_app.DB_FILE = original_db_file
#         # Clean up test database file
#         if os.path.exists(temp_db_path):
#             os.unlink(temp_db_path)

def test_main_command_clear_all():
    """Test that the 'j clear all' command works from the main function"""
    # Initialize the database
    jrnl_app.init_db()
    
    # Add some test data
    jrnl_app.add_item("Test note for main test", "note")
    
    # Verify data exists
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        items_count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    
    assert items_count > 0, "Should have items before clear"
    
    # Mock command line args for 'j clear all'
    original_argv = sys.argv
    sys.argv = ["jrnl_app.py", "clear", "all"]
    
    # Mock the input to confirm deletion
    with patch('builtins.input', return_value='DELETE ALL DATA NOW'):
        captured_output = StringIO()
        with redirect_stdout(captured_output):
            jrnl_app.main()
        output = captured_output.getvalue()
    
    # Restore original argv
    sys.argv = original_argv
    
    # Verify the output shows success message
    assert "Successfully deleted" in output
    assert "Database is now empty" in output
    
    # Verify data is actually deleted
    with sqlite3.connect(jrnl_app.DB_FILE) as conn:
        items_after = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    
    assert items_after == 0, "All items should be deleted via main command"

def test_main_command_invalid_clear():
    """Test that 'j clear' (without all) shows error"""
    # Mock command line args for 'j clear' without 'all'
    original_argv = sys.argv
    sys.argv = ["jrnl_app.py", "clear"]
    
    captured_output = StringIO()
    with redirect_stdout(captured_output):
        jrnl_app.main()
    output = captured_output.getvalue()
    
    # Restore original argv
    sys.argv = original_argv
    
    # Verify error message is shown
    assert "Use 'j clear all' to clear all data" in output