import enum
import logging
from abc import abstractmethod

from ironicclient.client import get_client as get_ironic_client
from ironicclient.exc import StateTransitionFailed
from ironicclient.v1.client import Client
from ironicclient.v1.utils import PROVISION_ACTIONS

from rhub.api import db
from rhub.api.utils import ModelMixin, TimestampMixin
from rhub.bare_metal.model.common import (
    BareMetalArch,
    BareMetalException,
    IronicNode,
    _BM_TABLE_NAME_HANDLER,
)
from rhub.lab.model import Location

logger = logging.getLogger(__name__)


class IronicClient(Client):
    def change_and_wait_provision_state(self, node_uuid, new_state):
        # TODO: check states in PROVISION_ACTIONS.keys()

        self.node.set_provision_state(node_uuid, new_state)
        try:
            self.node.wait_for_provision_state(
                node_uuid,
                expected_state=PROVISION_ACTIONS[new_state]["expected_state"],
                poll_interval=PROVISION_ACTIONS[new_state]["poll_interval"],
            )
        except StateTransitionFailed as error:
            node = self.node.get(node_uuid)
            logger.exception(
                f"Error transitioning state - {error!r} - {node.last_error}"
            )
            raise BareMetalException() from error

    def get_node(self, node_uuid) -> IronicNode:
        return self.node.get(node_uuid)

    @staticmethod
    def operation_for_uefi_secure_boot() -> dict:
        return {
            "op": "add",
            "path": "/instance_info/capabilities",
            "value": {"secure_boot": "true"},
        }


class BareMetalHandlerType(str, enum.Enum):
    IRONIC = "ironic"


class BareMetalHandlerStatus(str, enum.Enum):
    AVAILABLE = "available"
    FAILED_API_CHECK = "failed_api_check"
    FAILED_SSH_CHECK = "failed_ssh_check"
    MAINTENANCE = "maintenance"
    UNAVAILABLE = "unavailable"


class BareMetalHandler(db.Model, ModelMixin, TimestampMixin):
    __tablename__ = _BM_TABLE_NAME_HANDLER

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)

    #: :type: :class:`BareMetalHandlerType`
    type = db.Column(db.Enum(BareMetalHandlerType), nullable=False)

    #: :type: :class:`BareMetalArch`
    arch = db.Column(db.Enum(BareMetalArch), nullable=False)

    #: :type: :class:`BareMetalHandlerStatus`
    status = db.Column(
        db.Enum(BareMetalHandlerStatus),
        server_default=BareMetalHandlerStatus.UNAVAILABLE.name,
        nullable=False,
    )
    last_check = db.Column(db.DateTime(timezone=True))
    last_check_error = db.Column(db.Text)

    location_id = db.Column(
        db.Integer, db.ForeignKey(f"{Location.__tablename__}.id"), nullable=False
    )
    #: :type: :class:`Location`
    location = db.relationship("Location")

    #: :type: :class:`BareMetalHost`
    hosts = db.relationship("BareMetalHost", back_populates="handler")

    __mapper_args__ = {
        "polymorphic_on": type,
    }

    @abstractmethod
    def get_client(self):
        raise NotImplementedError()

    def is_available(self) -> bool:
        return self.status is BareMetalHandlerStatus.AVAILABLE

    # TODO: rename
    def can_update_status(self) -> bool:
        return self.status in {
            BareMetalHandlerStatus.AVAILABLE,
            BareMetalHandlerStatus.UNAVAILABLE,
        }


class BareMetalIronicHandler(BareMetalHandler):
    user_name = db.Column(db.String(128), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    base_url = db.Column(db.String(128), nullable=False, unique=True)
    hostname = db.Column(db.String(128), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": BareMetalHandlerType.IRONIC,
    }

    def get_client(self) -> IronicClient:
        client = get_ironic_client(
            api_version=1,
            os_ironic_api_version="latest",
            auth_type="http_basic",
            endpoint=self.base_url,
            username=self.user_name,
            password=self.password,
        )
        client.__class__ = IronicClient
        return client

    def to_dict(self) -> dict[str, str]:
        data = super().to_dict()
        del data['password']
        return data
