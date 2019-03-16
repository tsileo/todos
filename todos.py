from typing import List
from typing import Optional
from typing import Dict
from typing import Any
import sys
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

import yaml

from blobstash.docstore import DocStoreClient
from blobstash.docstore import LuaScript
from blobstash.docstore import Q

CURRENT_YEAR = datetime.now().year

RED = "\033[1;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[;33m"
RESET = "\033[0;0m"


def red(text: str) -> str:
    return RED + text + RESET


def yellow(text: str) -> str:
    return YELLOW + text + RESET


def green(text: str) -> str:
    return GREEN + text + RESET


# The following MapReduce script is for extracting Markdown TODOs in the notes collection (looking at checkboxes `[ ]`)
# and conver them as todo item
map_step = LuaScript(
    """
-- Python equivalent to splitlines
function splitlines(s)
  if s:sub(-1)~="\\n" then s=s.."\\n" end
  return s:gmatch("(.-)\\n")
end

-- find and emit TODO item (by looking at checkbox (`[ ]`)
return function(doc)
  if doc.content == nil then return end

  -- keep track of the line number (needed to uniquely identify a TODO within a note)
  local l = 1
  for s in splitlines(doc.content) do
    -- if the line contains a Markdown checkbox, then it's a TODO
    if s:find("%[ %]") then
      local dat = {}
      dat[doc._id] = { version = doc._version, todo = { text = s, line = l, note_title = doc.title } }
      emit("todos", dat)
    end
    l = l + 1
  end
end
"""
)

reduce_step = LuaScript(
    """
-- group the TODO items by document ID
return function(key, vs)
  local out = {}
  for _, v in ipairs(vs) do
    for did, todo in pairs(v) do
      if out[did] ~= nil then
        table.insert(out[did].todos, todo.todo)
      else
        out[did] = { todos = { todo.todo }, version = todo.version, note_title = todo.title }
      end
    end
  end
  return out
end
"""
)


@dataclass
class TodoItem:
    _id: str
    raw_todo: Dict[str, Any]
    raw_version: str

    @property
    def todo(self) -> str:
        """Remove everyting before the checkbox."""
        if self.raw_todo["line"]:
            return self.raw_todo["text"].split("[ ]")[1].strip()

        return self.raw_todo["text"]

    @property
    def todo_color(self) -> str:
        """Add some bash coloring based on the priority and add the source tag (task or note)."""
        todo = self.todo

        # Add color for the prioritized tasks
        if "p:H" in todo:
            todo = red(todo.replace("p:H", "").strip())
        elif "p:M" in todo:
            todo = yellow(todo.replace("p:M", "").strip())

        if self.raw_todo["line"]:
            # The note doesn't have a title, return a [note] tag
            if not self.raw_todo.get("note_title"):
                return f"[note]\t\t{todo}"

            # Cut the title if it's too long
            title = self.raw_todo["note_title"]
            if len(title) > 15:
                title = title[:12] + "..."
            return f"{title}\t{todo}"

        # The note was created from the `todos` CLI, add a [cli] tag
        return f"[cli]\t\t{todo}"

    @property
    def version(self) -> datetime:
        return datetime.fromtimestamp(float(self.raw_version) / 1e9)

    @property
    def id(self) -> str:
        if self.raw_todo["line"]:
            # Take the last few bytes (this is the random part of the ID)
            return (self._id[-5:] + str(self.raw_todo["line"]))[::-1]

        return self._id[-6:][::-1]

    @property
    def date(self) -> str:
        if self.version.year != CURRENT_YEAR:
            return self.version.strftime("%Y-%m-%d @ %H:%M")

        return self.version.strftime("%b %d @ %H:%M")

    @property
    def p(self) -> int:
        if "p:H" in self.raw_todo["text"]:
            return 3
        elif "p:M" in self.raw_todo["text"]:
            return 2
        else:
            return 1


def list_todos(tasks_col, col, as_of) -> List[TodoItem]:
    """Combine and sort todo items (using the MapReduce and querying the tasks collection."""
    todos = []

    # 1. Perform a MapReduce to fetch TODOs from the notes
    mr = col.map_reduce(map_step, reduce_step, as_of=as_of)
    if "todos" in mr:
        for _id, raw_todos in mr["todos"].items():
            for todo in raw_todos["todos"]:
                todos.append(TodoItem(_id, todo, raw_todos["version"]))

    # 2. Fetch TODOs from the tasks
    for task in tasks_col.query(
        Q["done"] == False, as_of=as_of
    ):  # noqa  # PEP8 does not like the `== False`
        todos.append(
            TodoItem(
                task["_id"].id(),
                {"text": task["action"], "line": None},
                task["_id"].version(),
            )
        )

    # Returns the todo sorted by most recent
    return sorted(todos, key=lambda d: (d.p, d.raw_version), reverse=True)


def filter_todos(tasks_col, col, as_of: str, q: str) -> List[TodoItem]:
    """Performs a basic text match."""
    todos = []
    for todo in list_todos(tasks_col, col, as_of):
        if q in todo.todo:
            todos.append(todo)

    return todos


def select_todo(tasks_col, col, short_id: str) -> Optional[TodoItem]:
    """Returns the first todo that which ID match the short ID (short prefix)."""
    for todo in list_todos(tasks_col, col, ""):
        if todo.id.startswith(short_id):
            return todo

    return None


def help() -> None:
    print(
        """todos - Task system powered by BlobStash Docstore and Markdown notes.

Usage:
    # add a new todo
    $ todos add new todo item

    # list all todos
    $ todos

    # filter by text
    $ todos +work

    # mark as done (the full ID is not needed, just input the first letter, even one letter is enough)
    $ todos <idprefix> done

"""
    )


def main() -> None:  # noqa: C901
    """CLI interface."""
    cli_args = sys.argv[1:]

    # Check if the help is requested
    if len(cli_args) == 1 and cli_args[0] in ["--help", "-h"]:
        help()
        return

    # Config check
    CONFIG_FILE = Path("~/.config/todos.yaml").expanduser()
    try:
        with CONFIG_FILE.open() as f:
            config = yaml.load(f, Loader=yaml.SafeLoader)
    except FileNotFoundError:
        print(f"Please create config file at {CONFIG_FILE}")
        return

    # Setup
    client = DocStoreClient(base_url=config["base_url"], api_key=config["api_key"])
    col = client[config["notes_col"]]
    tasks_col = client[config["todos_col"]]
    as_of = ""

    # Extract the "as_of", if any
    for i, arg in enumerate(cli_args.copy()):
        if arg.startswith("asof:"):
            as_of = arg.replace("asof:", "")
            cli_args.pop(i)

    # List tasks when no args are given
    if not cli_args:
        for todo in list_todos(tasks_col, col, as_of):
            print(f"{todo.id}\t{todo.date}\t{todo.todo_color}")
    elif len(cli_args) == 1:
        for todo in filter_todos(tasks_col, col, as_of, cli_args[0]):
            print(f"{todo.id}\t{todo.date}\t{todo.todo_color}")

    # Adding a new task
    elif cli_args[0] == "add":
        todo_text = " ".join(cli_args[1:]).strip()
        tasks_col.insert({"action": todo_text, "done": False})
        print(green("Task added"))

    # Actions on a specific todo
    elif len(cli_args) == 2:
        short_id, action = cli_args
        if action not in ["done"]:
            print(f"Action {action!r} is an invalid")
            return

        # Mark a todo as done
        todo = select_todo(  # type: ignore  # Mypy does not like the re-assignment
            tasks_col, col, short_id
        )
        if not todo:
            print(f"No task matching id {short_id!r}")
            return

        # The task was extracted from a note
        if todo.raw_todo["line"]:
            # From the note collection
            note = col.get_by_id(todo._id)
            lines = note["content"].splitlines()

            lines[todo.raw_todo["line"] - 1] = lines[todo.raw_todo["line"] - 1].replace(
                "[ ]", "[x]"
            )
            note["content"] = "\r\n".join(lines)
            col.update(note)
        else:
            # It's coming from the tasks collection
            task = tasks_col.get_by_id(todo._id)
            task["done"] = True
            tasks_col.update(task)

        print(green(f"Task {todo.id} done"))

    # Display the help
    else:
        help()


if __name__ == "__main__":
    main()
