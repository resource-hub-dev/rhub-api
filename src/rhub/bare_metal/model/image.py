import enum
from abc import abstractmethod
from pathlib import Path

from sqlalchemy.sql import expression

from rhub.api import db
from rhub.api.utils import ModelMixin, TimestampMixin
from rhub.bare_metal.model.common import (
    BARE_METAL_IMAGES_BASE_PATH,
    BareMetalArch,
    BareMetalBootType,
    IRONIC_HTTP_IMAGES_URL,
    _BM_TABLE_NAME_IMAGE,
    _BM_TABLE_NAME_IMAGE_ISO,
    _BM_TABLE_NAME_IMAGE_QCOW2,
)


class BareMetalImageType(str, enum.Enum):
    GENERIC = "generic"
    ISO = "iso"
    QCOW2 = "qcow2"


class ImageBaseOS(str, enum.Enum):
    CENTOS = "CentOS"
    FEDORA = "Fedora"
    RHEL = "RHEL"


class BareMetalImage(db.Model, ModelMixin, TimestampMixin):
    # TODO: review constraints
    __tablename__ = _BM_TABLE_NAME_IMAGE

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=False, server_default="")

    #: :type: :class:`ImageBaseOS`
    base_os = db.Column(db.Enum(ImageBaseOS), nullable=False)

    #: :type: :class:`BareMetalImageType`
    type = db.Column(db.Enum(BareMetalImageType), nullable=False)

    #: :type: :class:`BareMetalArch`
    arch = db.Column(db.Enum(BareMetalArch), nullable=False)

    # boot type - TODO: think of some bitwise operation
    legacy_bios = db.Column(db.Boolean, server_default=expression.true(), nullable=False)
    uefi = db.Column(db.Boolean, server_default=expression.true(), nullable=False)
    uefi_secure_boot = db.Column(db.Boolean, server_default=expression.true(), nullable=False)

    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": BareMetalImageType.GENERIC,
    }

    __table_args__ = (
        db.UniqueConstraint(
            "arch", "base_os", "type", "version", name="unique_image_constraint"
        ),
    )

    @property
    def name(self) -> str:
        return f"{self.base_os} {self.version} {self.arch} {self.type}"

    @property
    def boot_type(self) -> str:
        if self.uefi_secure_boot:
            return BareMetalBootType.UEFI_SECURE_BOOT

        if self.uefi:
            return BareMetalBootType.UEFI

        if self.legacy_bios:
            return BareMetalBootType.LEGACY_BIOS

    @property
    def directory(self) -> Path:
        # TODO: version adjustments before inserting on DB
        directory_suffix = (
            f"{self.base_os}-"
            f"{self.version.strip().replace(' ', '_')}-"
            f"{self.arch}-"
            f"{self.type}-"
            f"{self.boot_type}"
        )
        return BARE_METAL_IMAGES_BASE_PATH / directory_suffix

    @property
    @abstractmethod
    def ansible_playbook_file(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def ansible_playbook_variables(self) -> dict[str, str]:
        raise NotImplementedError()


class BareMetalImageISO(BareMetalImage):
    __tablename__ = _BM_TABLE_NAME_IMAGE_ISO

    # TODO: improve checksums types
    id = db.Column(
        db.Integer,
        db.ForeignKey(f"{BareMetalImage.__tablename__}.id"),
        primary_key=True,
    )
    download_url = db.Column(db.String(1024), nullable=False)
    iso_sha256 = db.Column(db.String(64), unique=True, nullable=False)
    kernel_sub_path = db.Column(db.String(128), nullable=False)
    initramfs_sub_path = db.Column(db.String(128), nullable=False)
    source_sub_path = db.Column(db.String(128), nullable=False)
    stage2_sub_path = db.Column(db.String(128), nullable=False)

    #: :type: :class:`BareMetalProvisionISO`
    deployments = db.relationship("BareMetalProvisionISO", back_populates="image")

    __mapper_args__ = {
        "polymorphic_identity": BareMetalImageType.ISO,
    }

    @property
    def mount_directory(self) -> Path:
        return self.directory / "mount"

    @property
    def iso_file_path(self) -> Path:
        return self.directory / "image.iso"

    @property
    def source_url(self) -> str:
        # ironic requires it to finish in a slash
        return f"{IRONIC_HTTP_IMAGES_URL}/{self.directory.name}/mount/"

    @property
    def source_file_path(self) -> Path:
        return self.mount_directory / self.source_sub_path

    @property
    def kernel_file_path(self) -> Path:
        return self.mount_directory / self.kernel_sub_path

    @property
    def initramfs_file_path(self) -> Path:
        return self.mount_directory / self.initramfs_sub_path

    @property
    def stage2_file_path(self) -> Path:
        return self.mount_directory / self.stage2_sub_path

    @property
    def ansible_playbook_file(self) -> str:
        return "image_iso.yml"

    @property
    def ansible_playbook_variables(self) -> dict[str, str]:
        return {
            "image_directory": str(self.directory),
            "image_file": str(self.iso_file_path),
            "image_sha256": self.iso_sha256,
            "image_url": self.download_url,
            "mount_directory": str(self.mount_directory),
        }


class BareMetalImageQCOW2(BareMetalImage):
    __tablename__ = _BM_TABLE_NAME_IMAGE_QCOW2

    # TODO: improve checksums types
    id = db.Column(
        db.Integer,
        db.ForeignKey(f"{BareMetalImage.__tablename__}.id"),
        primary_key=True,
    )
    image_download_url = db.Column(db.String(1024), nullable=False)
    image_sha256 = db.Column(db.String(64), unique=True, nullable=False)
    kernel_download_url = db.Column(db.String(1024), nullable=False)
    kernel_sha256 = db.Column(db.String(64), unique=True, nullable=False)
    initramfs_download_url = db.Column(db.String(1024), nullable=False)
    initramfs_sha256 = db.Column(db.String(64), unique=True, nullable=False)

    #: :type: :class:`BareMetalProvisionQCOW2`
    deployments = db.relationship("BareMetalProvisionQCOW2", back_populates="image")

    __mapper_args__ = {
        "polymorphic_identity": BareMetalImageType.QCOW2,
    }

    @property
    def image_file_path(self) -> Path:
        return self.directory / "image.qcow2"

    @property
    def kernel_file_path(self) -> Path:
        return self.directory / "image.kernel"

    @property
    def initramfs_file_path(self) -> Path:
        return self.directory / "image.initramfs"

    @property
    def ansible_playbook_file(self) -> str:
        return "image_qcow2.yml"

    @property
    def ansible_playbook_variables(self) -> dict[str, str]:
        return {
            "image_directory": str(self.directory),
            "image_file": str(self.image_file_path),
            "image_sha256": self.image_sha256,
            "image_url": self.image_download_url,
            "initramfs_file": str(self.initramfs_file_path),
            "initramfs_sha256": self.initramfs_sha256,
            "initramfs_url": self.initramfs_download_url,
            "kernel_file": str(self.kernel_file_path),
            "kernel_sha256": self.kernel_sha256,
            "kernel_url": self.kernel_download_url,
        }
