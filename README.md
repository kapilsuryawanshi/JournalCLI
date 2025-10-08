# jrnl - Command Line Journal and Task Manager

## Overview
jrnl is a command-line tool for managing journal entries, tasks, and notes. It allows users to create, organize, and track tasks and notes from the terminal with various options for due dates, recurrence, and linking.

## Features
- Create and manage tasks with due dates and recurrence patterns
- Add and organize notes, including linking notes together
- Track task status (todo, doing, waiting, done)
- Search functionality for finding tasks and notes
- Recurring tasks that automatically create new tasks when completed
- Link notes for better organization and cross-referencing

## Installation
No installation required – simply run the Python script directly.

## Dependencies
- Python 3.x
- sqlite3 (typically included with Python)
- colorama (for colored output)

## Usage

### Basic Commands
```
jrnl                    Show tasks grouped by due date (default view) (Overdue / Due Today / Due Tomorrow / This Week / This Month / Future / No Due Date)
jrnl page|p             Show journal (grouped by creation date)
jrnl new note <text> [-link <id>[,<id>,...]]      Add a new note with optional links
jrnl new task <text> [-due @<YYYY-MM-DD|today|tomorrow|eow|eom|eoy>] [-recur <Nd|Nw|Nm|Ny>]     Add a new task with optional due date and recurrence
jrnl edit note <id> [-text <text>] [-link <id>[,<id>,...]] [-unlink <id>[,<id>,...]]  Edit note with optional text, linking, unlinking
jrnl edit task <id> [-text <text>] [-due <text>] [-note <text>] [-recur <Nd|Nw|Nm|Ny>]  Edit task with optional parameters
jrnl rm <note|task> <id>[,<id>,...]      Delete notes or tasks by ID
jrnl task|t <id> edit [-text <text>] [-due <text>] [-note <text>] [-recur <Nd|Nw|Nm|Ny>]  (DEPRECATED) Edit task with optional parameters
jrnl note|n             Show all notes
jrnl note|n <id>        Show specific note with linked notes
jrnl note|n <id> edit [-text <text>] [-link <id>[,<id>,...]] [-unlink <id>[,<id>,...]]  (DEPRECATED) Edit note with optional text, linking, unlinking
jrnl task|t             Show all unfinished tasks
jrnl done               Show all completed tasks grouped by completion date
jrnl status|s           Show tasks grouped by status (Todo, Doing, Waiting)
jrnl due|d              Show tasks grouped by due date (Overdue / Due Today / This Week / This Month / Future / No Due Date)
jrnl restart <id>[,<id>...]   Mark tasks as not done
jrnl start <id>[,<id>...]     Mark tasks as in progress
jrnl waiting <id>[,<id>...]   Mark tasks as waiting
jrnl done|x <id>[,<id>...] <note text>      Mark tasks as done with a completion note
jrnl find <text>        Search for tasks and notes containing text (supports wildcards: *, ?)
jrnl rm t<id>[,n<id>...]      (DEPRECATED) Delete tasks (t) or notes (n)
jrnl help|h             Show this help message
```

### Search
You can search for tasks and notes containing specific text:

- `jrnl find <text>` - Search for tasks and notes containing the specified text (supports wildcards: * and ?)

The old command `jrnl find|f <text>` has been completely removed (the 'f' alias is no longer supported).
Wildcard characters supported:
- `*` - Matches any sequence of zero or more characters
- `?` - Matches any single character

Examples:
- `jrnl find "*task*"` - Find items containing "task" anywhere in the text
- `jrnl find "task ????"` - Find items where "task" is followed by exactly 4 characters
- `jrnl find "task*done"` - Find items that contain "task" followed by "done" with anything in between

### Creating Tasks
Use the `jrnl new task` command to create new tasks:

- `jrnl new task "Buy groceries"` - Create a task with today's date as the due date
- `jrnl new task "Meeting with team" -due @tomorrow` - Create a task with a due date of tomorrow
- `jrnl new task "Weekly report" -due @eow -recur 1w` - Create a recurring task due at the end of each week

### Creating Notes
Use the `jrnl new note` command to create new notes:

- `jrnl new note "Interesting idea for project"` - Create a standalone note
- `jrnl new note "Follow up on meeting" -link 1,2` - Create a note and link it to existing notes with IDs 1 and 2

### Managing Tasks
Tasks can be managed in various ways:

- Change a task's status: `jrnl start 1` (marks task 1 as "doing")
- Edit a task: `jrnl edit task 1 -text "Updated task text"` or `jrnl task 1 edit -text "Updated task text"` (deprecated)
- Complete a task: `jrnl done 1 "Completed successfully"` (marks task 1 as done with a note)

### Managing Notes
Notes can be linked and edited:

- View a specific note: `jrnl note 1`
- Edit a note: `jrnl edit note 1 -text "Updated note text"` or `jrnl note 1 edit -text "Updated note text"` (deprecated)
- Link notes together: `jrnl edit note 1 -link 2,3`

### Delete Items
You can delete notes and tasks using the consolidated rm command:

- `jrnl rm note 1` - Delete a single note
- `jrnl rm note 1,2,3` - Delete multiple notes
- `jrnl rm task 1` - Delete a single task
- `jrnl rm task 1,2,3` - Delete multiple tasks

The old syntax `jrnl rm t<id>[,n<id>...]` has been completely removed.

### List Items
You can list items in different ways using the list command:

- `jrnl list page` - Show journal (grouped by creation date) (replaces the old 'jrnl page|p' command)
- `jrnl list note` - Show all notes
- `jrnl list task` - Show all unfinished tasks (grouped by creation date)
- `jrnl list task due` - Show tasks grouped by due date (Overdue / Due Today / Due Tomorrow / This Week / This Month / Future / No Due Date)
- `jrnl list task status` - Show tasks grouped by status (Todo, Doing, Waiting)
- `jrnl list task done` - Show all completed tasks grouped by completion date

The old commands `jrnl note`, `jrnl done`, `jrnl status`, `jrnl due`, and `jrnl page|p` have been completely removed.

### Task Operations
You can perform various operations on tasks:

- `jrnl start task 1,2` - Mark tasks as in progress
- `jrnl restart task 1,2` - Mark tasks as not done
- `jrnl waiting task 1,2` - Mark tasks as waiting
- `jrnl done task 1,2 "completion note"` - Mark tasks as done with a completion note

Note: Task deletion is handled separately with the `jrnl rm` command.

The old commands `jrnl start`, `jrnl restart`, `jrnl waiting`, `jrnl done|x <id> <note>`, `jrnl rm t<id>`, `jrnl task`, and `jrnl note` have been completely removed.

### Show Specific Items
You can view specific notes and tasks:

- `jrnl show note 1` - Show a specific note with linked notes
- `jrnl show task 1` - Show a specific task

The old command `jrnl note <id>` has been completely removed.

## Database
The application uses a SQLite database named `jrnl.db` to store all tasks, notes, and their relationships.

## Development
The application is written in Python and follows a modular design with separate functions for different operations. Tests are available in the test files using pytest.

## Testing
Run the tests using:
```
python -m pytest test_comprehensive_jrnl.py
python -m pytest test_note_linking.py
python -m pytest test_consolidated_commands.py
```

## License
This project does not specify a license, so it defaults to the standard MIT License terms.