# pipen-board

Visualize configuration and running of [pipen][1] pipelines on the web.

## Installation

```bash
pip install pipen-board
```

## Usage

```bash
$ pipen board --help
Usage: pipen board [options] <pipeline> -- [pipeline options]

Visualize configuration and running of pipen pipelines on the web

Required Arguments:
  pipeline              The pipeline and the CLI arguments to run the pipeline. For the
                        pipeline either `/path/to/pipeline.py:<pipeline>` or
                        `<module.submodule>:<pipeline>` `<pipeline>` must be an instance of
                        `Pipen` and running the pipeline should be called under `__name__ ==
                        '__main__'.

Options:
  -h, --help            show help message and exit
  --port PORT           Port to serve the UI wizard [default: 18521]
  --name NAME           The name of the pipeline. Default to the pipeline class name. You
                        can use a different name to associate with a different set of
                        configurations.
  --additional FILE     Additional arguments for the pipeline, in YAML, INI, JSON or TOML
                        format. Can have sections `ADDITIONAL_OPTIONS` and `RUNNING_OPTIONS`
  --dev                 Run the pipeline in development mode. This will print verbosal
                        logging information and reload the pipeline if a new instantce
                        starts when page reloads.
  --root ROOT           The root directory of the pipeline. [default: .]
  --loglevel {auto,debug,info,warning,error,critical}
                        Logging level. If `auto`, set to `debug` if `--dev` is set,
                        otherwise `info` [default: auto]
```

## Describing arguments in docstring

### Docstring schema

```python
class ProcessOrProcessGroup:
    """Short summary

    Long description
    Long description

    Args:
        arg1 (<metadata>): description
            - subarg1 (<metadata>): description
            - subarg2 (<metadata>): description
        arg2 (<metadata>): description

    <Other Sections>:
        <content>
    """
```

The metadata can have multiple attributes, separated by semicolon (`;`). For example:

```
arg1 (action=ns;required): description
```

### Marks

You can mark a process using `pipen.utils.mark(<mark>=<value>)` as a decorator to decorate a process. For example:

```python
from pipen import Proc
from pipen.utils import mark

@mark(board_config_no_input=True)
class MyProc(Proc):
    pass
```

Available marks:

- `board_config_no_input`: Whether to show the input section for the process in configuation page. Only affects the start processes. Default to `False`.
- `board_config_hidden`: Whether to hide the process options in the configuration page. Note that the process is still visible in the process list. Default to `False`.

### Metadata for arguments


| Name     | Description | Allowed values |
| -------- | ----------- | -------------- |
| `action` | Like the `action` argument in [`argx`][2]*. | `store_true`, `store_false`, `ns`, `namespace`, `append`, `extend`, `clear_append`, `clear_extend` (other values are allowed but ignore, they may be effective for CLI use) |
| `btype`  | Board type (option type specified directly). If specified, `action` will be ignored | `ns`, `choice`, `mchoice`, `array`, `list`, `json`, `int`, `float`, `bool`, `str`, `text`, `auto`* |
| `type` | Fallback for `action` and `btype` | Same as `btype` |
| `ns`/`namespace` | Shortcut for `btype=ns` | No values needed |
| `choices`/`choice` | Shortcut for `btype=choice` | No values needed |
| `mchoices`/`mchoice` | Shortcut for `btype=mchoice` | No values needed |
| `array`/`list` | Shortcut for `btype=array`/`btype=list` | No values needed |
| `choices`/`choice` | Shortcut for `btype=choice` | No values needed |
| `mchoices`/`mchoice` | Shortcut for `btype=mchoice` | No values needed |
| `order` | The order of the argument in the UI. | Any integer |
| `readonly` | Whether the argument is readonly. | No values needed (True if specified, otherwise False) |
| `required` | Whether the argument is required. | No values needed (True if specified, otherwise False) |
| `placeholder` | The placeholder in the UI for the argument. | Any string |
| `bitype` | The type of the elements in an array or list. | `int`, `float`, `bool`, `str`, `json`, `auto`* |
| `itype` | Fallback for `bitype` | Same as `bitype` |

- `argx*`: An argument parser for Python, compatible with `argparse`.
- `auto*`: Automatically infer the type from a string value.
  - Any of `True`, `TRUE`, `true`, `False`, `FALSE`, `false` will be inferred as a `bool` value.
  - Any of `None`, `NONE`, `none`, `null`, `NULL` will be inferred as `None`.
  - Any integers will be inferred as `int`.
  - Any floats will be inferred as `float`.
  - Try to parse the value as JSON. If succeed, the value will be inferred as `json`.
  - Otherwise, the value will be inferred as `str`.

### Types of options in the UI

The type of an option in the UI is determined by the `btype`, `action` or `type` metadata. If neither is specified, a `PlainText` will be used.

- `BoolOption`: Shown as a switch
- `TextOption`: Shown as a textarea (allow multiple lines)
- `ChoiceOption`: Shown as a dropdown list (`subarg1` and `subarg2` in the example above are used as the choices)
- `MChoiceOption`: Shown as a multiple choice list (`subarg1` and `subarg2` in the example above are used as the choices)
- `JsonOption`: Shown as a textarea, but the value will be validated and parsed as JSON
- `ArrayOption`: Shown as a tag input. Items can be added or removed.
- `AutoOption`: Shown as a 1-row textarea, and the value will be parsed automatically
- `PlainText`: Shown as a plain text. No validation or parsing will be performed.
- `MoreLikeOption`: Show as a box with buttons to add or remove sub-options. It's usally used together with `ns` type. If there is a sub-option under the option in the docstring wrapped by `<...>`, it indicates that we may have more sub-options.


[1]: https://github.com/pwwang/pipen
[2]: https://github.com/pwwang/argx
