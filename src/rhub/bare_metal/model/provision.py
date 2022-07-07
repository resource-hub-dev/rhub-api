import enum
import json
import logging
from abc import abstractmethod
from copy import deepcopy
from pathlib import Path
from typing import TextIO

from flask import url_for

from rhub.api import db, jinja_env
from rhub.api.utils import ModelMixin, TimestampMixin
from rhub.bare_metal.model.common import (
    BARE_METAL_KICKSTART_BASE_PATH,
    BARE_METAL_UTILS_PATH,
    BareMetalBootType,
    _BM_TABLE_NAME_HOST,
    _BM_TABLE_NAME_IMAGE_ISO,
    _BM_TABLE_NAME_IMAGE_QCOW2,
    _BM_TABLE_NAME_PROVISION,
    _BM_TABLE_NAME_PROVISION_ISO,
    _BM_TABLE_NAME_PROVISION_QCOW2,
)

logger = logging.getLogger(__name__)

GET_KS_DEBUG_SCRIPT_ENDPOINT = "/v0.rhub_api_bare_metal_provision_provision_kickstart_debug_script_get"
UPLOAD_LOGS_ENDPOINT = "/v0.rhub_api_bare_metal_provision_provision_logs_upload"

# https://opendev.org/openstack/ironic/src/branch/stable/yoga/ironic/drivers/modules/ks.cfg.template
with (BARE_METAL_UTILS_PATH / "ironic_template_data.json").open(encoding="utf-8") as json_file:
    IRONIC_TEMPLATE_DATA = json.load(json_file)


class BareMetalProvisionType(str, enum.Enum):
    GENERIC = "generic"
    ISO = "iso"
    QCOW2 = "qcow2"


class BareMetalProvisionStatus(str, enum.Enum):
    ACTIVE = "active"
    FAILED_PROVISIONING_DEPLOY_HOST = "failed_provisioning_deploy_host"
    FAILED_PROVISIONING_SYNC_IMAGE = "failed_provisioning_sync_image"
    FAILED_RETURNING_HOST = "failed_returning_host"
    FINISHED = "finished"
    PROVISIONING_DEPLOY_HOST = "provisioning_deploy_host"
    PROVISIONING_ENDING = "provisioning_ending"
    PROVISIONING_SYNC_IMAGE = "provisioning_sync_image"
    QUEUED = "queued"
    RETURNING_HOST = "returning_host"


class BareMetalProvision(db.Model, ModelMixin, TimestampMixin):
    __tablename__ = _BM_TABLE_NAME_PROVISION

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False, server_default="")

    #: :type: :class:`BareMetalProvisionType`
    type = db.Column(db.Enum(BareMetalProvisionType), nullable=False)

    #: :type: :class:`BareMetalBootType`
    boot_type = db.Column(db.Enum(BareMetalBootType), nullable=False)

    #: :type: :class:`BareMetalProvisionStatus`
    status = db.Column(
        db.Enum(BareMetalProvisionStatus),
        server_default=BareMetalProvisionStatus.QUEUED.name,
        nullable=False,
    )

    host_id = db.Column(db.Integer, db.ForeignKey(f"{_BM_TABLE_NAME_HOST}.id"), nullable=False)
    #: :type: :class:`BareMetalHost`
    host = db.relationship("BareMetalHost", back_populates="deployments")
    host_reservation_expires_at = db.Column(db.DateTime(timezone=True))

    logs_path = db.Column(db.String(1024))

    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": BareMetalProvisionType.GENERIC,
    }

    @property
    @abstractmethod
    def ironic_operations(self) -> list[dict]:
        raise NotImplementedError()


class BareMetalProvisionISO(BareMetalProvision):
    __tablename__ = _BM_TABLE_NAME_PROVISION_ISO

    id = db.Column(
        db.Integer,
        db.ForeignKey(f"{BareMetalProvision.__tablename__}.id"),
        primary_key=True,
    )
    kickstart = db.Column(db.Text)

    image_id = db.Column(db.Integer, db.ForeignKey(f"{_BM_TABLE_NAME_IMAGE_ISO}.id"), nullable=False)
    #: :type: :class:`BareMetalImageISO`
    image = db.relationship("BareMetalImageISO", back_populates="deployments")

    __mapper_args__ = {
        "polymorphic_identity": BareMetalProvisionType.ISO,
    }

    @property
    def kickstart_rendered(self) -> str:
        template_data = deepcopy(IRONIC_TEMPLATE_DATA)

        url = url_for(GET_KS_DEBUG_SCRIPT_ENDPOINT, provision_id=self.id, _external=True)
        template_data["on_error"] = f"/usr/bin/curl {url} | bash\n" + template_data["on_error"]

        data = {
            "hostname": self.host.name,
            "resource_hub": template_data,
        }
        return jinja_env.from_string(self.kickstart).render(**data)

    @property
    def kickstart_file(self) -> Path:
        return BARE_METAL_KICKSTART_BASE_PATH / f"kickstart_{self.id}.cfg"

    @property
    def debug_script(self) -> str:
        """
        Once the kickstart provisioning hits an error, it will call an endpoint (GET_KS_DEBUG_SCRIPT_ENDPOINT) to get
        this debug script.

        This method should be improved to:
            - provide a proper token for uploading the debug logs;
            - provide different debug scripts based on the provisioning (arch, OS, ...);
        """

        url = url_for(UPLOAD_LOGS_ENDPOINT, provision_id=self.id, _external=True)
        script = (BARE_METAL_UTILS_PATH / "kickstart_debug_script.sh").read_text(encoding="utf-8")

        # TODO: create temp token and put it on this curl call
        script += f'\n/usr/bin/curl -F "file=@/tmp/install-logs-$date.tbz" {url}\n'
        return script

    def write_kickstart_content(self, kickstart_local_file: TextIO) -> dict[str, str]:
        kickstart_local_file.write(self.kickstart_rendered)
        kickstart_local_file.flush()
        return {
            "kickstart_file": str(self.kickstart_file),
            "kickstart_local_file": kickstart_local_file.name,
        }

    @property
    def ironic_operations(self) -> list[dict]:
        return [
            {"op": "replace", "path": "/deploy_interface", "value": "anaconda"},
            {
                "op": "add",
                "path": "/instance_info/image_source",
                "value": self.image.source_url,
            },
            {
                "op": "add",
                "path": "/instance_info/kernel",
                "value": f"file://{self.image.kernel_file_path}",
            },
            {
                "op": "add",
                "path": "/instance_info/ks_template",
                "value": f"file://{self.kickstart_file}",
            },
            {
                "op": "add",
                "path": "/instance_info/ramdisk",
                "value": f"file://{self.image.initramfs_file_path}",
            },
            {
                "op": "add",
                "path": "/instance_info/stage2",
                "value": f"file://{self.image.stage2_file_path}",
            },
            {
                "op": "add",
                "path": "/instance_info/disk_file_extension",
                "value": ".img",
            },
            # TODO: discuss
            {"op": "add", "path": "/instance_info/root_gb", "value": 50},
        ]


class BareMetalProvisionQCOW2(BareMetalProvision):
    __tablename__ = _BM_TABLE_NAME_PROVISION_QCOW2

    id = db.Column(
        db.Integer,
        db.ForeignKey(f"{BareMetalProvision.__tablename__}.id"),
        primary_key=True,
    )

    image_id = db.Column(db.Integer, db.ForeignKey(f"{_BM_TABLE_NAME_IMAGE_QCOW2}.id"), nullable=False)
    #: :type: :class:`BareMetalImageQCOW2`
    image = db.relationship("BareMetalImageQCOW2", back_populates="deployments")

    __mapper_args__ = {
        "polymorphic_identity": BareMetalProvisionType.QCOW2,
    }

    @property
    def ironic_operations(self) -> list[dict]:
        return [
            {"op": "replace", "path": "/deploy_interface", "value": "direct"},
            {
                "op": "add",
                "path": "/instance_info/image_source",
                "value": f"file://{self.image.image_file_path}",
            },
            {
                "op": "add",
                "path": "/instance_info/kernel",
                "value": f"file://{self.image.kernel_file_path}",
            },
            {
                "op": "add",
                "path": "/instance_info/ramdisk",
                "value": f"file://{self.image.initramfs_file_path}",
            },
            # TODO: discuss
            {"op": "add", "path": "/instance_info/root_gb", "value": 50},
        ]
