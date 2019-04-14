# todos

<a href="https://d.a4.io/tsileo/todos"><img src="https://d.a4.io/api/badges/tsileo/todos/status.svg" alt="Build Status"></a>
<a href="https://github.com/tsileo/todos/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-ISC-red.svg?style=flat" alt="License"></a>
<a href="https://github.com/ambv/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>


Manage TODO list from the command line.
Uses [BlobStash](http://github.com/tsileo/blobstash) as backend.

## Features

 - You get to see cats 😻
 - Tasks created from the CLI are stored inside a special DocStore collections
 - Extract Markdown TODOs (like `[ ] item`) directly from other DocStore collections
 - Basic prioritazion support (just add `p:H` or `p:M` to attach priority, default is low (L)), with colorized bash output
 - Support time-travel listing (using `asof:YYYY-MM-DD` and other formats)

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
