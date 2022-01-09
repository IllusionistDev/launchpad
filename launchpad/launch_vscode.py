import abc
import sys
import uuid
import os
import yaml
import json
import base64
import time
import random
import logging
import datetime
from enum import Enum

from kubernetes import config, client

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_KUBE_CONFIG = '~/.kube/config'
DEFAULT_VSCODE_PASSWORD = 'admin'

config.load_kube_config(config_file=DEFAULT_KUBE_CONFIG)


class AppConfigError(Exception):
  pass


class ManifestNotFound(AppConfigError):
  pass


def get_short_uuid():
  return str(uuid.uuid4()).rsplit('-', 1)[1]


def base64_encode(secret: str):
    return base64.b64encode(secret.encode('utf-8')).decode('utf-8')


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

  @property
  def namespace(self):
    return f"{self.app_name}-{self.session}"

  @property
  def details(self):
    return self._app_details

  @property
  def status(self):
    pods = self._k8s_core_v1.list_namespaced_pod(namespace=self.namespace).items
    if pods:
      return pods[0].status.phase

  def get_app_url(self):
    services = self._k8s_core_v1.list_namespaced_service(namespace=self.namespace).items
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
    self._app_details['last_checked_at'] = datetime.datetime.utcnow()
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
    resource_manifest_path = os.path.join(self.app_manifests_path, resource_manifest_filename)
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
    NOTE: Waits until namespace is terminated, check every 1000ms.
    """
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


class VSCode(App):
  """
  VSCode Application.
  """
  app_name = 'vscode'
  app_manifests_path = '/Users/muhammadrehan/Documents/strata/code-challenge/apps/vscode'

  def __init__(self, session, password=DEFAULT_VSCODE_PASSWORD) -> None:
      self.session = session
      self.password = password

  def normalize_namespace_manifest(self, manifest):
    return manifest.format(name=self.namespace)

  def normalize_secret_manifest(self, manifest):
    return manifest.format(name=self.app_name, password=base64_encode(self.password))

  def normalize_service_manifest(self, manifest):
    port = random.randint(9000, 9999)
    # TODO: check if the port is used by some session.
    return manifest.format(name=self.app_name, port=port)

  def deployment_pre_create(self):
    # Create resources that needs to be there before the
    # deployment goes-off.
    self.create_resource(resource=Resource.NAMESPACE)
    self.create_resource(resource=Resource.SECRET, include_namespace=True)
    self.create_resource(resource=Resource.PVC, include_namespace=True)

  def deployment_post_create(self):
    # Expose to public by creating service after deployment's deployed.
    self.create_resource(resource=Resource.SERVICE, include_namespace=True)

  def launch(self, wait_for_readiness=False):
      self.create_resource(resource=Resource.DEPLOYMENT, include_namespace=True)
      self.update_app_details_from_cluster(wait_for_readiness=wait_for_readiness)

if __name__ == '__main__':
    session = get_short_uuid()
    vscode_app = VSCode(session=session)
    vscode_app.launch(wait_for_readiness=True)

    # record the session into the file.
    with open('./installed_apps.txt', 'a') as fp:
      fp.write(f"{session}\n")

    app_details = vscode_app.details
    app_details['last_checked_at'] = (app_details['last_checked_at']
                                      .strftime("%m/%d/%Y, %H:%M:%S"))
    print("==============================================================")
    print("App Launched with details: ", json.dumps(app_details, indent=2))
    print("==============================================================")
