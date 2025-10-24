from typing import List

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from q_developer_boto3 import boto3 as q_boto3

from neopilot.ai_gateway.api.auth_utils import StarletteUser
from neopilot.ai_gateway.auth.glgo import GlgoAuthority, cloud_connector_token_context_var
from neopilot.ai_gateway.integrations.amazon_q.errors import (
    AccessDeniedExceptionReason,
    AWSException,
    raise_aws_errors,
)
from neopilot.ai_gateway.structured_logging import get_request_logger
from neopilot.ai_gateway.tracking import log_exception

request_log = get_request_logger("amazon_q")

__all__ = [
    "AmazonQClientFactory",
    "AmazonQClient",
]


class AmazonQClientFactory:
    def __init__(
        self,
        glgo_authority: GlgoAuthority,
        endpoint_url: str,
        region: str,
    ):
        self.glgo_authority = glgo_authority
        self.sts_client = boto3.client("sts", region)
        self.endpoint_url = endpoint_url
        self.region = region

    def get_client(self, current_user: StarletteUser, role_arn: str):
        token = self._get_glgo_token(current_user)
        credentials = self._get_aws_credentials(current_user, token, role_arn)

        return AmazonQClient(
            url=self.endpoint_url,
            region=self.region,
            credentials=credentials,
        )

    def _get_glgo_token(
        self,
        current_user: StarletteUser,
    ):
        user_id = current_user.global_user_id
        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User Id is missing")

        try:
            cloud_connector_token: str = cloud_connector_token_context_var.get()
            token = self.glgo_authority.token(
                user_id=user_id,
                cloud_connector_token=cloud_connector_token,
            )
            request_log.info("Obtained Glgo token", source=__name__, user_id=user_id)
            return token
        except Exception as ex:
            log_exception(ex)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cannot obtain OIDC token",
            )

    @raise_aws_errors
    def _get_aws_credentials(
        self,
        current_user: StarletteUser,
        token: str,
        role_arn: str,
    ):
        if current_user.claims is not None:
            session_name = f"{current_user.claims.subject}"
        else:
            request_log.warn("No user claims found, setting session name to placeholder")
            session_name = "placeholder"

        return self.sts_client.assume_role_with_web_identity(
            RoleArn=role_arn,
            RoleSessionName=session_name,
            WebIdentityToken=token,
            DurationSeconds=43200,  # 12 Hour expiration
        )["Credentials"]


class AmazonQClient:
    def __init__(self, url: str, region: str, credentials: dict):
        self.client = q_boto3.client(
            "q",
            region_name=region,
            endpoint_url=url,
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

    @raise_aws_errors
    def create_or_update_auth_application(self, application_request):
        params = dict(
            clientId=application_request.client_id,
            clientSecret=application_request.client_secret,
            instanceUrl=application_request.instance_url,
            redirectUrl=application_request.redirect_url,
        )

        try:
            request_log.info("Creating OAuth Application Connection.")

            self._create_o_auth_app_connection(**params)
        except AWSException as ex:
            if ex.is_conflict():
                request_log.info("OAuth Application Exists. Updating OAuth Application Connection.")

                self._delete_o_auth_app_connection()
                self._create_o_auth_app_connection(**params)
            else:
                raise ex

    @raise_aws_errors
    def delete_o_auth_app_connection(self):
        try:
            request_log.info("Deleting OAuth Application Connection.")

            self._delete_o_auth_app_connection()
        except AWSException as ex:
            if ex.is_conflict() or ex.is_not_found():
                request_log.info("OAuth Application Does Not Exist.")
            else:
                raise ex

    @raise_aws_errors
    def send_event(self, event_request):
        event_id = event_request.event_id
        payload = event_request.payload.model_dump_json(exclude_none=True)

        try:
            self._send_event(event_id, payload)
        except ClientError as ex:
            if ex.__class__.__name__ == "AccessDeniedException":
                return self._retry_send_event(ex, event_request.code, payload, event_id)

            raise ex

    @raise_aws_errors
    def send_message(self, message: str, history: List[dict[str, str]]):
        return self.client.send_message(
            message=message,
            conversationId="conversation_id",
            history=history,
        )

    @raise_aws_errors
    def generate_code_recommendations(self, payload):
        return self.client.generate_code_recommendations(
            fileContext=payload["fileContext"],
            maxResults=payload["maxResults"],
        )

    @raise_aws_errors
    def verify_oauth_connection(self, health_request):
        try:
            return self._verify_oauth_connection()
        except ClientError as ex:
            if ex.response["Error"]["Code"] == "AccessDeniedException":
                return self._retry_verify_oauth_connection(ex, health_request.code)

            raise ex

    def _verify_oauth_connection(self):
        return self.client.verify_o_auth_app_connection()

    @raise_aws_errors
    def _create_o_auth_app_connection(self, **params):
        self.client.create_o_auth_app_connection(**params)

    @raise_aws_errors
    def _delete_o_auth_app_connection(self):
        self.client.delete_o_auth_app_connection()

    def _send_event(self, event_id: str, payload: dict):
        self.client.send_event(
            providerId="GITLAB",
            eventId=event_id,
            eventVersion="1.0",
            event=payload,
        )

    def _retry_send_event(self, error, code, payload, event_id):
        self._is_retry(error, code)

        return self._send_event(event_id, payload)

    def _retry_verify_oauth_connection(self, error, code):
        self._is_retry(error, code)

        return self._verify_oauth_connection()

    def _is_retry(self, error, code):
        match str(error.response.get("reason")):
            case AccessDeniedExceptionReason.GITLAB_EXPIRED_IDENTITY:
                self.client.create_auth_grant(code=code)
            case AccessDeniedExceptionReason.GITLAB_INVALID_IDENTITY:
                self.client.update_auth_grant(code=code)
            case _:
                return HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(error),
                )
