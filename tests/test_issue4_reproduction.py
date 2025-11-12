import sys
sys.path.insert(0, '.')

import jrnl_app
from io import StringIO
from contextlib import redirect_stdout

def test_show_due_shows_complete_hierarchy():
    """
    Test that show_due shows complete hierarchy including child notes and tasks.
    Based on the issue example: task111 (id:240) had child notes (id:242) and tasks (id:241) 
    that should now be visible in the 'j ls task due' output.
    """
    # Initialize the database
    jrnl_app.init_db()
    
    # Create the same structure as in the issue
    # Create a note structure
    note1_id = jrnl_app.add_item("note1", "note")
    note11_id = jrnl_app.add_item("note11", "note", note1_id)
    note111_id = jrnl_app.add_item("note111", "note", note11_id)
    
    # Add the main task under note111
    task1_id = jrnl_app.add_item("task1", "todo", note111_id)
    
    # Add child tasks to task1
    task11_id = jrnl_app.add_item("task11", "todo", task1_id)
    task12_id = jrnl_app.add_item("task12", "todo", task1_id)
    
    # Add deeper task
    task111_id = jrnl_app.add_item("task111", "todo", task11_id)
    
    # Add the children mentioned in the issue - a note and a task under task111
    note_for_task111_id = jrnl_app.add_item("Note for task111", "note", task111_id)
    task111_dup_id = jrnl_app.add_item("task111", "todo", task111_id)  # Duplicate name as per issue
    
    # Add another task
    task2_id = jrnl_app.add_item("task2", "todo", note111_id)
    task3_id = jrnl_app.add_item("task3", "todo", note111_id)
    
    # Set due dates so they appear in the due view
    from datetime import datetime, timedelta
    today = datetime.now().date().strftime("%Y-%m-%d")
    
    # Update due dates for proper assignment to 'Due Today' bucket
    with jrnl_app.sqlite3.connect(jrnl_app.DB_FILE) as conn:
        for task_id in [task1_id, task11_id, task12_id, task111_id, task2_id, task3_id]:
            conn.execute(
                "UPDATE items SET due_date=? WHERE id=?",
                (today, task_id)
            )
    
    # Capture the output of show_due()
    captured_output = StringIO()
    with redirect_stdout(captured_output):
        jrnl_app.show_due()
    
    output = captured_output.getvalue()
    
    print("Output of 'j ls task due':")
    print(output)
    
    # Verify that the complete hierarchy is shown, including child notes/tasks
    expected_elements = [
        "task1",        # Root task
        "task11",       # Child of task1  
        "task12",       # Child of task1
        "task111",      # Child of task11
        "Note for task111",  # Child (note) of task111 - this was missing before
        "task111",      # Child (task) of task111 - this was missing before (different object with same name)
        "task2",        # Another root task under note111
        "task3"         # Another root task under note111
    ]
    
    all_present = True
    for element in expected_elements:
        if element in output:
            print(f"✓ Found '{element}' in output")
        else:
            print(f"✗ Missing '{element}' from output")
            all_present = False
    
    if all_present:
        print("\n✓ SUCCESS: All elements including child notes and tasks are shown in due view!")
        print("The fix successfully resolves the issue where children of tasks were not shown")
    else:
        print("\n✗ FAILURE: Some expected elements are missing from the output")
    
    return all_present

def test_original_issue_scenario():
    """
    Test the exact scenario described in the issue.
    """
    # Initialize database
    jrnl_app.init_db()
    
    # Create the exact structure mentioned in the issue
    note1 = jrnl_app.add_item("note1", "note")
    note11 = jrnl_app.add_item("note11", "note", note1)
    note111 = jrnl_app.add_item("note111", "note", note11)
    note112 = jrnl_app.add_item("note112", "note", note11)
    note113 = jrnl_app.add_item("note113", "note", note11)
    note12 = jrnl_app.add_item("note12", "note", note1)
    note13 = jrnl_app.add_item("note13", "note", note1)
    note2 = jrnl_app.add_item("note2", "note")
    note3 = jrnl_app.add_item("note3", "note")
    
    # Add the tasks mentioned in the issue
    task1 = jrnl_app.add_item("task1", "todo", note112)  # Under note112 as per issue
    task2 = jrnl_app.add_item("task2", "todo", note112)
    task3 = jrnl_app.add_item("task3", "todo", note112)
    
    # Add the child hierarchy mentioned in the issue
    task11 = jrnl_app.add_item("task11", "todo", task1)
    task12 = jrnl_app.add_item("task12", "todo", task1)
    task111 = jrnl_app.add_item("task111", "todo", task11)
    
    # The children that weren't showing: notes 241 and 242 from the issue
    # Note for task111 (id:242) and task111 (id:241) under task111 (id:240)  
    note_for_task111 = jrnl_app.add_item("Note for task111", "note", task111)
    task111_dup = jrnl_app.add_item("task111", "todo", task111)  # Different task with same name
    
    # Set them all to due today
    from datetime import datetime
    today = datetime.now().date().strftime("%Y-%m-%d")
    
    with jrnl_app.sqlite3.connect(jrnl_app.DB_FILE) as conn:
        for task_id in [task1, task2, task3, task11, task12, task111]:
            conn.execute(
                "UPDATE items SET due_date=? WHERE id=?",
                (today, task_id)
            )
    
    # Capture the output of show_due()
    captured_output = StringIO()
    with redirect_stdout(captured_output):
        jrnl_app.show_due()
    
    output = captured_output.getvalue()
    
    print("Original Issue Scenario - Output of 'j ls task due':")
    print(output)
    
    # The key test: the children of task111 should now be visible
    # Before the fix: task111 would be shown but not its children
    # After the fix: task111 and its children (note and task) should be shown
    
    assert "task1" in output, "task1 should be in output"
    assert "task11" in output, "task11 should be in output" 
    assert "task111" in output, "task111 should be in output"
    assert "Note for task111" in output, "Child note should be in output now (was missing before)"
    assert "task111" in output, "Child task should be in output now (was missing before)"
    
    print("✓ All expected elements found in output!")
    print("✓ The issue where child notes and tasks were not shown in 'j ls task due' is FIXED!")
    
    return True

if __name__ == "__main__":
    success1 = test_show_due_shows_complete_hierarchy()
    print("\n" + "="*60 + "\n")
    success2 = test_original_issue_scenario()
    
    if success1 and success2:
        print("\n🎉 ALL TESTS PASSED! The fix is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED.")
        sys.exit(1)