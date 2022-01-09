import abc
import os
import yaml
import random
import json
import time
import logging
from enum import Enum
from functools import cached_property

from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from kubernetes import config, client

from catalog.exceptions import ManifestNotFound

__all__ = ['App', 'Resource']

logger = logging.getLogger(__name__)


def load_kube_config():
    config.load_kube_config(config_file=settings.KUBE_CONFIG)
    if settings.DEBUG:
        # Development setup is running minikube, which needs to
        # be accessible via minikube network.
        conf_copy = config.kube_config.Configuration.get_default_copy()
        conf_copy.host = 'https://minikube:8443'
        conf_copy.verify_ssl = False
        config.kube_config.Configuration.set_default(conf_copy)


# loading config at module level so api clients
# are correctly initialized.
load_kube_config()


class Resource(Enum):
    """
    Supported Kubernetes Resources so far.
    """
    NAMESPACE = 'namespace'
    SECRET = 'secret'
    PVC = 'pvc'
    DEPLOYMENT = 'deployment'
    SERVICE = 'service'

    @classmethod
    def all(cls):
        return [member for __, member in cls.__members__.items()]


class App(abc.ABC):
    """
    An abstract class that provides all the essentials to
    launch an App into a Kubernetes cluster seamlessly.
    """
    session = None

    app_name = None
    app_manifests_path = None
    resources = Resource.all()

    _k8s_core_v1 = client.CoreV1Api()
    _k8s_apps_v1 = client.AppsV1Api()
    _app_details = {
        'session': session,
        'app_url': None,
        'status': None,
        'last_checked_at': None
    }
    _resource_actions = {
        Resource.NAMESPACE: _k8s_core_v1.create_namespace,
        Resource.SECRET: _k8s_core_v1.create_namespaced_secret,
        Resource.PVC: _k8s_core_v1.create_namespaced_persistent_volume_claim,
        Resource.DEPLOYMENT: _k8s_apps_v1.create_namespaced_deployment,
        Resource.SERVICE: _k8s_core_v1.create_namespaced_service,
    }
    _ports_cache_key = 'app_ports'
    _ports_min = 9000
    _ports_max = 65535

    @cached_property
    def _allocated_ports(self):
        return json.loads(cache.get(self._ports_cache_key) or '[]')

    def is_port_avaliable(self, port):
        return port not in self._allocated_ports

    def allocate_port(self):
        """
        Allocate port in range of 9000 -> 65535
        """
        port = random.randint(self._ports_min, self._ports_max)
        while True:
            if self.is_port_avaliable(port):
                break
            port = random.randint(self._ports_min, self._ports_max)
            time.sleep(0.05)

        cache.set(self._ports_cache_key, json.dumps(self._allocated_ports + [port]))
        return port

    def release_port(self, port):
        ports = self._allocated_ports
        try:
            ports.remove(port)
        except ValueError:
            return
        cache.set(self._ports_cache_key, json.dumps(ports))

    @cached_property
    def namespace(self):
        return f"{self.app_name}-{self.session}"

    @property
    def details(self):
        return self._app_details

    @property
    def status(self):
        pods = self._k8s_core_v1.list_namespaced_pod(
            namespace=self.namespace).items
        if pods:
            return pods[0].status.phase

    def get_app_url(self):
        services = self._k8s_core_v1.list_namespaced_service(
            namespace=self.namespace).items
        if services:
            service = services[0]
            if ingress := service.status.load_balancer.ingress:
                return f"http://{ingress[0].ip}:{service.spec.ports[0].port}"

    def update_app_details_from_cluster(self, wait_for_readiness=False):
        """
        Update app details from the cluster.

        Arguments:
          wait_for_readiness: Wait until the app is ready and accessible.
        """
        def wait_for_workload_to_be_ready():
            app_status = self.status
            while app_status is None or app_status == 'Pending':
                # wait for 300ms before pulling
                # status again.
                time.sleep(0.3)
                app_status = self.status
                logger.info("Waiting for '%s' to be ready..", self.app_name)

        def wait_for_public_ip_assignment():
            app_url = self.get_app_url()
            while app_url is None:
                # wait for 300ms before pulling
                # status again.
                time.sleep(0.3)
                app_url = self.get_app_url()
                logger.info("Waiting for '%s' to be assigned a public IP address..", self.app_name)

        if wait_for_readiness:
            wait_for_workload_to_be_ready()
            wait_for_public_ip_assignment()

        self._app_details['status'] = self.status
        self._app_details['app_url'] = self.get_app_url()
        self._app_details['last_checked_at'] = timezone.now()
        return self._app_details

    def get_resource_handler(self, resource):
        return self._resource_actions[resource]

    def normalize_resource_manifest(self, resource: Resource, manifest: str):
        attr_name = f"normalize_{resource.value}_manifest"
        if hasattr(self, attr_name):
            normalization_handler = getattr(self, attr_name)
            if callable(normalization_handler):
                return normalization_handler(manifest)
        # by default, appname would be formatted into the manifest.
        return manifest.format(name=self.app_name)

    def get_resource_manifest(self, resource):
        assert resource in self.resources, f"Invalid resource name {resource}"
        resource_manifest_filename = f"{resource.value}.yaml"
        resource_manifest_path = os.path.join(
            self.app_manifests_path, resource_manifest_filename)
        if os.path.exists(resource_manifest_path):
            with open(resource_manifest_path, 'r') as fd:
                return yaml.safe_load(self.normalize_resource_manifest(
                    resource=resource,
                    manifest=fd.read()
                ))
        else:
            raise ManifestNotFound(
                f"Manifest for resource '{resource.value}' not found in {self.app_manifests_path} directory."
            )

    def _check_for_reraise(exc: client.ApiException):
        info = json.loads(exc.body)
        if (reason := info.get('reason').lower()) == 'alreadyexists':
            return reason
        else:
            raise exc

    def _skip_if_already_exists(self, k8s_action_handler, *args, **kwargs):
        """
        Wraps actions into to suppress exceptions if resource already exists in cluster.

        Returns:
          resource or status if resource exists.
        """
        def __check_for_reraise(exc: client.ApiException):
            info = json.loads(exc.body)
            if (reason := info.get('reason').lower()) == 'alreadyexists':
                return reason
            else:
                raise exc

        try:
            return k8s_action_handler(*args, **kwargs)
        except client.ApiException as exc:
            return __check_for_reraise(exc)

    def _invoke_resource_hook(self, resource, prefix: str):
        hook_name = f"{resource.value}_{prefix}"
        if hasattr(self, hook_name):
            handler = getattr(self, hook_name)
            if callable(handler):
                return handler()

    def _resource_pre_create(self, resource):
        """
        Resource pre-create hook that an App may implement per resource.
        """
        return self._invoke_resource_hook(resource, 'pre_create')

    def _resource_post_create(self, resource):
        """
        Resource post-create hook that an App may implement per resource.
        """
        return self._invoke_resource_hook(resource, 'post_create')

    def create_resource(self, resource, include_namespace=False):
        assert resource in self.resources, f"Invalid resource {resource}."
        # pre create hook
        self._resource_pre_create(resource=resource)
        # whether to include namespace or not
        kwargs = {}
        if include_namespace:
            kwargs['namespace'] = self.namespace
        # create resource
        manifest = self.get_resource_manifest(resource=resource)
        handler = self.get_resource_handler(resource=resource)
        result = self._skip_if_already_exists(handler, body=manifest, **kwargs)
        # post create hook
        self._resource_post_create(resource=resource)
        return result

    def launch(self, wait_for_readiness=False):
        """
        Provide the App's launch sequence.

        Arguments:
          wait_for_readiness: Wait until the app is ready and accessible.

        Example implementation could be:
          self.create_resource(resource=Resource.NAMESPACE)
          self.create_resource(resource=Resource.SECRET, include_namespace=True)
          self.create_resource(resource=Resource.PVC, include_namespace=True)
          ...
        """
        raise NotImplementedError("Must implement App launch sequence.")

    def uninstall(self, wait_until_uninstalled=False):
        """
        Uninstall the Application.

        Arguments:
            wait_until_uninstalled: Waits until namespace is terminated, check every 1000ms.
        """
        # retrieve in-use port so it can be released.
        port = None
        self.update_app_details_from_cluster()
        if self.details['app_url']:
            port = int(self.details['app_url'].rsplit(':', 1)[1])

        try:
            self._k8s_core_v1.delete_namespace(name=self.namespace)
        except client.ApiException as exc:
            exc_info = json.loads(exc.body)
            if exc_info['reason'] == 'NotFound':
                logger.info("No such app: '%s'", self.namespace)
                return

        if wait_until_uninstalled:
            while True:
                try:
                    self._k8s_core_v1.read_namespace(name=self.namespace)
                    logger.info("Waiting for namespace %s to terminate..", self.namespace)
                    time.sleep(1)
                except client.ApiException:
                    break

            logger.info("Uninstalled '%s' successfully.", self.namespace)
        else:
            logger.info("Uninstall has been started for '%s'.", self.namespace)

        if port:
            # release port now.
            self.release_port(port=port)
