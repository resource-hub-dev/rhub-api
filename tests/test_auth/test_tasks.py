from unittest.mock import ANY
import pytest
from rhub.auth import model as auth_model
from rhub.openstack import model as openstack_model
from rhub.auth import tasks as auth_tasks


def test_cleanup_users(mocker, di_mock, ldap_client_mock, messaging_mock):
    manager = auth_model.User(
        id=2,
        external_uuid=None,
        ldap_dn='uid=manager,dc=example,dc=com',
        name='manager',
        email='manager@example.com',
        manager_id=None,
        manager=None,
    )
    user = auth_model.User(
        id=1,
        external_uuid=None,
        ldap_dn='uid=user,dc=example,dc=com',
        name='user',
        email='user@example.com',
        manager_id=manager.id,
        manager=manager,
    )

    mocker.patch('rhub.auth.tasks.di', new=di_mock)

    auth_model.User.query.filter.return_value = [user]
    ldap_client_mock.get.return_value = []  # => user has been deleted from LDAP

    query_result_mock = mocker.Mock()
    openstack_model.Project.query.filter.return_value = query_result_mock

    auth_tasks.cleanup_users()

    ldap_client_mock.get.assert_called_with(user.ldap_dn)
    messaging_mock.send.assert_called_with('auth.user.delete', ANY, extra=ANY)

    query_result_mock.update.assert_called_with(
        {'owner_id': manager.id},
        synchronize_session='fetch',
    )
