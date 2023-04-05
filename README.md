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

[1]: https://github.com/pwwang/pipen
