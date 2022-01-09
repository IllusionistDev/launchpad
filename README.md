# Launchpad ![ci](https://github.com/Qubad786/launchpad/actions/workflows/ci.yaml/badge.svg)
This is your launchpad that comes with a variety of applications waiting to run on your kubernetes cluster with a single click.

# Development setup

## Prerequisites
1. Make (on mac via homebrew: brew install make)
2. Docker
3. DockerCompose
4. A functioning Kubernetes cluster (`~/.kube/config` is used with current context by default)

### Minikube Cluster Setup
```bash
# If you're on MBP M1 follow installation steps below OR
# follow instructions for other platforms @
# https://minikube.sigs.k8s.io/docs/start/

# Install minikube binariess (M1)
$ curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-darwin-arm64
$ sudo install minikube-darwin-arm64 /usr/local/bin/minikube

# Start minikube cluster
$ minikube start

# Open a terminal tab and run following to start proxy access to services.
$ minikube tunnel

# Minikube comes with a nice dashboard that lets you see the state of cluster intuitively.
$ minikube dashboard --url

🤔  Verifying dashboard health ...
🚀  Launching proxy ...
🤔  Verifying proxy health ...
URL: http://127.0.0.1:57298/api/v1/namespaces/kubernetes-dashboard/services/http:kubernetes-dashboard:/proxy/

Pretty Easy!
```

## Project Installation
Launchpad runs the following service containers:
1. web server
2. celery
3. celery beat
4. redis
5. postgres 

### One liner installation script
```bash
source <(curl -s https://raw.githubusercontent.com/Qubad786/launchpad/master/install.sh)
```

### Admin Panel
Django admin is running at: http://localhost:8080/admin, You can use following credentials to login:
```bash
Username: admin
Password: admin
```

### Swagger API Docs
Swagger API docs are located at http://localhost:8080/swagger, you should be able to try some APIs there.

### Debug
Django Debug Toolbar @ http://localhost:8080/__debug__

### Useful make targets

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

# generate migrations
make migrations

# apply migrations
make migrate

# install requirements
make requirements

# stop services
make stop

# remove service containers
make down
```
