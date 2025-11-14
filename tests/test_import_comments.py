"""Test suite for import functionality with comment lines."""

import sqlite3
import tempfile
import os
import sys
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


def test_import_ignores_comment_lines():
    """Test that import function ignores lines starting with #"""
    # Create a test file with comments and actual content
    test_file = tempfile.mktemp()
    with open(test_file, 'w') as f:
        f.write("# This is a comment\n")
        f.write(". Task 1\n")
        f.write("# Another comment\n")
        f.write("- Note 1\n")
        f.write("#    This is also a comment, even with spaces\n")
        f.write("  # This is a comment with leading spaces\n")
        f.write("x Completed task\n")
        f.write("# Final comment\n")
        f.write("/ Task in progress\n")
        f.write("\\ Waiting task\n")
        f.write("- Final note\n")
    
    try:
        # Import from the file
        with redirect_stdout(StringIO()):
            imported_ids = jrnl_app.import_from_file(test_file)
        
        # Should have imported 6 items (not the comments)
        # . Task 1, - Note 1, x Completed task, / Task in progress, \ Waiting task, - Final note
        assert len(imported_ids) == 6
        
        # Check the items in the database
        with sqlite3.connect(DB_FILE) as conn:
            items = conn.execute("SELECT title, status FROM items ORDER BY id").fetchall()

            # Should have exactly these items in this order (excluding comments):
            expected_items = [
                ("Task 1", "todo"),        # . Task 1
                ("Note 1", "note"),        # - Note 1
                ("Completed task", "done"), # x Completed task
                ("Task in progress", "doing"), # / Task in progress
                ("Waiting task", "waiting"),  # \ Waiting task
                ("Final note", "note"),    # - Final note
            ]

            assert len(items) == len(expected_items)
            for i, (title, item_status) in enumerate(items):
                expected_title, expected_status = expected_items[i]
                assert title == expected_title
                assert item_status == expected_status
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


def test_import_ignores_comment_lines_with_spaces():
    """Test that import function ignores lines starting with # after leading spaces"""
    # Create a test file with comments that have leading spaces
    test_file = tempfile.mktemp()
    with open(test_file, 'w') as f:
        f.write("    # Indented comment\n")
        f.write(". Task 1\n")
        f.write("\t# Tab-indented comment\n")
        f.write("- Note 1\n")
    
    try:
        # Import from the file
        with redirect_stdout(StringIO()):
            imported_ids = jrnl_app.import_from_file(test_file)
        
        # Should have imported 2 items (ignoring the comments)
        assert len(imported_ids) == 2
        
        # Check the items in the database
        with sqlite3.connect(DB_FILE) as conn:
            items = conn.execute("SELECT title, status FROM items ORDER BY id").fetchall()

            # Should have these 2 items:
            expected_items = [
                ("Task 1", "todo"),        # . Task 1
                ("Note 1", "note"),        # - Note 1
            ]

            assert len(items) == len(expected_items)
            for i, (title, item_status) in enumerate(items):
                expected_title, expected_status = expected_items[i]
                assert title == expected_title
                assert item_status == expected_status
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


def test_import_empty_and_comment_lines_mixed():
    """Test that import handles empty lines and comments mixed together"""
    # Create a test file with various combinations of empty lines and comments
    test_file = tempfile.mktemp()
    with open(test_file, 'w') as f:
        f.write("\n")  # empty line
        f.write("# Comment 1\n")
        f.write("\n")  # empty line
        f.write("  \n")  # line with only spaces
        f.write("\t\t\n")  # line with only tabs
        f.write("# Comment 2\n")
        f.write(". Real task\n")  # This should be imported
        f.write("\n")  # empty line
        f.write("  # Comment with leading spaces\n")
        f.write("- Real note\n")  # This should be imported
        f.write("# Final comment\n")
    
    try:
        # Import from the file
        with redirect_stdout(StringIO()):
            imported_ids = jrnl_app.import_from_file(test_file)
        
        # Should have imported 2 items (ignoring empty lines and comments)
        assert len(imported_ids) == 2
        
        # Check the items in the database
        with sqlite3.connect(DB_FILE) as conn:
            items = conn.execute("SELECT title, status FROM items ORDER BY id").fetchall()

            # Should have these 2 items:
            expected_items = [
                ("Real task", "todo"),     # . Real task
                ("Real note", "note"),     # - Real note
            ]

            assert len(items) == len(expected_items)
            for i, (title, item_status) in enumerate(items):
                expected_title, expected_status = expected_items[i]
                assert title == expected_title
                assert item_status == expected_status
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)