"""Test suite for the enhanced import/export functionality with temporary files and editor."""

import sqlite3
import tempfile
import os
import sys
from io import StringIO
from contextlib import redirect_stdout
import argparse
import subprocess
from unittest.mock import patch, MagicMock

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


# Test enhanced import functionality
def test_enhanced_import_with_editor():
    """Test enhanced import command that opens editor when no file path is provided"""
    # Since we can't actually open an editor in tests, we'll mock the process
    # First, let's mock the editor to simply create a file with test content
    import tempfile
    import subprocess
    
    # Create a temporary file to simulate what would happen in the editor
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write("- Root note\n\t. Child task\n\t\t- Grandchild note")
        temp_file_path = temp_file.name
    
    try:
        # Add some content to the database first to verify import works
        with redirect_stdout(StringIO()):
            # Add a parent if needed
            parent_ids = jrnl_app.add_note([], "Parent for import")
        
        parent_id = parent_ids[0] if parent_ids else None
        
        # Mock the subprocess call to editor
        with patch('subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = None  # Simulate editor closing
            
            # Mock the file creation and reading process
            with patch('tempfile.NamedTemporaryFile', return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(name=temp_file_path)), __exit__=MagicMock())):
                with patch('os.unlink'):
                    # Call the import function (this will be implemented later)
                    # For now this is just documenting the expected behavior
                    pass
    finally:
        # Cleanup
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def test_enhanced_export_with_editor():
    """Test enhanced export command that opens editor when no file path is provided"""
    # Create some test data to export
    with redirect_stdout(StringIO()):
        root_task_ids = jrnl_app.add_task(["Root task"])
        root_task_id = root_task_ids[0]
        
        # Add a child note under the root task
        child_note_id = jrnl_app.add_item("Child note", "note", root_task_id)
        
        # Add a grandchild task under the child note
        grandchild_task_id = jrnl_app.add_item("Grandchild task", 'todo', child_note_id)
        
        # Mark the grandchild task as done
        jrnl_app.update_task_status([grandchild_task_id], 'done')
    
    # Since we can't actually open an editor in tests, we'll mock the process
    with patch('subprocess.run') as mock_subprocess:
        mock_subprocess.return_value = None  # Simulate editor closing
        
        with patch('tempfile.NamedTemporaryFile') as mock_tempfile:
            mock_tempfile_handler = MagicMock()
            mock_tempfile_handler.__enter__.return_value = MagicMock(name='/tmp/tempxxxxxx.txt')
            mock_tempfile_handler.__exit__.return_value = None
            mock_tempfile.return_value = mock_tempfile_handler

            with patch('os.unlink'):
                # Call the export function (this will be implemented later)
                # For now this is just documenting the expected behavior
                pass


def test_enhanced_import_with_parent_id():
    """Test enhanced import command with parent ID but no file path"""
    # Create parent item
    with redirect_stdout(StringIO()):
        parent_ids = jrnl_app.add_note([], "Parent note")
        parent_id = parent_ids[0]
    
    # Temp file path
    temp_path = tempfile.mktemp()
    
    # Mock the process 
    with patch('subprocess.run'):
        with patch('tempfile.NamedTemporaryFile') as mock_tempfile:
            mock_tempfile_handler = MagicMock()
            mock_file_obj = MagicMock()
            mock_file_obj.name = temp_path
            mock_tempfile_handler.__enter__.return_value = mock_file_obj
            mock_tempfile_handler.__exit__.return_value = None
            mock_tempfile.return_value = mock_tempfile_handler

            with patch('os.unlink'):
                # Create actual temporary file with content for the function to read
                with open(temp_path, 'w') as f:
                    f.write("- Test note\n\t. Test task")
                
                # Call the enhanced import function
                with patch('jrnl_app.import_from_file') as mock_import:
                    mock_import.return_value = [1, 2]  # Mock returning some IDs
                    result = jrnl_app.import_with_editor(parent_id)
                    
                    # Verify the function was called correctly
                    mock_import.assert_called_once_with(temp_path, parent_id)
                    assert result == [1, 2]
    
    # Clean up temp file if it was created
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except:
        pass


def test_enhanced_import_fallback_to_file():
    """Test that import still works with explicit file path (backward compatibility)"""
    # Create a test file with import data
    test_file = tempfile.mktemp()
    with open(test_file, 'w') as f:
        f.write("- Test root\n\t. Test child task")
    
    try:
        # Import with explicit file path (should use the original import path)
        with redirect_stdout(StringIO()):
            imported_ids = jrnl_app.import_from_file(test_file)
        
        # Should have imported one root item
        assert len(imported_ids) > 0
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)


def test_enhanced_export_fallback_to_file():
    """Test that export still works with explicit file path (backward compatibility)"""
    # Create some test data to export
    with redirect_stdout(StringIO()):
        task_ids = jrnl_app.add_task(["Test task"])
        task_id = task_ids[0]
    
    export_file = tempfile.mktemp()
    try:
        # Export with explicit file path (should use the original export path)
        success = jrnl_app.export_to_file(task_id, export_file)
        assert success
        
        # Verify file was created and contains expected content
        assert os.path.exists(export_file)
        with open(export_file, 'r') as f:
            content = f.read()
            assert ". Test task" in content
    finally:
        if os.path.exists(export_file):
            os.remove(export_file)