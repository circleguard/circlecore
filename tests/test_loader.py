import pytest
from circleguard import InvalidKeyException, Loader
from tests.utils import loader


def test_loading_map_id():
    result = loader.map_id("E")
    assert result == 0

    result = loader.map_id("9d0a8fec2fe3f778334df6bdc60b113c")
    assert result == 221777


def test_loading_user_id():
    result = loader.user_id("E")
    assert result == 0

    result = loader.user_id("] [")
    assert result == 13506780

    result = loader.user_id("727")
    assert result == 10750899


def test_loading_username():
    result = loader.username(0)
    assert result == ""

    result = loader.username(13506780)
    assert result == "] ["


def test_incorrect_key():
    loader = Loader("incorrect key")
    with pytest.raises(InvalidKeyException):
        loader.username(13506780)
    with pytest.raises(InvalidKeyException):
        loader.user_id("] [")
    with pytest.raises(InvalidKeyException):
        loader.map_id("9d0a8fec2fe3f778334df6bdc60b113c")
