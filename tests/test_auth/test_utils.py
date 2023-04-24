import pytest
from rhub.auth import utils as auth_utils


@pytest.mark.parametrize(
    'original, normalized',
    [
        ('ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPcQ5pAiQVQl8Hb0Z2LcltOU0Vt58e/RQo9BiTn9YtUd alf@melmac',
         'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPcQ5pAiQVQl8Hb0Z2LcltOU0Vt58e/RQo9BiTn9YtUd'),
        ('AAAAC3NzaC1lZDI1NTE5AAAAIPcQ5pAiQVQl8Hb0Z2LcltOU0Vt58e/RQo9BiTn9YtUd alf@melmac',
         'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPcQ5pAiQVQl8Hb0Z2LcltOU0Vt58e/RQo9BiTn9YtUd'),
        ('AAAAC3NzaC1lZDI1NTE5AAAAIPcQ5pAiQVQl8Hb0Z2LcltOU0Vt58e/RQo9BiTn9YtUd',
         'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPcQ5pAiQVQl8Hb0Z2LcltOU0Vt58e/RQo9BiTn9YtUd'),
        ('ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7gYc6YDmGwW3Y8l4zMXfrWVGadcGLo7sI9OI90+h2NcaDkof3h8WUgzJig0tU3D9gy8EDLtzKx9ydDvg3o5mQSEde0KR6WZkv/aU5WPCgcod5BorQgyxKbbHVJ1mOaJ9DG/BJpmPxu9s8gRQUFHOB4GBnz6gTGVMKMWfpYGorWvfMwmN22eiUDBY2dcm3PQyBBJLXkEDQ6QI8mrDTvm8++f6i6W/aVORbAbu+FPNTZQZQVxOG9xBtgHpkKX1f2vx2pgN+kAtx02m4oS3GcBS9+W+JNfIM4X8Rc0x5KgwSbmyBn3q43L6p7XIL0jTQPIm9daNHh05IWZlhlrcuSI0xrk/EaK5bZT5TAdVYpnKrmJZBVGvYo6PJtCWkwsPlF/fNKOlfODTaATkvwed59ZCT560zLpBTg3qOZSqWvBOyZ2GlivlcMhM4XvFijnzYOlVP90m31VfWEjEGb2EkJleywZXZydJcmdcVKh14YC149oEI31PboqyPZAcgP7do6E0=',
         'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7gYc6YDmGwW3Y8l4zMXfrWVGadcGLo7sI9OI90+h2NcaDkof3h8WUgzJig0tU3D9gy8EDLtzKx9ydDvg3o5mQSEde0KR6WZkv/aU5WPCgcod5BorQgyxKbbHVJ1mOaJ9DG/BJpmPxu9s8gRQUFHOB4GBnz6gTGVMKMWfpYGorWvfMwmN22eiUDBY2dcm3PQyBBJLXkEDQ6QI8mrDTvm8++f6i6W/aVORbAbu+FPNTZQZQVxOG9xBtgHpkKX1f2vx2pgN+kAtx02m4oS3GcBS9+W+JNfIM4X8Rc0x5KgwSbmyBn3q43L6p7XIL0jTQPIm9daNHh05IWZlhlrcuSI0xrk/EaK5bZT5TAdVYpnKrmJZBVGvYo6PJtCWkwsPlF/fNKOlfODTaATkvwed59ZCT560zLpBTg3qOZSqWvBOyZ2GlivlcMhM4XvFijnzYOlVP90m31VfWEjEGb2EkJleywZXZydJcmdcVKh14YC149oEI31PboqyPZAcgP7do6E0=')
    ]
)
def test_normalize_ssh_key(original, normalized):
    assert auth_utils.normalize_ssh_key(original) == normalized


@pytest.mark.parametrize(
    'original',
    [
        'ssh-ed25519 AAAA= alf@melmac',
        'ssh-ed25519 alf@melmac',
    ]
)
def test_normalize_ssh_key_invalid(original):
    with pytest.raises(ValueError):
        auth_utils.normalize_ssh_key(original)
