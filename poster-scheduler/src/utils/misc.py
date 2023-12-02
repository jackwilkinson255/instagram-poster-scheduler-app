import logging
from google.cloud import secretmanager

logger = logging.getLogger("insta_poster_logger")


def get_credentials_secret(
    test_acct: bool = True, project_id: str = None
) -> tuple[str]:
    client = secretmanager.SecretManagerServiceClient()
    account = "" if test_acct else ""
    creds = []
    logger.info("Accessing credentials from secret manager...")
    for secret_id in [account, "password"]:
        # Build the resource name of the secret version.
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        # Access the secret version.
        response = client.access_secret_version(name=name)
        # Return the decoded payload.
        creds.append(response.payload.data.decode("UTF-8"))
    logger.info("Found credentials!")

    return creds[0], creds[1]


def get_current_service_account():
    import google.auth
    credentials, project_id = google.auth.default()
    if hasattr(credentials, "service_account_email"):
        logger.info(f"Service account in use: {credentials.service_account_email}")
    else:
        logger.info("Not using service account.")
