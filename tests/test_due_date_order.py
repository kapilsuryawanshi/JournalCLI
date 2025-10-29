"""Test to verify the order of due date categories in show_due function"""

import sys
import os
from io import StringIO
from contextlib import redirect_stdout
import tempfile
import sqlite3

# Add the main directory to path so we can import jrnl_app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jrnl_app


def test_due_date_order():
    """Test that due date categories are displayed in the correct order: Future -> This Month -> This Week -> Tomorrow -> Today -> Overdue"""
    
    # Create a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        original_db = jrnl_app.DB_FILE
        jrnl_app.DB_FILE = tmp_db.name
        
        try:
            # Initialize the database
            jrnl_app.init_db()
            
            # Add tasks with different due dates
            from datetime import datetime, timedelta
            
            # Add a future task that's definitely beyond the current month
            future_date = (datetime.now().date() + timedelta(days=60)).strftime("%Y-%m-%d")  # 60 days from now
            jrnl_app.add_task([f"Future task @{future_date}"])
            
            # Add a task due this month but after this week (to go in "This Month" category)
            today = datetime.now().date()
            # Calculate the end of the current week
            end_of_week = today + timedelta(days=(6 - today.weekday()))
            # Schedule for a date that's after the end of the week but still in this month
            # Since today is 2025-10-22, end of week is 2025-10-26, and end of month is 2025-10-31
            # Schedule for October 29th to ensure it's within this month but after this week
            this_month_date = today.replace(day=29).strftime("%Y-%m-%d")
            jrnl_app.add_task([f"This Month task @{this_month_date}"])
            
            # Add a task due this week (but not tomorrow)
            # Calculate a date that's within the next 7 days but not tomorrow
            this_week_date = (today + timedelta(days=3)).strftime("%Y-%m-%d")  # 3 days from now
            jrnl_app.add_task([f"This Week task @{this_week_date}"])
            
            # Add a task due tomorrow
            tomorrow_date = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
            jrnl_app.add_task([f"Tomorrow task @{tomorrow_date}"])
            
            # Add a task due today
            jrnl_app.add_task([f"Today task @today"])
            
            # Add an overdue task
            overdue_date = (datetime.now().date() - timedelta(days=2)).strftime("%Y-%m-%d")
            jrnl_app.add_task([f"Overdue task @{overdue_date}"])
            
            # Capture the output of show_due
            f = StringIO()
            with redirect_stdout(f):
                jrnl_app.show_due()
            output = f.getvalue()
            
            # Split the output into lines
            lines = output.split('\n')
            
            # Extract the category headers
            categories = []
            for line in lines:
                stripped = line.strip()
                if stripped in ["Overdue", "Due Today", "Due Tomorrow", "This Week", "This Month", "Future", "No Due Date"]:
                    categories.append(stripped)
            
            # Check the order of categories (should be Future -> This Month -> This Week -> Tomorrow -> Today -> Overdue)
            expected_order = ["Future", "This Month", "This Week", "Due Tomorrow", "Due Today", "Overdue"]
            
            # The test should fail with current implementation since order is currently:
            # ["Overdue", "Due Today", "Due Tomorrow", "This Week", "This Month", "Future", "No Due Date"]
            assert categories == expected_order, f"Expected order {expected_order}, but got {categories}"
            
        finally:
            # Close the connection and restore original DB_FILE
            # Force close any potential connections
            sqlite3.connect(tmp_db.name).close()
            jrnl_app.DB_FILE = original_db
            # Clean up temporary file
            try:
                os.unlink(tmp_db.name)
            except PermissionError:
                # On Windows, sometimes files can't be deleted immediately
                # due to file locking, so we just continue
                pass


if __name__ == "__main__":
    test_due_date_order()
    print("Test passed: Due date categories are in the correct order")