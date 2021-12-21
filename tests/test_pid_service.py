from unittest.mock import MagicMock

import pytest

from molgenis.bbmri_eric.errors import EricError
from molgenis.bbmri_eric.pid_service import PidService, Status


@pytest.fixture
def handle_client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def pid_service(handle_client) -> PidService:
    return PidService(handle_client, "test")


def test_reverse_lookup(pid_service, handle_client):
    handle_client.search_handle.return_value = ["pid1", "pid2"]

    result = pid_service.reverse_lookup("my_url")

    handle_client.search_handle.assert_called_with(URL="my_url", prefix="test")
    assert result == ["pid1", "pid2"]


def test_reverse_lookup_no_auth(pid_service, handle_client):
    handle_client.search_handle.return_value = None

    with pytest.raises(EricError) as e:
        pid_service.reverse_lookup("my_url")

    assert str(e.value) == "Insufficient permissions for reverse lookup"


def test_register_pid(pid_service: PidService, handle_client):
    handle_client.generate_and_register_handle.return_value = "pid1"

    result = pid_service.register_pid("url", "biobank1")

    handle_client.generate_and_register_handle.assert_called_with(
        prefix="test", location="url", NAME="biobank1"
    )
    assert result == "pid1"


def test_set_name(pid_service: PidService, handle_client):
    pid_service.set_name("pid1", "new_name")
    handle_client.modify_handle_value.assert_called_with("pid1", NAME="new_name")


def test_set_status(pid_service: PidService, handle_client):
    pid_service.set_status("pid1", Status.TERMINATED)
    handle_client.modify_handle_value.assert_called_with("pid1", STATUS="TERMINATED")


def test_remove_status(pid_service: PidService, handle_client):
    pid_service.remove_status("pid1")
    handle_client.delete_handle_value.assert_called_with("pid1", "STATUS")
