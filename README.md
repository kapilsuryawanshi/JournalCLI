# JournalCLI - Task Management Application

## Overview
JournalCLI is a command-line tool for managing tasks and notes with a journal-like interface. It allows users to create, organize, and track tasks with due dates, status updates, and hierarchical structure.

## Features

### Task Management
- Create tasks with optional due dates (`j task <text>`)
- Support for various due date formats:
  - Keywords: `today`, `tomorrow`, `eow` (end of week), `eom` (end of month), `eoy` (end of year)
  - Day names: `monday`, `tuesday`, etc.
  - Explicit dates: `YYYY-MM-DD`
- Task statuses: `todo`, `doing`, `waiting`, `done`
- Hierarchical tasks: Create child tasks under parent tasks
- Recurring tasks with configurable patterns (daily, weekly, monthly, yearly)

### Note Management
- Create standalone notes or notes attached to tasks
- Hierarchical notes (notes under other notes)
- Link notes together for better organization

### Viewing and Filtering
- `j` or `j ls task due`: Show tasks grouped by due date (overdue, today, tomorrow, this week, this month, future)
- `j ls task status`: Show tasks grouped by status (todo, doing, waiting, done)
- `j ls task`: Show all incomplete tasks
- `j ls page` or `j` (default): Show journal view with all tasks and notes grouped by creation date
- `j ls note`: Show all notes

## Change in Behavior

### Hidden Completed Root Tasks
**IMPORTANT CHANGE**: As of this update, the following commands will no longer display root tasks that are marked as completed:
- `j` (default command, shows due tasks)  
- `j ls task due` (shows tasks grouped by due date)
- `j ls task status` (shows tasks grouped by status)
- `j ls page` (shows journal view)

This change was implemented to reduce clutter and focus on active tasks. When a root task is marked as completed, it and its entire subtree (all child tasks) will be hidden from these views.

### Command Syntax
- `j` - Show tasks by due date (default view)
- `j task [@<pid>] <text> [-due <date>] [-recur <Nd|Nw|Nm|Ny>]` - Add a task, optionally under a parent
- `j note [@<pid>] <text>` - Add a note, optionally under a parent note
- `j ls <page|note|task> [due|status|done]` - List items with optional grouping
- `j <start|restart|waiting|done> task <id>` - Update task status
- `j done task <id> [note text]` - Mark task as done with optional note
- `j rm <note|task> <id>` - Delete note or task
- `j task <id> [-text <text>] [-due <date>] [-note <note_text>] [-recur <pattern>]` - Edit task
- `j note <id> [-text <text>] [-link <id>] [-unlink <id>] [-task <text>]` - Edit note

## Examples

1. Create a task with due date: `j task Finish report @tomorrow`
2. Mark task as done: `j done task 5`
3. Show all overdue tasks: `j ls task due` (then look under "Overdue")
4. Create child task: `j task @5 Write introduction` (creates child under task 5)
5. Add note to task: `j note @5 This should include market analysis`

## Technical Notes

The application uses SQLite for data storage. The main tables are:
- `tasks`: Stores task information (title, status, dates, parent task ID, etc.)
- `notes`: Stores note information (text, creation date, task association, parent note ID)
- `note_links`: Stores links between notes

The application automatically excludes completed root tasks and their children from display in commands like `j`, `j ls task due`, and `j ls task status`.