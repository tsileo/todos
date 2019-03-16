# todos

Manage TODO list from the command line.
Uses [BlobStash](http://github.com/tsileo/blobstash) as backend.

## Features

 - Tasks created from the CLI are stored inside a special DocStore collections
 - Extract Markdown TODOs (like `[ ] item`) directly from other DocStore collections

## Install

    $ pip install git+https://github.com/tsileo/todos
    # Create the config file
    $ vim ~/.config/todos.yaml

### Config

```yaml
base_url: 'http://localhost:8050'
api_key: '123'
notes_col: 'test'
todos_col: 'todos_cli'
```

## Usage

See the help.

    $ todos -h
