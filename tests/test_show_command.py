import sys
import os
import sqlite3
import tempfile
import pytest
from io import StringIO
from unittest.mock import patch

# Adding the main directory to sys.path so we can import jrnl_app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import jrnl_app

def test_show_note_by_id():
    """Test the show command with a note ID"""
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
        temp_db_path = temp_db.name

    # Set the global DB_FILE in jrnl_app to our temp database
    original_db_file = jrnl_app.DB_FILE
    jrnl_app.DB_FILE = temp_db_path

    try:
        # Initialize the database
        jrnl_app.init_db()

        # Add a note to the database
        note_id = jrnl_app.add_item("Test note content", "note")

        # Capture the output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            jrnl_app.show_item_details(note_id)

        output = captured_output.getvalue()
        
        # Verify that the output contains the note content and ID
        assert "Test note content" in output
        assert f"(id:{note_id})" in output
        assert "note" in output.lower()

    finally:
        # Clean up: remove the temporary database file
        jrnl_app.DB_FILE = original_db_file
        os.unlink(temp_db_path)


def test_show_task_by_id():
    """Test the show command with a task ID"""
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
        temp_db_path = temp_db.name

    # Set the global DB_FILE in jrnl_app to our temp database
    original_db_file = jrnl_app.DB_FILE
    jrnl_app.DB_FILE = temp_db_path

    try:
        # Initialize the database
        jrnl_app.init_db()

        # Add a task to the database
        task_id = jrnl_app.add_item("Test task content", "todo")

        # Capture the output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            jrnl_app.show_item_details(task_id)

        output = captured_output.getvalue()
        
        # Verify that the output contains the task content and ID
        assert "Test task content" in output
        assert f"(id:{task_id})" in output

    finally:
        # Clean up: remove the temporary database file
        jrnl_app.DB_FILE = original_db_file
        os.unlink(temp_db_path)


def test_show_nonexistent_item():
    """Test the show command with a non-existent ID"""
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
        temp_db_path = temp_db.name

    # Set the global DB_FILE in jrnl_app to our temp database
    original_db_file = jrnl_app.DB_FILE
    jrnl_app.DB_FILE = temp_db_path

    try:
        # Initialize the database
        jrnl_app.init_db()

        # Capture the output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            jrnl_app.show_item_details(9999)  # Non-existent ID

        output = captured_output.getvalue()
        
        # Verify that the output contains an error message
        assert "Error: Item with ID 9999 does not exist" in output

    finally:
        # Clean up: remove the temporary database file
        jrnl_app.DB_FILE = original_db_file
        os.unlink(temp_db_path)


def test_show_note_with_child_items():
    """Test the show command with a note that has child items"""
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
        temp_db_path = temp_db.name

    # Set the global DB_FILE in jrnl_app to our temp database
    original_db_file = jrnl_app.DB_FILE
    jrnl_app.DB_FILE = temp_db_path

    try:
        # Initialize the database
        jrnl_app.init_db()

        # Add a parent note
        parent_note_id = jrnl_app.add_item("Parent note", "note")
        
        # Add a child note
        child_note_id = jrnl_app.add_item("Child note", "note", parent_note_id)
        
        # Add a child task
        child_task_id = jrnl_app.add_item("Child task", "todo", parent_note_id)

        # Capture the output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            jrnl_app.show_item_details(parent_note_id)

        output = captured_output.getvalue()
        
        # Verify that the output contains the parent note content
        assert "Parent note" in output
        assert f"(id:{parent_note_id})" in output
        
        # Verify that the output contains the child items
        assert "Child note" in output
        assert "Child task" in output

    finally:
        # Clean up: remove the temporary database file
        jrnl_app.DB_FILE = original_db_file
        os.unlink(temp_db_path)


def test_show_task_with_child_items():
    """Test the show command with a task that has child items"""
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
        temp_db_path = temp_db.name

    # Set the global DB_FILE in jrnl_app to our temp database
    original_db_file = jrnl_app.DB_FILE
    jrnl_app.DB_FILE = temp_db_path

    try:
        # Initialize the database
        jrnl_app.init_db()

        # Add a parent task
        parent_task_id = jrnl_app.add_item("Parent task", "todo")
        
        # Add a child note
        child_note_id = jrnl_app.add_item("Child note", "note", parent_task_id)
        
        # Add a child task
        child_task_id = jrnl_app.add_item("Child task", "todo", parent_task_id)

        # Capture the output
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            jrnl_app.show_item_details(parent_task_id)

        output = captured_output.getvalue()
        
        # Verify that the output contains the parent task content
        assert "Parent task" in output
        assert f"(id:{parent_task_id})" in output
        
        # Verify that the output contains the child items
        assert "Child note" in output
        assert "Child task" in output

    finally:
        # Clean up: remove the temporary database file
        jrnl_app.DB_FILE = original_db_file
        os.unlink(temp_db_path)


if __name__ == "__main__":
    # Run the tests
    test_show_note_by_id()
    test_show_task_by_id()
    test_show_nonexistent_item()
    test_show_note_with_child_items()
    test_show_task_with_child_items()
    print("All tests passed!")