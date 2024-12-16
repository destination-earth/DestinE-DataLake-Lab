import logging
import boto3
from botocore.client import Config
from botocore.exceptions import NoCredentialsError, ClientError
from pathlib import Path

from config import APP_LOGGER_NAME

# Get App Logger
logger = logging.getLogger(APP_LOGGER_NAME)

class S3Tools:

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        is_overwrite_s3: bool = True,
    ):

        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key

        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise ValueError("Bucket Credentials not set")

        self.is_overwrite_s3 = is_overwrite_s3

    def upload_file_to_s3(
        self, file_name: str, endpoint_url, bucket_name, object_name: str = None
    ):
        # If S3 object_name was not specified, use the file_name
        if object_name is None:
            object_name = file_name

        # Configure the S3 client
        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            config=Config(signature_version="s3v4"),
        )

        if self.is_overwrite_s3 == False:
            try:
                # Check if the object already exists in S3
                s3_client.head_object(Bucket=bucket_name, Key=object_name)
                logger.warning(f"File '{object_name}' already exists in bucket '{bucket_name}'.")
                return False
            except ClientError as e:
                # If a ClientError is thrown, check that it's because the object does not exist
                if e.response["Error"]["Code"] != "404":
                    logger.error(f"An error occurred: {e}")
                    return False

        # If we get here, the file does't exist and can be uploaded.
        try:
            # Upload the file to S3
            s3_client.upload_file(file_name, bucket_name, object_name)
            logger.info(
                f"File '{file_name}' uploaded to bucket '{bucket_name}' as '{object_name}'."
            )
        except FileNotFoundError:
            logger.error(f"The file '{file_name}' was not found.")
        except NoCredentialsError:
            logger.error("Credentials not available.")

        return True

    def upload_folder_to_s3(self, folder_path: str, endpoint_url, bucket_name):
        """
        Uploads a folder and its contents to an S3-compatible object storage.

        :param folder_path: Path to the local folder to upload.
        :param endpoint_url: The endpoint URL of the S3-compatible service.
        :param bucket_name: The name of the S3 bucket to upload to.
        """
        # Create an S3 client
        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            config=Config(signature_version="s3v4"),
        )

        # Get the list of all files in the folder
        folder_path: Path = Path(folder_path)
        for file_path in folder_path.rglob("*"):
            if file_path.is_file():
                # Generate the S3 object name
                # object_name = str(file_path.relative_to(folder_path))
                object_name_string: str = str(file_path)

                # Check if the object already exists in S3 if overwrite is not allowed
                if not self.is_overwrite_s3:
                    try:
                        s3_client.head_object(
                            Bucket=bucket_name, Key=object_name_string
                        )
                        logger.info(
                            f"File '{object_name_string}' already exists in bucket '{bucket_name}'. Skipping upload."
                        )
                        continue
                    except ClientError as e:
                        # If the object does not exist, continue to upload
                        if e.response["Error"]["Code"] != "404":
                            logger.error(f"An error occurred: {e}")
                            continue

                try:
                    # Upload the file to S3
                    s3_client.upload_file(
                        str(file_path), bucket_name, object_name_string
                    )
                    logger.info(
                        f"File '{file_path}' uploaded to bucket '{bucket_name}' as '{object_name_string}'."
                    )
                except FileNotFoundError:
                    logger.error(f"The file '{file_path}' was not found.")
                except NoCredentialsError:
                    logger.error("Credentials not available.")
                except ClientError as e:
                    logger.error(f"An error occurred: {e}")
