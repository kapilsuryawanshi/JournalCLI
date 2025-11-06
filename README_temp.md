# j - Command Line Journal and Task Manager

`j` is a powerful, minimalist command-line tool for managing tasks and notes. Designed for speed and simplicity, it allows users to efficiently track tasks, create notes, and organize information directly from the terminal.

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
4. Use the application directly: `python jrnl_app.py` (or create an alias/script to run it as `j`)

## Dependencies

- Python 3.x
- SQLite3 (typically included with Python)
- Colorama (for colored output): `pip install colorama`

## Usage

```
j [command] [arguments...]
```

## Commands

### List Commands

**List tasks by due date (default view)**:
```
j list task due
j ls task due  # New alias for 'list'
j  # This command is equivalent to the above
```
Shows tasks grouped by due date: Overdue, Due Today, Due Tomorrow, This Week, This Month, Future, No Due Date

**List journal by creation date**:
```
j list page
j ls page  # New alias for 'list'
```
Shows all entries grouped by creation date

**List all unfinished tasks**:
```
j list task
j ls task  # New alias for 'list'
```

**List tasks by status**:
```
j list task status
j ls task status  # New alias for 'list'
```
Shows tasks grouped by status: Todo, Doing, Waiting

**List completed tasks**:
```
j list task done
j ls task done  # New alias for 'list'
```
Shows completed tasks grouped by completion date

**List all notes**:
```
j list note
j ls note  # New alias for 'list'
```

**Show specific note with linked notes**:
```
j note <id>
```
Shows the specific note with linked notes. To edit, use additional options like `-text`, `-link`, `-unlink`. To add a task under this note, use `-task <text>`.

**Show specific task**:
```
j task <id>
```
Shows the specific task details with its subtasks. To edit, use additional options like `-text`, `-due`, `-note`, `-recur`.

### Creation Commands

**Create tasks**:
```
j task [@<pid>] <text> [-due <YYYY-MM-DD|keyword>] [-recur <Nd|Nw|Nm|Ny>]
```
Examples:
- `j task "Buy groceries"`
- `j task @123 "Meeting with team" -due tomorrow`
- `j task "Weekly report" -due eow -recur 1w`

Due date keywords: `today`, `tomorrow`, `eow` (end of week), `eom` (end of month), `eoy` (end of year), day names (monday, tuesday, etc.)

Recurrence patterns: `Nd` (N days), `Nw` (N weeks), `Nm` (N months), `Ny` (N years)

**Create notes**:
