# Launchpad ![ci](https://github.com/Qubad786/launchpad/actions/workflows/ci.yaml/badge.svg)
This is your launchpad that comes with a variety of applications waiting to run on your kubernetes cluster with a single click.

# Development setup

## Prerequisites
1. Make (on mac via homebrew: brew install make)
2. Docker
3. DockerCompose
4. A functioning Kubernetes cluster (`~/.kube/config` is used with current context by default)

## Installation
Launchpad runs the following service containers:
1. web server
2. celery
3. celery beat
4. redis
5. postgres 



### helpers
```bash
# start services
make up

# start services in detached mode
make up-d

# restart the service containers
make restart

# see web logs 
make logs

# see celery logs
make clogs

# attach to python shell
make shell

# ssh into web service container
make ssh

# ssh into celery service container
make cssh

# stop services
make stop

# remove service containers
make down
```
