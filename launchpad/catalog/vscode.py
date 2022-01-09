import os
import logging

from django.conf import settings

from catalog.base import App, Resource
from catalog.utils import base64_encode

logger = logging.getLogger(__name__)

DEFAULT_VSCODE_PASSWORD = 'admin'


class VSCode(App):
    """
    VSCode Application.
    """
    app_name = 'vscode'
    app_manifests_path = os.path.join(settings.BASE_DIR, 'catalog/manifests/vscode/')

    def __init__(self, session, password=DEFAULT_VSCODE_PASSWORD) -> None:
        self.session = session
        self.password = password

    def normalize_namespace_manifest(self, manifest):
        return manifest.format(name=self.namespace)

    def normalize_secret_manifest(self, manifest):
        return manifest.format(name=self.app_name, password=base64_encode(self.password))

    def normalize_service_manifest(self, manifest):
        return manifest.format(name=self.app_name, port=self.allocate_port())

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
        self.update_app_details_from_cluster(
            wait_for_readiness=wait_for_readiness)
