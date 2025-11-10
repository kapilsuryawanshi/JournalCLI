#!/usr/bin/env python3
"""
Test script to verify the refactoring works correctly
"""
import tempfile
import os
import sys
import sqlite3
from io import StringIO
from contextlib import redirect_stdout

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jrnl_app

def test_function_removal():
    """Test that only delete_item function exists"""
    print("Testing function removal...")
    
    # Check which delete functions exist
    functions_exist = []
    if hasattr(jrnl_app, 'delete_item'):
        functions_exist.append('delete_item')
    if hasattr(jrnl_app, 'delete_note'):
        functions_exist.append('delete_note')
    if hasattr(jrnl_app, 'delete_task'):
        functions_exist.append('delete_task')
    
    print(f"Delete functions found: {functions_exist}")
    
    # Verify we only have delete_item
    if functions_exist == ['delete_item']:
        print("SUCCESS: Only delete_item function exists")
        return True
    else:
        print(f"FAILURE: Expected ['delete_item'], got {functions_exist}")
        return False

def test_database_operations():
    """Test basic database operations with unified schema"""
    print("\nTesting database operations...")
    
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        db_file = tmp_file.name

    try:
        # Set the global DB_FILE to our temp file
        original_db = jrnl_app.DB_FILE
        jrnl_app.DB_FILE = db_file

        # Initialize the database
        jrnl_app.init_db()

        # Add a task and a note
        task_id = jrnl_app.add_item('Test task', 'todo')
        note_id = jrnl_app.add_item('Test note', 'note')

        print(f"Added task with ID: {task_id}")
        print(f"Added note with ID: {note_id}")

        # Verify they were added
        task = jrnl_app.get_item_by_id(task_id)
        note = jrnl_app.get_item_by_id(note_id)

        print(f"Task retrieved: {task}")
        print(f"Note retrieved: {note}")

        # Test that both items exist
        if task is not None and note is not None:
            print("SUCCESS: Items were added and retrieved correctly")
        else:
            print("FAILURE: Items were not retrieved correctly")
            return False

        # Restore original DB_FILE
        jrnl_app.DB_FILE = original_db

        # Clean up
        jrnl_app.DB_FILE = original_db  # Make sure we're not holding the file
        try:
            os.unlink(db_file)
        except PermissionError:
            # On Windows, the file might still be locked, which is normal
            pass
        
        return True

    except Exception as e:
        print(f"FAILURE: Error in database operations: {e}")
        # Restore original DB_FILE
        jrnl_app.DB_FILE = original_db
        # Clean up (try to remove the temp file but ignore errors)
        try:
            if os.path.exists(db_file):
                os.unlink(db_file)
        except:
            pass  # On Windows, might not be able to delete if file is locked
        return False

def main():
    print("Testing refactoring changes...")
    
    success = True
    success &= test_function_removal()
    success &= test_database_operations()
    
    if success:
        print("\nAll tests passed! Refactoring is working correctly.")
        return 0
    else:
        print("\nSome tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())