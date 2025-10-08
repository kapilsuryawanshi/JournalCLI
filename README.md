# jrnl - Command Line Journal and Task Manager

`jrnl` is a powerful, minimalist command-line tool for managing tasks and notes. Designed for speed and simplicity, it allows users to efficiently track tasks, create notes, and organize information directly from the terminal.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Usage](#usage)
- [Commands](#commands)
- [Search Functionality](#search-functionality)
- [Recurring Tasks](#recurring-tasks)
- [Note Linking](#note-linking)
- [Zettelkasten Support](#zettelkasten-support)
- [Database](#database)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Task Management**: Create, track, and manage tasks with due dates and status updates
- **Note Taking**: Create and organize notes with linking capabilities
- **Flexible Views**: Multiple ways to view your tasks and notes (by due date, status, creation date, etc.)
- **Color-Coded Interface**: Visual indicators for task status and due dates
- **Powerful Search**: Search across all tasks and notes with wildcard support
- **Recurring Tasks**: Set up tasks that automatically reoccur
- **Note Linking**: Connect related notes for knowledge graph functionality
- **Zettelkasten Ready**: Perfect for implementing a digital Zettelkasten system
- **Scriptable**: Can be integrated into other tools and scripts for automation

## Installation

1. Download the `jrnl_app.py` file
2. Ensure you have Python 3.x installed
3. Install required dependencies: `pip install colorama`
4. Use the application directly: `python jrnl_app.py` (or create an alias/script to run it as `jrnl`)

## Dependencies

- Python 3.x
- SQLite3 (typically included with Python)
- Colorama (for colored output): `pip install colorama`

## Usage

```
jrnl [command] [arguments...]
```

## Commands

### List Commands

**List tasks by due date (default view)**:
```
jrnl list task due
jrnl  # This command is equivalent to the above
```
Shows tasks grouped by due date: Overdue, Due Today, Due Tomorrow, This Week, This Month, Future, No Due Date

**List journal by creation date**:
```
jrnl list page
jrnl page  # Alternative command
```
Shows all entries grouped by creation date

**List all unfinished tasks**:
```
jrnl list task
```

**List tasks by status**:
```
jrnl list task status
jrnl status  # Alternative command
```
Shows tasks grouped by status: Todo, Doing, Waiting

**List completed tasks**:
```
jrnl list task done
jrnl done  # Alternative command
```
Shows completed tasks grouped by completion date

**List all notes**:
```
jrnl list note
jrnl notes  # Alternative command
```

**Show specific note with linked notes**:
```
jrnl show note <id>
jrnl note <id>  # Alternative command
```

**Show specific task**:
```
jrnl show task <id>
```

### Creation Commands

**Create tasks**:
```
jrnl new task <text> [-due @<YYYY-MM-DD|keyword>] [-recur <Nd|Nw|Nm|Ny>]
```
Examples:
- `jrnl new task "Buy groceries"`
- `jrnl new task "Meeting with team" -due @tomorrow`
- `jrnl new task "Weekly report" -due @eow -recur 1w`

Due date keywords: `today`, `tomorrow`, `eow` (end of week), `eom` (end of month), `eoy` (end of year), day names (monday, tuesday, etc.)

Recurrence patterns: `Nd` (N days), `Nw` (N weeks), `Nm` (N months), `Ny` (N years)

**Create notes**:
```
jrnl new note <text> [-link <id>[,<id>,...]]
```
Examples:
- `jrnl new note "Interesting idea for project"`
- `jrnl new note "Follow up on meeting" -link 1,2`

### Modification Commands

**Mark tasks as in progress**:
```
jrnl start task <id>[,<id>...]
jrnl doing <id>[,<id>...]  # Alternative command
```

**Mark tasks as not done**:
```
jrnl restart task <id>[,<id>...]
jrnl undone <id>[,<id>...]  # Alternative command
```

**Mark tasks as waiting**:
```
jrnl waiting task <id>[,<id>...]
```

**Mark tasks as done**:
```
jrnl done task <id>[,<id>...] <note text>
jrnl x task <id>[,<id>...] <note text>  # Alternative command
```

**Update task due date**:
```
jrnl due task <id> <keyword|YYYY-MM-DD>
```
Supports the same due date keywords as task creation.

**Edit task**:
```
jrnl edit task <id> [-text <text>] [-due <date>] [-note <note text>] [-recur <pattern>]
```
Examples:
- `jrnl edit task 1 -text "Updated task title"`
- `jrnl edit task 1 -due @tomorrow`
- `jrnl edit task 1 -recur 2w`

**Edit note**:
```
jrnl edit note <id> [-text <text>] [-link <id>[,<id>,...]] [-unlink <id>[,<id>,...]]
```
Examples:
- `jrnl edit note 1 -text "Updated note text"`
- `jrnl edit note 1 -link 2,3`
- `jrnl edit note 1 -unlink 2`

### Deletion Commands

**Delete notes or tasks**:
```
jrnl rm <note|task> <id>[,<id>,...]
```
Examples:
- `jrnl rm note 1`
- `jrnl rm note 1,2,3`
- `jrnl rm task 1`
- `jrnl rm task 1,2,3`

### Search Commands

**Search for content in tasks and notes**:
```
jrnl find <text>
```
Examples:
- `jrnl find "meeting"`
- `jrnl find "*important*"` (with wildcards)

### Help

**Show help**:
```
jrnl help
jrnl h  # Alternative command
```

## Search Functionality

The search command allows you to find tasks and notes containing specific text:

```
jrnl find <text>
```

Wildcard characters supported:
- `*` - Matches any sequence of zero or more characters
- `?` - Matches any single character

Examples:
- `jrnl find "*task*"` - Find items containing "task" anywhere in the text
- `jrnl find "task ????"` - Find items where "task" is followed by exactly 4 characters
- `jrnl find "task*done"` - Find items that contain "task" followed by "done" with anything in between

The search is case-insensitive and looks through both task titles and note texts.

## Recurring Tasks

`jrnl` supports recurring tasks that automatically create new tasks when completed:

```
jrnl new task "Take out trash" -due @friday -recur 1w
```

This creates a task that recurs weekly. When marked as done, it will automatically create a new instance with the next due date calculated based on the recurrence pattern.

Recurrence patterns:
- `Nd`: Every N days (e.g., `2d` for every 2 days)
- `Nw`: Every N weeks (e.g., `1w` for every week)
- `Nm`: Every N months (e.g., `1m` for every month)
- `Ny`: Every N years (e.g., `1y` for every year)

## Note Linking

Connect related notes to create a knowledge graph:

```
jrnl new note "Project concept" -link 1,2
jrnl edit note 3 -link 4,5
jrnl edit note 3 -unlink 1
```

When you view a specific note, all linked notes will be displayed to help you see the connections in your knowledge network.

## Zettelkasten Support

The note linking functionality enables using `jrnl` as a digital Zettelkasten system, which functions as a "second brain". The Zettelkasten method involves:

1. Creating atomic notes (one idea per note)
2. Linking related notes together
3. Building a web of interconnected knowledge
4. Discovering new connections and insights through the network structure

`jrnl` provides all necessary tools to implement this method effectively.

## Database

The application uses a SQLite database named `jrnl.db` to store all tasks, notes, and their relationships. The database is created automatically if it doesn't exist.

## Testing

The application includes comprehensive unit tests to ensure reliability:

```
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_comprehensive_jrnl.py

# Run tests with verbose output
python -m pytest -v tests/
```

The test suite covers all major functionality of the application and uses the TDD methodology for quality assurance.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Run the test suite to ensure everything works
6. Commit your changes (`git commit -m 'Add some amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.