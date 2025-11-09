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

def test_root_tasks_under_notes_not_shown_in_ls_task():
    """
    Test to reproduce the issue where root tasks (tasks that have a note as parent)
    are not shown in the output of the command 'j ls task'.
    """
    # Initialize the database
    jrnl_app.init_db()
    
    # Create a note
    note1_id = jrnl_app.add_item("test note1", "note")
    
    # Add child note to the root note
    note11_id = jrnl_app.add_item("test note11", "note", note1_id)
    
    # Add another level of notes
    note112_id = jrnl_app.add_item("test note112", "note", note11_id)
    
    # Add note1123 under note112
    note1123_id = jrnl_app.add_item("test note 1123", "note", note112_id)
    
    # Add task under the note - this should be a "root task" according to the definition
    task_under_note1_id = jrnl_app.add_item("test task 11231", "todo", note1123_id)  # This is task id 23 equivalent
    task_under_note2_id = jrnl_app.add_item("test task 11232", "todo", note1123_id)  # This is task id 24 equivalent
    
    # Add a note under the task
    note_under_task_id = jrnl_app.add_item("test note under 23", "note", task_under_note1_id)
    
    # Add a task under the first task (to create a child structure)
    task_under_task_id = jrnl_app.add_item("test task under 23", "todo", task_under_note1_id)
    
    # Capture the output of show_task() (this is what 'j ls task' does)
    captured_output = StringIO()
    with redirect_stdout(captured_output):
        jrnl_app.show_task()
    
    output = captured_output.getvalue()
    
    print("Output of 'j ls task':")
    print(repr(output))
    print("Actual output:")
    print(output)
    
    # The output should contain the root tasks that are under notes
    # According to the definition: "A task having note as a parent is a root task"
    # So task_under_note1_id and task_under_note2_id should be visible in 'j ls task' output
    
    # Check if the root tasks (that have note parents) are in the output
    assert f"test task 11231" in output, f"Root task 'test task 11231' (id: {task_under_note1_id}) should be visible in task listing"
    assert f"test task 11232" in output, f"Root task 'test task 11232' (id: {task_under_note2_id}) should be visible in task listing"
    
    # Also check that the children of these root tasks are shown
    assert "test note under 23" in output, f"Child 'test note under 23' should be visible under its root task"
    assert "test task under 23" in output, f"Child 'test task under 23' should be visible under its root task"

def test_root_tasks_definition():
    """
    Test to verify the definition of root tasks: tasks with no parent or with note as parent
    """
    jrnl_app.init_db()
    
    # Create a root task (no parent)
    root_task_no_parent = jrnl_app.add_item("Root task with no parent", "todo")
    
    # Create a note
    note_id = jrnl_app.add_item("Parent note", "note")
    
    # Create a task under the note (should be root task according to definition)
    root_task_under_note = jrnl_app.add_item("Root task under note", "todo", note_id)
    
    # Create a task under another task (should NOT be root task)
    child_task = jrnl_app.add_item("Child task", "todo", root_task_no_parent)
    
    # Capture the output of show_task()
    captured_output = StringIO()
    with redirect_stdout(captured_output):
        jrnl_app.show_task()
    
    output = captured_output.getvalue()
    
    print("Root tasks test output:")
    print(output)
    
    # Both tasks with no parent and tasks under notes should be shown as roots
    # The child task (under another task) should not be shown at the root level
    assert "Root task with no parent" in output, "Task with no parent should be in task listing"
    assert "Root task under note" in output, "Task under note should be in task listing"
    # The child task should be shown under its parent, not as a root task
    assert "Child task" in output, "Child task should be in output, under its parent"