import logging
import boto3
from botocore.client import Config
from botocore.exceptions import NoCredentialsError, ClientError
from pathlib import Path
from typing import Optional

from config import APP_LOGGER_NAME, IS_UPLOAD_S3

# Get App Logger
logger = logging.getLogger(APP_LOGGER_NAME)


class S3Tools:
    """
    Utility class for interacting with S3-compatible object storage.

    Handles uploading files and folders to S3 with support for checking
    existing files and skip-if-exists logic.
    """

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        is_overwrite_s3: bool = True,
    ) -> None:
        """
        Initialize S3Tools with AWS credentials.

        Args:
            aws_access_key_id: AWS access key ID for authentication
            aws_secret_access_key: AWS secret access key for authentication
            is_overwrite_s3: Whether to overwrite existing files (default: True)

        Raises:
            ValueError: If credentials are missing or invalid
        """
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key

        if not self.aws_access_key_id or not self.aws_secret_access_key:

            if IS_UPLOAD_S3:
                raise ValueError("Bucket Credentials not set")
            else:
                logger.warning(
                    "Bucket credentials not set, but IS_UPLOAD_S3 is False. This is ok. Skipping upload mode."
                )

        self.is_overwrite_s3 = is_overwrite_s3

    def upload_file_to_s3(
        self,
        file_name: str,
        endpoint_url: str,
        bucket_name: str,
        object_name: Optional[str] = None,
    ) -> bool:
        """
        Upload a single file to S3 storage.
        Note: This is not used in the current implementation, but kept for potential future use.

        example usage: path in bucket is same as local file path
        s3_tools.upload_file_to_s3(
            file_name="EO.XXX.YYY.ZZZ/metadata/collection.json",
            endpoint_url="https://s3.central.data.destination-earth.eu",
            bucket_name="test-bucket-1",
        )

        example usage: path in bucket is different from local file path
        s3_tools.upload_file_to_s3(
            file_name="EO.XXX.YYY.ZZZ/metadata/collection.json",
            endpoint_url="https://s3.central.data.destination-earth.eu",
            bucket_name="test-bucket-1",
            object_name="collection.json",
        )

        Args:
            file_name: Path to the local file to upload
            endpoint_url: S3 endpoint URL
            bucket_name: Name of the S3 bucket
            object_name: Name of the object in S3 (defaults to file_name)

        Returns:
            True if upload was successful, False otherwise
        """
        if file_name is None:
            logger.error("File name must be provided for upload.")
            return False

        if file_name.startswith("s3://"):
            logger.error("File name must be a local path, not an S3 URL.")
            return False

        if file_name.startswith("."):
            logger.error(
                "File name can be a relative path, but should not start with './' or '../'"
            )
            return False

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

        if not self.is_overwrite_s3:
            try:
                # Check if the object already exists in S3
                s3_client.head_object(Bucket=bucket_name, Key=object_name)
                logger.warning(
                    f"File '{object_name}' already exists in bucket '{bucket_name}'."
                )
                return False
            except ClientError as e:
                # If a ClientError is thrown, check that it's because the object does not exist
                if e.response["Error"]["Code"] != "404":
                    logger.error(f"An error occurred: {e}")
                    return False

        # If we get here, the file doesn't exist and can be uploaded.
        try:
            # Upload the file to S3
            s3_client.upload_file(file_name, bucket_name, object_name)
            logger.info(
                f"File '{file_name}' uploaded to bucket '{bucket_name}' as '{object_name}'."
            )
        except FileNotFoundError:
            logger.error(f"The file '{file_name}' was not found.")
            return False
        except NoCredentialsError:
            logger.error("Credentials not available.")
            return False

        return True

    def upload_folder_to_s3(
        self, folder_path: str, endpoint_url: str, bucket_name: str, target_path: Optional[str] = None
    ) -> None:
        """
        Upload a folder and its contents to S3-compatible object storage.

        Args:
            folder_path: Path to the local folder to upload
            endpoint_url: The endpoint URL of the S3-compatible service
            bucket_name: The name of the S3 bucket to upload to
            target_path: The target path in the S3 bucket (optional). 
            If not provided, files will be uploaded under the bucket root with the same path structure as the local folder.
            If provided, files will be uploaded under the target path with the same path structure as the local folder.
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
        folder_path_path: Path = Path(folder_path)
        for file_path in folder_path_path.rglob("*"):
            if file_path.is_file():
                # Generate the S3 object name
                if target_path:
                    object_name_string: str = str(
                        Path(target_path) / file_path.relative_to(folder_path_path)
                    )
                else:
                    object_name_string: str = str(
                        folder_path_path / file_path.relative_to(folder_path_path)
                    )
                object_name_string = Path(object_name_string).as_posix().lstrip("/")

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

    def s3_create_bucket(
        self,
        endpoint_url: str,
        bucket_name: str,
    ) -> bool:
        """
        Create a new bucket in the S3-compatible object storage.
        If the bucket already exists, it will not be created again and the function will return True.

        example usage:
        s3_tools.s3_create_bucket(
            endpoint_url="https://s3.central.data.destination-earth.eu",
            bucket_name="test-bucket-1",
        )
        
        Args:
            endpoint_url: The endpoint URL of the S3-compatible service
            bucket_name: The name of the bucket to create
        Returns:
            True if bucket was created successfully, False otherwise
        """

        if not bucket_name or not endpoint_url:
            logger.error("Bucket name and endpoint URL must be provided.")
            return False
        
        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            config=Config(signature_version="s3v4"),
        )

        try:
            # Check if bucket already exists
            s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket '{bucket_name}' already exists.")
            return True  # Bucket already exists

        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])

            # 404 = bucket does not exist → create it
            if error_code == 404:
                try:
                    s3_client.create_bucket(Bucket=bucket_name)
                    logger.info(f"Bucket '{bucket_name}' created successfully.")
                    return True
                except ClientError as e:
                    logger.error(f"An error occurred while creating the bucket: {e}")
                    return False

            # Any other error (403 forbidden, auth failure, etc.)
            logger.error(f"An error occurred while accessing the bucket: {e}")
            return False

    def move_bucket_contents_to_prefix(
        self,
        endpoint_url: str,
        bucket_name: str,
        target_prefix: str,
    ) -> None:
        """
        Move all objects in a bucket under a new top-level folder prefix.

        Each object is copied to '{target_prefix}/{original_key}' and then deleted
        from its original location. Objects that already start with '{target_prefix}/'
        are skipped to avoid double-moving.

        Note: S3 has no native move operation; this is implemented as copy + delete.

        Args:
            endpoint_url: The endpoint URL of the S3-compatible service
            bucket_name: The name of the S3 bucket
            target_prefix: The top-level folder name to move all objects into
        """
        target_prefix = target_prefix.strip("/")

        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            config=Config(signature_version="s3v4"),
        )

        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket_name)

        for page in pages:
            objects = page.get("Contents", [])
            for obj in objects:
                source_key: str = obj["Key"]

                # Skip objects already under the target prefix
                if source_key.startswith(f"{target_prefix}/"):
                    logger.warning(
                        f"Object '{source_key}' already under prefix '{target_prefix}/'. Skipping."
                    )
                    continue

                destination_key: str = f"{target_prefix}/{source_key}"
                copy_source = {"Bucket": bucket_name, "Key": source_key}

                try:
                    s3_client.copy_object(
                        CopySource=copy_source,
                        Bucket=bucket_name,
                        Key=destination_key,
                    )
                    logger.info(
                        f"Copied '{source_key}' -> '{destination_key}' in bucket '{bucket_name}'."
                    )
                except ClientError as e:
                    logger.error(
                        f"Failed to copy '{source_key}' to '{destination_key}': {e}"
                    )
                    continue

                try:
                    s3_client.delete_object(Bucket=bucket_name, Key=source_key)
                    logger.info(
                        f"Deleted original '{source_key}' from bucket '{bucket_name}'."
                    )
                except ClientError as e:
                    logger.error(
                        f"Failed to delete original '{source_key}' after copy: {e}"
                    )
