#!/usr/bin/env python3
"""
Test script to verify the functionality of the enhanced 'done' command
that requires a note to be added when completing tasks.
"""

import os
import sys
import subprocess
import tempfile
import sqlite3
from datetime import datetime

def run_jrnl_command(args):
    """Run a jrnl command and return the result"""
    result = subprocess.run([sys.executable, "jrnl_app.py"] + args, 
                          capture_output=True, text=True)
    return result

def test_done_with_note():
    """Test marking a task as done with a note"""
    print("Testing: Marking a task as done with a note")
    
    # Clean up any existing test database
    if os.path.exists("test_jrnl.db"):
        os.remove("test_jrnl.db")
    
    # Create a temporary file with modified DB_FILE
    with open("jrnl_app.py", "r") as f:
        content = f.read()
    
    # Create a temporary file with modified DB_FILE
    temp_content = content.replace('DB_FILE = "jrnl.db"', 'DB_FILE = "test_jrnl.db"')
    with open("temp_jrnl_app.py", "w") as f:
        f.write(temp_content)
    
    try:
        # Add a task first
        result = subprocess.run([sys.executable, "temp_jrnl_app.py", "task", "Test task for completion"], 
                              capture_output=True, text=True)
        print(f"Add task result: {result.stdout.strip()}")
        if result.stderr:
            print(f"Add task error: {result.stderr.strip()}")
        
        # Verify the task was added
        with sqlite3.connect("test_jrnl.db") as conn:
            tasks = conn.execute("SELECT * FROM tasks").fetchall()
            print(f"Tasks in DB after creation: {len(tasks)}")
            for task in tasks:
                print(f"  Task: {task}")
        
        # Mark the task as done with a note
        result = subprocess.run([sys.executable, "temp_jrnl_app.py", "done", "1", "Completed with test note"], 
                              capture_output=True, text=True)
        print(f"Mark done result: {result.stdout.strip()}")
        if result.stderr:
            print(f"Mark done error: {result.stderr.strip()}")
        
        # Verify the task was marked as done
        with sqlite3.connect("test_jrnl.db") as conn:
            tasks = conn.execute("SELECT * FROM tasks WHERE id=1").fetchall()
            if tasks:
                task = tasks[0]
                print(f"Task status after completion: {task[2]} (status), {task[5]} (completion date)")
                
                # Verify the note was added to the task
                notes = conn.execute("SELECT * FROM notes WHERE task_id=1").fetchall()
                print(f"Notes for task 1: {len(notes)}")
                for note in notes:
                    print(f"  Note: {note}")
                
                # Check if task status is 'done' and completion date is set
                if task[2] == 'done' and task[5] is not None:
                    print("✓ Task correctly marked as done with completion date")
                else:
                    print("✗ Task not correctly marked as done")
                
                # Check if note was added
                if len(notes) == 1 and notes[0][1] == "Completed with test note":
                    print("✓ Note correctly added to completed task")
                else:
                    print("✗ Note not correctly added to completed task")
            else:
                print("✗ Task not found")
        
        return True
    except Exception as e:
        print(f"Error in test: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists("test_jrnl.db"):
            os.remove("test_jrnl.db")
        if os.path.exists("temp_jrnl_app.py"):
            os.remove("temp_jrnl_app.py")

def test_done_without_note():
    """Test attempting to mark a task as done without providing a note"""
    print("\nTesting: Attempting to mark a task as done without a note (should fail)")
    
    # Clean up any existing test database
    if os.path.exists("test_jrnl.db"):
        os.remove("test_jrnl.db")
    
    # Create a temporary file with modified DB_FILE
    with open("jrnl_app.py", "r") as f:
        content = f.read()
    temp_content = content.replace('DB_FILE = "jrnl.db"', 'DB_FILE = "test_jrnl.db"')
    with open("temp_jrnl_app.py", "w") as f:
        f.write(temp_content)
    
    try:
        # Add a task first
        result = subprocess.run([sys.executable, "temp_jrnl_app.py", "task", "Test task for completion"], 
                              capture_output=True, text=True)
        print(f"Add task result: {result.stdout.strip()}")
        
        # Try to mark the task as done without a note (should fail)
        result = subprocess.run([sys.executable, "temp_jrnl_app.py", "done", "1"], 
                              capture_output=True, text=True)
        print(f"Mark done without note result: {result.stdout.strip()}")
        if result.stderr:
            print(f"Mark done without note error: {result.stderr.strip()}")
        
        # Verify the task was NOT marked as done
        with sqlite3.connect("test_jrnl.db") as conn:
            tasks = conn.execute("SELECT * FROM tasks WHERE id=1").fetchall()
            if tasks:
                task = tasks[0]
                print(f"Task status after failed completion attempt: {task[2]} (status), {task[5]} (completion date)")
                
                # Check if task status is still 'todo' and completion date is NOT set
                if task[2] == 'todo' and task[5] is None:
                    print("✓ Task correctly remained in 'todo' status")
                else:
                    print("✗ Task may have been incorrectly marked as done")
        
        # Verify that error message was shown
        if "Please provide a note" in result.stdout or "Please provide a note" in result.stderr:
            print("✓ Correct error message shown when no note is provided")
        else:
            print("✗ No appropriate error message shown")
            
        return True
    except Exception as e:
        print(f"Error in test: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists("test_jrnl.db"):
            os.remove("test_jrnl.db")
        if os.path.exists("temp_jrnl_app.py"):
            os.remove("temp_jrnl_app.py")

def test_x_shortcut_with_note():
    """Test marking a task as done using 'x' shortcut with a note"""
    print("\nTesting: Marking a task as done using 'x' shortcut with a note")
    
    # Clean up any existing test database
    if os.path.exists("test_jrnl.db"):
        os.remove("test_jrnl.db")
    
    # Create a temporary file with modified DB_FILE
    with open("jrnl_app.py", "r") as f:
        content = f.read()
    temp_content = content.replace('DB_FILE = "jrnl.db"', 'DB_FILE = "test_jrnl.db"')
    with open("temp_jrnl_app.py", "w") as f:
        f.write(temp_content)
    
    try:
        # Add a task first
        result = subprocess.run([sys.executable, "temp_jrnl_app.py", "task", "Test task for x shortcut"], 
                              capture_output=True, text=True)
        print(f"Add task result: {result.stdout.strip()}")
        
        # Mark the task as done using 'x' shortcut with a note
        result = subprocess.run([sys.executable, "temp_jrnl_app.py", "x", "1", "Completed with x shortcut"], 
                              capture_output=True, text=True)
        print(f"Mark done with x shortcut result: {result.stdout.strip()}")
        if result.stderr:
            print(f"Mark done with x shortcut error: {result.stderr.strip()}")
        
        # Verify the task was marked as done
        with sqlite3.connect("test_jrnl.db") as conn:
            tasks = conn.execute("SELECT * FROM tasks WHERE id=1").fetchall()
            if tasks:
                task = tasks[0]
                print(f"Task status after completion with x: {task[2]} (status), {task[5]} (completion date)")
                
                # Verify the note was added to the task
                notes = conn.execute("SELECT * FROM notes WHERE task_id=1").fetchall()
                print(f"Notes for task 1: {len(notes)}")
                
                # Check if task status is 'done' and completion date is set
                if task[2] == 'done' and task[5] is not None:
                    print("✓ Task correctly marked as done with completion date using 'x' shortcut")
                else:
                    print("✗ Task not correctly marked as done using 'x' shortcut")
                
                # Check if note was added
                if len(notes) == 1 and notes[0][1] == "Completed with x shortcut":
                    print("✓ Note correctly added to completed task using 'x' shortcut")
                else:
                    print("✗ Note not correctly added to completed task using 'x' shortcut")
        
        return True
    except Exception as e:
        print(f"Error in test: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists("test_jrnl.db"):
            os.remove("test_jrnl.db")
        if os.path.exists("temp_jrnl_app.py"):
            os.remove("temp_jrnl_app.py")

if __name__ == "__main__":
    print("Testing the enhanced 'done' command functionality")
    print("="*50)
    
    success = True
    success &= test_done_with_note()
    success &= test_done_without_note()
    success &= test_x_shortcut_with_note()
    
    print("\n" + "="*50)
    if success:
        print("All tests completed! Check results above.")
    else:
        print("Some tests failed!")