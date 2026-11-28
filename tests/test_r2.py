import hashlib
import io
from unittest.mock import MagicMock

from botocore.awsrequest import AWSPreparedRequest, AWSResponse
from urllib3 import HTTPResponse

from app.config import config
from app.r2 import R2StorageClient, r2


async def test_delete_sends_no_version_id() -> None:
    client = MagicMock()

    await R2StorageClient(client=client).delete(path="user/1/profile/2/profile.jpg")

    client.delete_object.assert_called_once_with(Bucket=config.STORAGE_BUCKET_NAME, Key="user/1/profile/2/profile.jpg")


async def test_upload_sends_unchunked_signed_payload() -> None:
    requests: list[AWSPreparedRequest] = []

    def respond(request: AWSPreparedRequest, **_: object) -> AWSResponse:
        requests.append(request)

        return AWSResponse(request.url, 200, {}, HTTPResponse(body=io.BytesIO(), preload_content=False))

    r2._client.meta.events.register("before-send", respond)

    await r2.upload(path="user/1/profile/2/profile.jpg", file=b"image", content_type="image/jpeg")

    assert requests[0].body.read() == b"image"
    assert "Content-Encoding" not in requests[0].headers
    assert requests[0].headers["X-Amz-Content-SHA256"] == hashlib.sha256(b"image").hexdigest().encode()
