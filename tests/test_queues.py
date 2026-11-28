import json

import httpx
import pytest
from pytest_mock import MockerFixture
from tenacity import wait_none

from app import queues


def respond_with(mocker: MockerFixture, statuses: list[int]) -> list[httpx.Request]:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)

        return httpx.Response(statuses[len(requests) - 1])

    mocker.patch.object(queues, "http_client", httpx.AsyncClient(transport=httpx.MockTransport(handle)))
    mocker.patch.object(queues.publish.retry, "wait", wait_none())

    return requests


async def test_send_publishes_envelope_after_transient_failures(mocker: MockerFixture) -> None:
    requests = respond_with(mocker, [503, 429, 204])

    await queues.send(queue="notification", body={"type": "push.send", "delivery_id": "1"})

    assert [str(request.url) for request in requests] == ["http://queues.test/notification"] * 3
    assert json.loads(requests[-1].content)["body"] == {"type": "push.send", "delivery_id": "1"}
    assert "trace" in json.loads(requests[-1].content)


async def test_send_raises_after_five_transient_failures(mocker: MockerFixture) -> None:
    requests = respond_with(mocker, [503] * 5)

    with pytest.raises(httpx.HTTPStatusError):
        await queues.send(queue="notification", body={})

    assert len(requests) == 5


async def test_send_does_not_retry_rejected_message(mocker: MockerFixture) -> None:
    requests = respond_with(mocker, [404])

    with pytest.raises(httpx.HTTPStatusError):
        await queues.send(queue="unknown", body={})

    assert len(requests) == 1
