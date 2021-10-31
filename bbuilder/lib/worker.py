#!/usr/bin/env python3

import contextlib
import os
import json
import yaml
from shutil import rmtree
from celery import states
from celery.exceptions import Ignore


class TaskFailure(Exception):
   pass


#
# Workdir context manager
#
@contextlib.contextmanager
def create_workdir(config, task_id):
    workdir_base = config['workdir']
    workdir = f"{workdir_base}/{task_id}"

    cwd = os.getcwd()

    os.makedirs(workdir, exist_ok=True)
    os.chdir(workdir)

    yield workdir

    os.chdir(cwd)
    rmtree(workdir)


def handle_event_gitea(request, config):
    event = request[0].get('X-Gitea-Event', None)
    if event is None:
        meta = f'FATAL: No X-Gitea-Event header in request'
        raise TaskFailure(meta)

    request_json = request[1]
    request_data = json.dumps(request_json, indent=2)
    print(f'Request JSON:\n{request_data}')

    # Get the repository clone_url
    repository = request_json.get('repository', None)
    if repository is None:
        meta = f'FATAL: No repository information in request JSON body'
        raise TaskFailure(meta)
    if config['ssh_key'] is not None:
        clone_url = repository.get('ssh_url')
    else:
        clone_url = repository.get('clone_url')

    # Get the event action (only relevant to Release events)
    event_action = request_json.get('action', None)

    # A push event which has a specific branch as its ref
    if event == 'push':
        ref = request_json.get('ref', None)
        if ref is None:
            meta = f'FATAL: No "ref" in request JSON body'
            raise TaskFailure(meta)

    # A release create event has a ref_type, usually "tag", and a ref (tag name)
    elif event == 'create':
        ref_type = request_json.get('ref_type', None)
        ref_name = request_json.get('ref', None)
        if ref_type is None or ref_name is None:
            meta = f'FATAL: No "ref" or "ref_type" in request JSON body'
            raise TaskFailure(meta)

        if ref_type == 'tag':
            ref_type = 'tags'
        ref = f'refs/{ref_type}/{ref_name}'

    # A release publish event has a release section with a tag_name
    elif event == 'release':
        release_detail = request_json.get('release', None)
        if release_detail is None:
            meta = f'FATAL: No "release" in request JSON body'
            raise TaskFailure(meta)

        tag_name = release_detail.get('tag_name', None)
        if tag_name is None:
            meta = f'FATAL: No "tag_name" in release information'
            raise TaskFailure(meta)

        ref = f'refs/tags/{tag_name}'

        if event_action is None:
            meta = f'FATAL: Event is "release" but no "action" present in JSON body'
            raise TaskFailure(meta)

    return event, event_action, clone_url, ref


def clone_repository(clone_url, config):
    print(f"Cloning repository...")
    if config['ssh_key'] is not None:
        ssh_key_file = config['ssh_key']
        os.environ['GIT_SSH_COMMAND='] = f'ssh -i {ssh_key_file} -o IdentitiesOnly=yes'

    os.system(f'git clone {clone_url} repo')


def parse_config(event, event_action):
    print(f'Parsing config from ".bbuilder-tasks.yaml"...')
    try:
        with open('.bbuilder-tasks.yaml', 'r') as fh:
            bbuilder_config = yaml.load(fh, Loader=yaml.BaseLoader).get('bbuilder', None)
        if bbuilder_config is None:
            raise
    except Exception:
        meta = f'FATAL: Repository ".bbuilder-tasks.yaml" does not exist or is not valid'
        raise TaskFailure(meta)

    tasks = bbuilder_config.get(event, [])
    # For release events, we require sub-categories for the actual event type
    if event == 'release':
        tasks = tasks.get(event_action, [])
        print(f'Tasks to perform for event "{event}.{event_action}":')
    else:
        print(f'Tasks to perform for event "{event}":')
        
    for task in tasks:
        print(f"- {task}")

    return tasks


#
# Entrypoint
#
hooktype_dict = {
    'gitea': handle_event_gitea
}


def do_task(self, config, hooktype, request):
    task_id = self.request.id
    print(f"Starting task {task_id}")

    if hooktype not in hooktype_dict.keys():
        meta = f'FATAL: Hook type "{hooktype}" is not valid.'
        raise TaskFailure(meta)

    event, event_action, clone_url, ref = hooktype_dict.get(hooktype)(request, config)

    print(f"Event type: {event}")
    print(f"Clone URL:  {clone_url}")

    with create_workdir(config, task_id) as workdir:
        print(f"Operating under {workdir}")

        clone_repository(clone_url, config)

        os.chdir('repo')

        print(f"Check out {ref}")
        os.system(f'git checkout {ref}')

        tasks = parse_config(event, event_action)

        for task in tasks:
            os.system(task)

        os.chdir('..')

        print("All tasks completed")
