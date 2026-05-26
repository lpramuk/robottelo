import pytest


@pytest.fixture
def dummy():
    return "I am dummy"


def test_unparametrized_request(request):
    # breakpoint()
    print(request)


@pytest.mark.parametrize("foo", [1, 2])
def test_unparametrized_request_too(request, foo):
    # breakpoint()
    print(foo)
    print(request)


@pytest.mark.parametrize("dummy", [1, 2])
def test_parametrized_request(request, dummy):
    # breakpoint()
    print(request)
    print(dummy)
