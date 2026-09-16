import asyncio
import hashlib
from contextlib import suppress
from uuid import UUID, uuid7

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.db import transactional
from app.errors import (
    AuthenticationError,
    AuthenticationServiceUnavailableError,
    OAuthCredentialError,
    OAuthCredentialRequiredError,
    UserSaveUnavailableError,
    WithdrawalOperationError,
)
from app.models import File, OAuthProviderEnum, User, UserOAuthCredential
from app.oauth.apple import verify_apple_credential
from app.oauth.base import SocialIdentity, credential_cipher, decrypt_credentials, encrypt_credentials, match_identity
from app.oauth.google import verify_google_credential
from app.oauth.supabase import get_social_identities
from app.s3 import S3StorageClient
from app.schemas.auth import LoginDTO, LoginRequest
from app.services.users import delete_uploaded_photo, download_social_photo


async def verify_login_credential(
    *, db: AsyncSession, user_id: UUID, data: LoginRequest | None, identities: list[SocialIdentity]
) -> UserOAuthCredential | None:
    if data is None or (data.apple is None and data.google is None):
        return None

    credential_cipher()
    proof_digest = None

    if data.apple is not None:
        client_id = data.apple.client_id
        code = data.apple.authorization_code.get_secret_value()
        proof_digest = hashlib.sha256(code.encode()).hexdigest()

        saved = await db.scalar(
            select(UserOAuthCredential).where(
                UserOAuthCredential.user_id == user_id,
                UserOAuthCredential.provider == OAuthProviderEnum.APPLE.value,
                UserOAuthCredential.client_id == client_id,
                UserOAuthCredential.proof_digest == proof_digest,
            )
        )

        if saved is not None:
            subject = decrypt_credentials(saved.credentials_ciphertext)["subject"]
            identity = match_identity(identities=identities, provider=OAuthProviderEnum.APPLE, subject=subject)

            if identity.identity_id != saved.identity_id:
                raise OAuthCredentialError

            return saved

        identity, refresh_token = await verify_apple_credential(
            client_id=client_id, authorization_code=code, identities=identities
        )
    else:
        identity, refresh_token = await verify_google_credential(
            refresh_token=data.google.refresh_token.get_secret_value(), identities=identities
        )
        client_id = config.GOOGLE_CLIENT_ID

    return UserOAuthCredential(
        user_id=user_id,
        identity_id=identity.identity_id,
        client_id=client_id,
        provider=identity.provider.value,
        credentials_ciphertext=encrypt_credentials({"subject": identity.subject, "refresh_token": refresh_token}),
        proof_digest=proof_digest,
    )


async def complete_login(
    *, db: AsyncSession, storage: S3StorageClient, auth_user_id: UUID, access_token: str, data: LoginRequest | None
) -> LoginDTO:
    identities = await get_social_identities(auth_user_id=auth_user_id, access_token=access_token)
    profile = min(identities, key=lambda item: (item.created_at, item.identity_id))

    user = await db.scalar(
        select(User).where(User.auth_user_id == auth_user_id).execution_options(include_deleted=True)
    )

    if user is not None and user.is_deleted:
        raise AuthenticationError

    user_id = user.id if user is not None else uuid7()

    try:
        credential = await verify_login_credential(db=db, user_id=user_id, data=data, identities=identities)
    except WithdrawalOperationError:
        raise AuthenticationServiceUnavailableError from None

    credential_required = any(
        identity.provider in {OAuthProviderEnum.GOOGLE, OAuthProviderEnum.APPLE} for identity in identities
    )
    photo_file = None
    uploaded_path = None
    uploaded_version_id = None

    if user is None and profile.photo_url:
        photo = await download_social_photo(url=profile.photo_url, provider=profile.provider)

        if photo is not None:
            content, file_name, file_type = photo
            file_id = uuid7()
            file_path = f"user/{user_id}/profile/{file_id}"
            path = f"{file_path}/{file_name}"

            with suppress(BotoCoreError, ClientError, OSError, TimeoutError):
                uploaded_version_id = await storage.upload(path=path, file=content)
                uploaded_path = path
                photo_file = File(
                    id=file_id,
                    file_name=file_name,
                    file_path=file_path,
                    file_size=len(content),
                    file_type=file_type,
                    is_deleted=False,
                )

    try:
        login = await save_login(
            db=db,
            user_id=user_id,
            auth_user_id=auth_user_id,
            email=profile.email,
            credential=credential,
            credential_required=credential_required,
            photo_file=photo_file,
        )
    except Exception, asyncio.CancelledError:
        if uploaded_path is not None:
            await delete_uploaded_photo(storage=storage, path=uploaded_path, version_id=uploaded_version_id)

        raise

    if uploaded_path is not None and not login.is_new_user:
        await delete_uploaded_photo(storage=storage, path=uploaded_path, version_id=uploaded_version_id)

    return login


@transactional(unavailable_error=UserSaveUnavailableError)
async def save_login(
    *,
    db: AsyncSession,
    user_id: UUID,
    auth_user_id: UUID,
    email: str | None,
    credential: UserOAuthCredential | None,
    credential_required: bool,
    photo_file: File | None,
) -> LoginDTO:
    await db.execute(
        insert(User)
        .values(id=user_id, auth_user_id=auth_user_id, email=email, is_deleted=False)
        .on_conflict_do_nothing(index_elements=[User.auth_user_id])
    )

    user = (
        await db.scalars(
            select(User)
            .where(User.auth_user_id == auth_user_id)
            .execution_options(include_deleted=True, populate_existing=True)
        )
    ).one()

    if user.is_deleted:
        raise AuthenticationError

    is_new_user = user.id == user_id

    if is_new_user and credential is None and credential_required:
        raise OAuthCredentialRequiredError

    if credential is not None:
        await db.execute(
            insert(UserOAuthCredential)
            .values(
                user_id=user.id,
                identity_id=credential.identity_id,
                client_id=credential.client_id,
                provider=credential.provider,
                credentials_ciphertext=credential.credentials_ciphertext,
                proof_digest=credential.proof_digest,
            )
            .on_conflict_do_update(
                index_elements=[
                    UserOAuthCredential.user_id,
                    UserOAuthCredential.identity_id,
                    UserOAuthCredential.client_id,
                ],
                set_={
                    "credentials_ciphertext": credential.credentials_ciphertext,
                    "proof_digest": credential.proof_digest,
                },
            )
        )

    if is_new_user and photo_file is not None:
        user.photo_file = photo_file

    return LoginDTO(user_id=user.id, is_new_user=is_new_user)
