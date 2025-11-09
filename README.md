# JournalCLI - Command Line Journal and Task Manager

JournalCLI is a command-line tool for managing tasks and notes with a hierarchical structure. It provides an efficient way to organize your daily activities, tasks, and notes in a simple interface.

## Features

- **Task Management**: Create, update, and track tasks with statuses (todo, doing, waiting, done)
- **Notes**: Create and organize notes in a hierarchical structure
- **Due Dates**: Set due dates for tasks with various formats (tomorrow, eow, specific dates)
- **Recurrence**: Set recurring tasks (daily, weekly, monthly, yearly)
- **Hierarchical Structure**: Tasks and notes can have parent-child relationships
- **Linking**: Link items together for better organization
- **Search**: Search through tasks and notes
- **Simplified Database Schema**: Uses a streamlined database schema for better performance

## Installation

1. Make sure you have Python 3.7+ installed
2. Install the required dependency:
   ```bash
   pip install colorama
   ```
3. Save the `jrnl_app.py` file and run it as needed

## Database Schema

The application uses a simplified database schema with the following tables:

1. **items** - Contains all items (both tasks and notes)
   - id: Primary key
   - type: 'todo' or 'note'
   - title: Title or content of the item
   - creation_date: Date when the item was created
   - pid: Parent ID for hierarchical relationships

2. **todo_info** - Contains additional information for todo items
   - id: Primary key
   - item_id: References items table
   - status: 'todo', 'doing', 'waiting', or 'done'
   - due_date: Due date for the task
   - completion_date: Date when the task was completed
   - recur: Recurrence pattern for recurring tasks

3. **item_links** - Links between items
   - id: Primary key
   - item1_id: First item in the link
   - item2_id: Second item in the link

## Usage

### Basic Commands

- `j` - Show tasks grouped by due date (default view)
- `j help` - Show help information
- `j task "task text"` - Add a new task
- `j note "note text"` - Add a new note
- `j ls page` - List all journal entries
- `j ls task` - List tasks only
- `j ls note` - List notes only

### Advanced Task Creation

- `j task "task text" -due tomorrow` - Add task with due date
- `j task "task text" -due eow` - Add task due at end of week
- `j task "task text" -recur 2d` - Add recurring task (every 2 days)
- `j task @<parent_id> "child task text"` - Add task under a parent task

### Advanced Note Creation

- `j note @<parent_note_id> "child note text"` - Add note under a parent note
- `j note <id> -text "new text"` - Edit a note
- `j note <id> -link <id1>,<id2>` - Link a note to other items

### Task Operations

- `j start task <id>,<id2>,...` - Mark task(s) as 'doing'
- `j done task <id>,<id2>,...` - Mark task(s) as done
- `j waiting task <id>,<id2>,...` - Mark task(s) as 'waiting'
- `j restart task <id>,<id2>,...` - Mark task(s) as 'todo' again

### Deleting Items

- `j rm task <id>,<id2>,...` - Delete tasks
- `j rm note <id>,<id2>,...` - Delete notes

### Search

- `j search "text"` - Search for tasks and notes containing text

## Examples

Add a task with a due date:
```bash
j task "Submit report" -due 2025-12-01
```

Add a recurring task:
```bash
j task "Daily exercise" -due tomorrow -recur 1d
```

Add a note under another note:
```bash
j note @123 "This note is under note 123"
```

Link two items:
```bash
j note 456 -link 789
```

Mark a task as done:
```bash
j done task 101
```

## Development

### Running Tests

To run the tests for the simplified schema:

```bash
python -m pytest test_new_schema.py -v
```

### File Structure

- `jrnl_app.py` - Main application file
- `test_new_schema.py` - Tests for the simplified schema
- `README.md` - This file

## Changes from Previous Version

This version implements a simplified database schema by consolidating the three tables (tasks, notes, note_links) into two main tables (items, todo_info) with a linking table (item_links). This provides a more unified and maintainable approach to managing both tasks and notes.

## Contributing

Feel free to submit issues or pull requests. For major changes, please open an issue first to discuss what you would like to change.