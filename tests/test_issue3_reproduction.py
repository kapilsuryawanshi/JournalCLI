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

def test_show_tasks_by_status_includes_root_tasks_with_note_parents():
    """
    Test that show_tasks_by_status includes root tasks that have note parents,
    not just those with no parent.
    """
    # Initialize the database
    jrnl_app.init_db()
    
    # Create a note
    note_id = jrnl_app.add_item("Parent note", "note")
    
    # Create a task with no parent (classic root task)
    root_task_no_parent = jrnl_app.add_item("Root task no parent", "todo")
    
    # Create a task under the note (should be root task according to definition)
    root_task_under_note = jrnl_app.add_item("Root task under note", "todo", note_id)
    
    # Create child tasks for hierarchy testing
    child_task = jrnl_app.add_item("Child task", "todo", root_task_no_parent)
    child_task2 = jrnl_app.add_item("Child task under note parent", "todo", root_task_under_note)
    
    # Change status of some tasks to make the test more realistic
    jrnl_app.update_todo_status(root_task_no_parent, "doing")
    jrnl_app.update_todo_status(root_task_under_note, "waiting")
    
    # Capture the output of show_tasks_by_status()
    captured_output = StringIO()
    with redirect_stdout(captured_output):
        jrnl_app.show_tasks_by_status()
    
    output = captured_output.getvalue()
    
    print("Output of 'j ls task status':")
    print(output)
    
    # Both root tasks should be visible in the output
    assert "Root task no parent" in output, "Root task with no parent should be in status view"
    assert "Root task under note" in output, "Root task under note should be in status view"
    
    # Children should also be visible under their parents
    assert "Child task" in output, "Child task should be in output"
    assert "Child task under note parent" in output, "Child task under note parent should be in output"

def test_show_tasks_by_status_with_all_status():
    """
    Test that all status views show root tasks with note parents.
    """
    jrnl_app.init_db()
    
    # Create notes for parent tasks
    note1 = jrnl_app.add_item("Note for todo", "note")
    note2 = jrnl_app.add_item("Note for doing", "note") 
    note3 = jrnl_app.add_item("Note for waiting", "note")
    
    # Create root tasks under notes with different statuses
    todo_task = jrnl_app.add_item("Todo task under note", "todo", note1)
    doing_task = jrnl_app.add_item("Doing task under note", "todo", note2)
    waiting_task = jrnl_app.add_item("Waiting task under note", "todo", note3)
    
    # Set different statuses
    jrnl_app.update_todo_status(todo_task, "todo")
    jrnl_app.update_todo_status(doing_task, "doing") 
    jrnl_app.update_todo_status(waiting_task, "waiting")
    
    # Also create root tasks with no parent for comparison
    no_parent_todo = jrnl_app.add_item("Todo task no parent", "todo")
    no_parent_doing = jrnl_app.add_item("Doing task no parent", "todo")
    no_parent_waiting = jrnl_app.add_item("Waiting task no parent", "todo")
    
    jrnl_app.update_todo_status(no_parent_todo, "todo")
    jrnl_app.update_todo_status(no_parent_doing, "doing")
    jrnl_app.update_todo_status(no_parent_waiting, "waiting")
    
    # Capture the output
    captured_output = StringIO()
    with redirect_stdout(captured_output):
        jrnl_app.show_tasks_by_status()
    
    output = captured_output.getvalue()
    
    # Tasks should be visible in their respective status sections
    assert "Todo" in output
    assert "Doing" in output 
    assert "Waiting" in output
    
    # Tasks with note parents should appear in their respective sections
    assert "Todo task under note" in output
    assert "Doing task under note" in output
    assert "Waiting task under note" in output
    
    # Tasks with no parent should also appear
    assert "Todo task no parent" in output
    assert "Doing task no parent" in output
    assert "Waiting task no parent" in output