# Example Systemd configuration for Basic Builder

This directory contains an example configuration set for running Basic Builder under systemd.

This presumes you've done a `pip3 install .` in the root of the repository (or in a virtualenv, etc.).

For demonstration purposes, the `ExecStart` path is `/usr/local/bin/bbuilder`, the `EnvironmentFile` is located at `/etc/default/bbuilder`, and that the `User` to execute as is named `git`.

1. Copy `environment.example` to `/etc/default/bbuilder` and edit it to suit your needs.

   **NOTE:** This file contains the sensitive `BB_AUTH_KEY` value. Ensure this file is only readable by trusted users (e.g. mode `400`)!

1. Copy `bbuilder-api.service` and `bbuilder-worker.service` into `/etc/systemd/system`.

1. Run `sudo systemctl daemon-reload` to load the changes to Systemd.

1. If applicable, create your service user.

1. Enable and start the API (`sudo systemctl enable --now bbuilder-api.service`) and Worker (`sudo systemctl enable --now bbuilder-worker.service`).

1. Configure your webhooks, etc.
