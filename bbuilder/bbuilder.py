#!/usr/bin/env python3

import click
import bbuilder.lib.worker

from flask import Flask, request
from celery import Celery

DEFAULT_REDIS_QUEUE = 'redis://127.0.0.1:6379/0'
DEFAULT_WORK_DIR = '/tmp/bbuilder'

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'], max_content_width=120)

config = dict()

# Version function
def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    from pkg_resources import get_distribution
    version = get_distribution('bbuilder').version
    click.echo(f'Basic Builder version {version}')
    ctx.exit()


# Worker CLI entrypoint
@click.command(name='worker', short_help='Run a Basic Builder worker.')
@click.option(
    '-c', '--concurrency', 'concurrency', envvar='BB_CONCURRENCY',
    default=1, show_default=True,
    help='The concurrency of the Celery worker. Envvar: BB_CONCURRENCY'
)
def cli_worker(concurrency):
    """
    Run a Basic Builder worker
    """
    celery = Celery('bbuilder', broker=config['broker'])

    @celery.task(bind=True)
    def do_task(self, hooktype, flask_request):
        return bbuilder.lib.worker.do_task(self, config, hooktype, flask_request)

    worker = celery.Worker(debug=config['debug'], concurrency=concurrency)
    worker.start()
       

# Run CLI entrypoint
@click.command(name='run', short_help='Run the Basic Builder server.')
@click.option(
    '-a', '--listen-addr', 'listen_addr', envvar='BB_LISTEN_ADDR',
    default='0.0.0.0', show_default=True,
    help='Listen on this address. Envvar: BB_LISTEN_ADDR'
)
@click.option(
    '-p', '--listen-port', 'listen_port', envvar='BB_LISTEN_PORT',
    default='7999', show_default=True,
    help='Listen on this port. Envvar: BB_LISTEN_PORT'
)
def cli_run(listen_addr, listen_port):
    """
    Run the Basic Builder server
    """
    app = Flask(__name__)
    app.config['CELERY_BROKER_URL'] = config['broker']
    app.config['CELERY_BROKER_BACKEND'] = config['broker']

    celery = Celery('bbuilder', broker=config['broker'])

    @app.route('/event/<hooktype>', methods=['POST'])
    def gitea_event(hooktype):
        request_json = request.get_json()
        request_headers = dict(request.headers)
        if request_json is None or request_headers is None:
            return False
        flask_request = (request_headers, request_json)
        
        @celery.task(bind=True)
        def do_task(self, hooktype, flask_request):
            return bbuilder.lib.worker.do_task(self, config, hooktype, flask_request)

        task = do_task.delay(hooktype, flask_request)

        return { "task_id": task.id }, 202

    app.run(listen_addr, listen_port, threaded=True, debug=config['debug'])


# Main CLI entrypoint
@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    '--version', is_flag=True, callback=print_version,
    expose_value=False, is_eager=True
)
@click.option(
    '-b', '--broker', 'broker', envvar='BB_BROKER',
    default=DEFAULT_REDIS_QUEUE, show_default=True,
    help='Celery broker URI. Envvar: BB_BROKER'
)
@click.option(
    '-w', '--work-dir', 'workdir', envvar='BB_WORK_DIR',
    default=DEFAULT_WORK_DIR, show_default=True,
    help='Directory to perform build tasks. Envvar: BB_WORK_DIR'
)
@click.option(
    '-d', '--debug', 'debug', envvar='BB_DEBUG',
    default=False, is_flag=True,
    help='Enable debug mode. Envvar: BB_DEBUG'
)
def cli(broker, workdir, debug):
    """
    Basic Builder (bbuilder) CLI
    """
    global config
    config['broker'] = broker
    config['workdir'] = workdir
    config['debug'] = debug


cli.add_command(cli_worker)
cli.add_command(cli_run)

#
# Main entrypoint
#
def main():
    return cli(obj={})


if __name__ == '__main__':
    main()
