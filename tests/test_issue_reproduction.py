import pytest
import sys
import os
from io import StringIO
from contextlib import redirect_stdout
import sqlite3
from unittest.mock import patch

# Add the main directory to the path so we can import jrnl_app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import jrnl_app

def test_tasks_with_children_not_expanded_in_note_output():
    """
    Test to reproduce the issue where tasks having children are not expanded 
    in the output of the command 'j ls note'.
    """
    # Initialize the database
    jrnl_app.init_db()
    
    # Create test data: a note with a task child, and that task has children
    note1_id = jrnl_app.add_item("test note1", "note")
    
    task_under_note_id = jrnl_app.add_item("test task under note", "todo", note1_id)
    
    # Add a note under the task
    note_under_task_id = jrnl_app.add_item("test note under task", "note", task_under_note_id)
    
    # Add a task under the task
    task_under_task_id = jrnl_app.add_item("test task under task", "todo", task_under_note_id)
    
    # Capture the output of show_note()
    captured_output = StringIO()
    with redirect_stdout(captured_output):
        jrnl_app.show_note()
    
    output = captured_output.getvalue()
    
    print("Output of 'j ls note':")
    print(output)
    
    # The output should contain the task with children expanded, 
    # but currently it doesn't show the children of the task under the note
    assert "test note under task" in output, "Child note under task should be visible in note listing"
    assert "test task under task" in output, "Child task under task should be visible in note listing"

def test_show_note_expands_all_children():
    """
    Test that show_note properly expands all children, including tasks with notes.
    """
    # This test should fail initially, demonstrating the bug
    jrnl_app.init_db()
    
    # Create a note
    parent_note_id = jrnl_app.add_item("Parent Note", "note")
    
    # Add a task under the note
    task_id = jrnl_app.add_item("Task under note", "todo", parent_note_id)
    
    # Add a note under the task
    child_note_id = jrnl_app.add_item("Child note under task", "note", task_id)
    
    # Add another task under the first task
    child_task_id = jrnl_app.add_item("Child task under task", "todo", task_id)
    
    # Add a note under the child task
    grandchild_note_id = jrnl_app.add_item("Grandchild note", "note", child_task_id)
    
    # Capture the output of show_note()
    captured_output = StringIO()
    with redirect_stdout(captured_output):
        jrnl_app.show_note()
    
    output = captured_output.getvalue()
    
    print("Detailed output for testing:")
    print(output)
    
    # All items should be visible in the output when using 'j ls note'
    # The issue is that tasks with children may not be fully expanded
    expected_items = [
        "Parent Note",
        "Task under note",
        "Child note under task", 
        "Child task under task",
        "Grandchild note"
    ]
    
    for item in expected_items:
        assert item in output, f"'{item}' should be visible in note listing output"