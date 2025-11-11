"""Test suite for export functionality with optional ID parameter."""

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


def test_export_entire_database_basic():
    """Test exporting entire database when no ID is provided"""
    # Add some test data
    with redirect_stdout(StringIO()):
        # Add a task
        task_ids = jrnl_app.add_task(["Root task"])
        root_task_id = task_ids[0]
        
        # Add a note
        note_ids = jrnl_app.add_note([], "Root note")
        root_note_id = note_ids[0]
        
        # Add a child task under the root task
        child_task_id = jrnl_app.add_item("Child task", "todo", root_task_id)
        
        # Add a child note under the root note
        child_note_id = jrnl_app.add_item("Child note", "note", root_note_id)
        
        # Mark one task as done
        jrnl_app.update_task_status([child_task_id], "done")

    # Export entire database to a file
    export_file = tempfile.mktemp()
    success = jrnl_app.export_entire_database(export_file)
    
    assert success is True
    assert os.path.exists(export_file)
    
    # Verify file contains expected content
    with open(export_file, 'r', encoding='utf-8') as f:
        content = f.read()
        # Should contain all items in some form
        assert "Root task" in content
        assert "Root note" in content
        assert "Child task" in content
        assert "Child note" in content
        assert "x Child task" in content  # Since it was marked as done
    
    if os.path.exists(export_file):
        os.remove(export_file)


def test_export_entire_database_with_hierarchy():
    """Test that export preserves hierarchy when exporting entire database"""
    with redirect_stdout(StringIO()):
        # Create a hierarchy: root -> child -> grandchild
        root_task_id = jrnl_app.add_item("Root task", "todo", None)
        child_task_id = jrnl_app.add_item("Child task", "todo", root_task_id)
        grandchild_note_id = jrnl_app.add_item("Grandchild note", "note", child_task_id)
        
        # Add another root item
        root_note_id = jrnl_app.add_item("Root note", "note", None)

    # Export entire database
    export_file = tempfile.mktemp()
    success = jrnl_app.export_entire_database(export_file)
    
    assert success is True
    
    with open(export_file, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.strip().split('\n')
        
        # Should have multiple lines for multiple root items and their children
        assert len(lines) >= 4  # At least root task, child task, grandchild note, and root note
        
        # Check that child items are properly indented (hierarchy preserved)
        has_indented_line = any(line.startswith('\t') for line in lines if line.strip())
        assert has_indented_line, "Expected hierarchy to be preserved with indentation"

    if os.path.exists(export_file):
        os.remove(export_file)


def test_export_entire_database_with_different_statuses():
    """Test that export shows correct prefixes for different task statuses"""
    with redirect_stdout(StringIO()):
        # Add tasks with different statuses
        todo_task_id = jrnl_app.add_item("Todo task", "todo", None)
        doing_task_id = jrnl_app.add_item("Doing task", "todo", None)
        waiting_task_id = jrnl_app.add_item("Waiting task", "todo", None)
        done_task_id = jrnl_app.add_item("Done task", "todo", None)
        
        # Set specific statuses
        jrnl_app.update_task_status([doing_task_id], "doing")
        jrnl_app.update_task_status([waiting_task_id], "waiting")
        jrnl_app.update_task_status([done_task_id], "done")

    export_file = tempfile.mktemp()
    success = jrnl_app.export_entire_database(export_file)
    assert success is True
    
    with open(export_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Verify appropriate prefixes for each status
        assert ". Todo task" in content  # default is todo
        assert "/ Doing task" in content  # doing status
        assert "\\ Waiting task" in content  # waiting status
        assert "x Done task" in content  # done status

    if os.path.exists(export_file):
        os.remove(export_file)


def test_export_entire_database_empty():
    """Test exporting an empty database"""
    export_file = tempfile.mktemp()
    success = jrnl_app.export_entire_database(export_file)
    
    # Should succeed but create an empty file (or file with just whitespace)
    assert success is True
    assert os.path.exists(export_file)
    
    with open(export_file, 'r', encoding='utf-8') as f:
        content = f.read()
        # For an empty database, content might be empty or just have minimal structure
        # The important thing is that it doesn't crash

    if os.path.exists(export_file):
        os.remove(export_file)


def test_command_line_export_no_id():
    """Test that command line export with no ID calls the appropriate function"""
    # This test would need to mock the command line parsing to verify
    # that when no ID is provided, the entire database export function is called
    pass