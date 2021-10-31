# Basic Builder

Basic Builder (bbuilder) is an extraordinarily simple CI tool. Send it webhooks from a Git management system (e.g. Gitea) and it will perform a basic set of tasks on your repository in response.

Tasks are specified in the `.bbuilder-tasks.yaml` file in the root of the repository. The specific events to operate on can be configured both from the webhook side, as well as via the YAML configuration inside the repository. A task can be any shell command which can be run by Python's `os.system` command.

## How Basic Builder works

At its core Basic Builder has two parts: a Flask API for handling webhook events, and a Celery worker daemon for executing the tasks.

The Flask API portion listens for webhooks from a compatible Git system, and the Celery worker then takes that request, clones the repository to a working directory, checks out the relevant `ref`, reads the tasks from `.bbuilder-tasks.yaml` for the current event type, and then executes them sequentially.

## Dependencies

1. Redis or another Celery-compatible broker system is required for the communication between the API and the worker(s).

1. The Python dependencies can be installed via `pip install -r requirements.txt`.

## Using Basic Builder

1. Help, as with all Click applications, can be shown with the `-h`/`--help` flags:

   ```
   $ bbuilder --help
   Usage: bbuilder [OPTIONS] COMMAND [ARGS]...

     Basic Builder (bbuilder) CLI

   Options:
     --version
     -b, --broker TEXT    Celery broker URI. Envvar: BB_BROKER  [default: redis://127.0.0.1:6379/0]
     -w, --work-dir TEXT  Directory to perform build tasks. Envvar: BB_WORK_DIR  [default: /tmp/bbuilder]
     -d, --debug          Enable debug mode. Envvar: BB_DEBUG
     -h, --help           Show this message and exit.

   Commands:
     run     Run the Basic Builder server.
     worker  Run a Basic Builder worker.
   ```

1. Run the API with the following command:

   ```
   $ bbuilder run
   ```

   By default, the API will listen on `0.0.0.0:7999`; you may change this with the `-a`/`--listen-addr` and `-p`/`--listen-port` options, for example:

   ```
   $ bbuilder --listen-addr 127.0.0.1 --listen-port 4000
   ```

1. Run a worker with the following command:

   ```
   $ bbuilder.py worker
   ```

   **NOTE:** The worker runs with `concurrency=1` by default, so all tasks will be run sequentially in the order they are sent. To allow for higher load, consider setting the `-c`/`--concurrency` setting to a higher value. Note however that this may cause some tasks, for instance during release creation, to occur out of order.

1. Configure your Git system to send webhooks for the event(s) and repositories you want to the Basic Builder API.

1. Optionally, configure Basic Builder to run under Systemd via the [example configurations](systemd/).

## Webhook Configuration

**NOTE:** Currently, Basic Builder supports only Gitea webhooks. However, other systems may be supported in the future.

Webhooks are sent to Basic Builder in JSON POST format, i.e. `POST` method and `application/json` content type.

Normally, Basic Builder should be sent only "Repository Events" type webhook events, and only the following events are handled by Basic Builder:

 * "Push": A normal push to a branch.

 * "Create": The creation of a tag.

 * "Release": The creation or editing of a release.

**NOTE:** Basic Builder is, as the name implies, extremely basic. These 3 are very likely the only 3 event types we will support. If you require more, a more complex CI system is what you're looking for.

## `.bbuilder-tasks.yaml`

Within each repository configured for Basic Builder must be a `.bbuilder-tasks.yaml` configuration.

For example, the following `.bbuilder-tasks.yaml` specifies a simple set of `echo` tasks to run on `push`, Tag `create`, and Release `published` events:

```
---
bbuilder:
  push:
    - echo pushed
  create:
    - echo created
  release:
    published:
      - echo published
```

You can extrapolate from here how to leverage Basic Builder to perform other tasks you may want on your repository. Each section is optional; if Basic Builder doesn't find any relevant tasks, it simply won't execute anything.

**NOTE:** The commands specified in `.bbuilder-tasks.yaml` are always run relative to the root of the repository on the relevant `ref`, either a branch for `push` events, or a tag for `create` or `release` events.

**NOTE:** The commands specified in `.bbuilder-tasks.yaml` are run with the privileges of the `bbuilder worker` process. Normally, this should not be `root`, but if it does need to be, **be very careful and remember that Basic Builder is implicitly trusting the content of this configuration in all repositories it is configured for**.
