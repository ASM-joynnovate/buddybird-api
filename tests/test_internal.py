from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from pytest_mock import MockerFixture

from app.main import app

HEADERS = {"X-Queue-Message-Id": "message-1", "X-Queue-Attempts": "1", "X-Queue-Timestamp": "1795651200000"}
USER_ID = "019ac2b0-0000-7000-8000-000000000001"
SESSION_ID = "019ac2b0-0000-7000-8000-000000000002"
SOUND_ID = "019ac2b0-0000-7000-8000-000000000003"
WORD_ID = "019ac2b0-0000-7000-8000-000000000004"
FILE_ID = "019ac2b0-0000-7000-8000-000000000005"
DELIVERY_ID = "019ac2b0-0000-7000-8000-000000000006"
CRON_TASKS = {
    "withdrawal.dispatch": "dispatch_due_withdrawals",
    "session.check_heartbeats": "finish_expired_sessions",
    "push.dispatch": "dispatch_due_pushes",
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def consume(client: TestClient, name: str, body: dict[str, Any]) -> Response:
    return client.post(f"/internal/queues/{name}", json={"body": body, "trace": {}}, headers=HEADERS)


def test_notification_delivers_push(client: TestClient, mocker: MockerFixture) -> None:
    deliver = mocker.patch("app.routers.internal.deliver")

    response = consume(client, "notification", {"type": "push.send", "delivery_id": DELIVERY_ID})

    assert response.status_code == 200
    deliver.assert_awaited_once_with(UUID(DELIVERY_ID))


def test_withdrawal_processes_user(client: TestClient, mocker: MockerFixture) -> None:
    process_user_withdrawal = mocker.patch("app.routers.internal.process_user_withdrawal")

    response = consume(client, "withdrawal", {"type": "withdrawal.process", "user_id": USER_ID})

    assert response.status_code == 200
    process_user_withdrawal.assert_awaited_once_with(UUID(USER_ID))


def test_judgment_result_saves_parrot_detection(client: TestClient, mocker: MockerFixture) -> None:
    db = mocker.patch("app.routers.internal.session_factory").return_value.__aenter__.return_value
    save_parrot_detection = mocker.patch("app.routers.internal.save_parrot_detection", return_value=[UUID(SESSION_ID)])
    send_report = mocker.patch("app.routers.internal.send_report")
    data = [{"audio_id": SOUND_ID, "is_parrot": True}]

    response = consume(
        client,
        "judgment-result",
        {
            "type": "audio.parrot_detected",
            "model_version": "parrot-detection-1",
            "analyzed_at": "2026-11-26T00:00:00+00:00",
            "data": data,
        },
    )

    assert response.status_code == 200
    save_parrot_detection.assert_awaited_once_with(
        db=db, model_version="parrot-detection-1", analyzed_at=datetime(2026, 11, 26, tzinfo=UTC), data=data
    )
    send_report.assert_awaited_once_with(db=db, session_ids=[UUID(SESSION_ID)])


def test_judgment_result_saves_mimic_judgment(client: TestClient, mocker: MockerFixture) -> None:
    db = mocker.patch("app.routers.internal.session_factory").return_value.__aenter__.return_value
    save_mimic_judgment = mocker.patch("app.routers.internal.save_mimic_judgment")
    send_report = mocker.patch("app.routers.internal.send_report")
    judgment = {"is_mimic": True, "score": 0.9}

    response = consume(
        client,
        "judgment-result",
        {
            "type": "audio.mimic_judged",
            "session_id": SESSION_ID,
            "model_version": "mimic-judgment-1",
            "analyzed_at": "2026-11-26T00:00:00+00:00",
            "target": {"audio_id": SOUND_ID},
            "reference": {"word_id": WORD_ID},
            "judgment": judgment,
        },
    )

    assert response.status_code == 200
    save_mimic_judgment.assert_awaited_once_with(
        db=db,
        sound_id=UUID(SOUND_ID),
        word_id=UUID(WORD_ID),
        model_version="mimic-judgment-1",
        judged_at=datetime(2026, 11, 26, tzinfo=UTC),
        judgment=judgment,
    )
    send_report.assert_awaited_once_with(db=db, session_ids=[UUID(SESSION_ID)])


def test_parrot_sound_detection_dlq_marks_failed(client: TestClient, mocker: MockerFixture) -> None:
    db = mocker.patch("app.routers.internal.session_factory").return_value.__aenter__.return_value
    mark_parrot_detection_failed = mocker.patch("app.routers.internal.mark_parrot_detection_failed")
    send_report = mocker.patch("app.routers.internal.send_report")
    data = [{"audio_id": SOUND_ID, "object_key": "user/1/session/2/sound.wav"}]

    response = consume(
        client,
        "parrot-sound-detection-dlq",
        {"type": "audio.detect_parrot", "session_id": SESSION_ID, "data": data},
    )

    assert response.status_code == 200
    mark_parrot_detection_failed.assert_awaited_once_with(db=db, data=data)
    send_report.assert_awaited_once_with(db=db, session_ids=[UUID(SESSION_ID)])


def test_mimicry_judgment_dlq_marks_failed(client: TestClient, mocker: MockerFixture) -> None:
    db = mocker.patch("app.routers.internal.session_factory").return_value.__aenter__.return_value
    mark_mimic_judgment_failed = mocker.patch("app.routers.internal.mark_mimic_judgment_failed")
    send_report = mocker.patch("app.routers.internal.send_report")

    response = consume(
        client,
        "mimicry-judgment-dlq",
        {"type": "audio.judge_mimic", "session_id": SESSION_ID, "target": {"audio_id": SOUND_ID}},
    )

    assert response.status_code == 200
    mark_mimic_judgment_failed.assert_awaited_once_with(db=db, sound_id=UUID(SOUND_ID))
    send_report.assert_awaited_once_with(db=db, session_ids=[UUID(SESSION_ID)])


def test_unknown_queue_returns_404(client: TestClient) -> None:
    response = consume(client, "periodic-command", {"type": "push.dispatch"})

    assert response.status_code == 404


def test_failed_handler_returns_500(
    client: TestClient, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    mocker.patch("app.routers.internal.deliver", side_effect=RuntimeError)

    response = consume(client, "notification", {"type": "push.send", "delivery_id": DELIVERY_ID})

    assert response.status_code == 500
    assert "메시지 처리 실패; queue=notification message_id=message-1" in caplog.text


@pytest.mark.parametrize("task", CRON_TASKS)
def test_cron_runs_task(client: TestClient, mocker: MockerFixture, task: str) -> None:
    mocker.patch("app.routers.internal.session_factory")
    mocker.patch("app.routers.internal.send_report")
    functions = {name: mocker.patch(f"app.routers.internal.{name}") for name in CRON_TASKS.values()}

    response = client.post(f"/internal/cron/{task}")

    assert response.status_code == 200
    assert {name: function.await_count for name, function in functions.items()} == {
        name: int(name == CRON_TASKS[task]) for name in functions
    }


def test_unknown_cron_task_returns_404(client: TestClient) -> None:
    response = client.post("/internal/cron/unknown.task")

    assert response.status_code == 404


def test_upload_confirmation_reads_r2_event(client: TestClient, mocker: MockerFixture) -> None:
    process = mocker.patch("app.routers.internal.uploads.process")
    key = f"upload/user/{USER_ID}/profile/{FILE_ID}/profile.jpg"

    response = client.post(
        "/internal/queues/upload-confirmation",
        json={
            "account": "account-id",
            "action": "PutObject",
            "bucket": "jn-buddybird-data-dev",
            "object": {"key": key, "size": 65536, "eTag": "etag"},
            "eventTime": "2026-11-26T00:00:00.000Z",
        },
        headers=HEADERS,
    )

    assert response.status_code == 200
    process.assert_awaited_once_with(key=key, size=65536)


@pytest.mark.parametrize(
    ("key", "processed"),
    [
        (f"upload/notification/{FILE_ID}/image.jpg", True),
        (f"user/{USER_ID}/word/{FILE_ID}/word.wav", True),
        (f"user/{USER_ID}/session/{FILE_ID}/sound.wav", True),
        (f"user/{USER_ID}/petcam/{FILE_ID}/image.jpg", True),
        (f"user/{USER_ID}/profile/{FILE_ID}/profile.jpg", False),
        (f"user/{USER_ID}/parrot/{FILE_ID}/photo.jpg", False),
        (f"preset/{FILE_ID}/word.wav", False),
    ],
)
def test_upload_confirmation_processes_only_target_keys(
    client: TestClient, mocker: MockerFixture, key: str, processed: bool
) -> None:
    process = mocker.patch("app.routers.internal.uploads.process")

    response = client.post(
        "/internal/queues/upload-confirmation",
        json={"object": {"key": key, "size": 1}},
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert process.await_count == int(processed)
