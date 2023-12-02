import io
import os
from pathlib import Path

import yaml
from google.cloud import storage
import logging
import json
import tempfile
from PIL import Image

logger = logging.getLogger("insta_poster_logger")


class CloudStorageAdapter:
    def __init__(self, bucket_name: str) -> None:
        self.storage_client = storage.Client()
        self.bucket_name = bucket_name
        self.bucket = self.storage_client.bucket(bucket_name)

    def list_buckets(self) -> object:
        """Lists all buckets."""
        buckets = self.storage_client.list_buckets()
        bucket_names = []
        if buckets:
            for bucket in buckets:
                bucket_names.append(bucket.name)
            return bucket_names
        else:
            return []

    def delete_bucket(self, bucket_name):
        """Deletes a bucket. The bucket must be empty."""
        if bucket_name in self.list_buckets():
            bucket = self.storage_client.get_bucket(bucket_name)
            bucket.delete()
            logger.info(f"Bucket {bucket_name} deleted")
        else:
            logger.info(f"Bucket {bucket_name} does not exist")

    def check_bucket_exists(self, bucket_name) -> bool:
        if bucket_name in self.list_buckets():
            return True
        return False

    def create_bucket(self, bucket_name, storage_class="STANDARD", storage_loc="EUROPE-WEST2"):
        if bucket_name in self.list_buckets():
            logger.info(f"Bucket {bucket_name} already created")
        else:
            bucket = self.storage_client.bucket(bucket_name)
            bucket.storage_class = storage_class
            self.storage_client.create_bucket(bucket, location=storage_loc)
            logger.info(f"Bucket {bucket_name} created")

    def delete_blob(self, blob_name: Path):
        """Deletes a blob from the bucket."""
        blob = self.bucket.blob(str(blob_name))
        blob.delete()
        logger.info(f"Blob {blob_name} deleted.")

    def delete_all_blobs(self, prefix=None):
        blobs = self.list_blobs(prefix)
        if blobs:
            for blob in blobs:
                self.delete_blob(blob)
                msg = f"Blob '{blob}' in {self.bucket_name} bucket deleted."
                logger.info(msg), print(msg)
        else:
            logger.info(f"{self.bucket_name} bucket already empty.")

    def upload_file_to_gcs(self, file_path: Path, subdirectory: Path = None):
        if not Path.is_file(file_path):
            logger.error(f"File '{file_path}' does not exist locally!")
            raise FileExistsError

        file_name = file_path.name

        if subdirectory:
            gcs_path = Path.joinpath(subdirectory, file_name)
        else:
            gcs_path = file_name

        blob = self.bucket.blob(str(gcs_path))
        blob.upload_from_filename(file_path)
        logger.info(f"File '{gcs_path}' upload complete!")

    def move_temp_file_to_bucket(self, temp_blob_path):
        """
        Extract zip file stored in tmp directory, move to gcs bucket
        unzip required files to separate directory
        """
        logging.info("Moving temp file to gcs bucket")
        new_blob = self.bucket.blob(os.path.basename(temp_blob_path))
        new_blob.upload_from_filename(temp_blob_path)

    @staticmethod
    def extract_blob(bucket, file, zip_file):
        zip_blob = bucket.blob(file)
        zip_blob.upload_from_string(zip_file.read(file))
        logger.info(f"File '{file}' extracted")

    def list_blobs(self, prefix=None):
        """Lists all the blobs in the bucket."""
        blobs = self.storage_client.list_blobs(self.bucket_name, prefix=prefix)
        blob_names = []
        for blob in blobs:
            blob_names.append(blob.name)
        return blob_names

    def blob_exists(self, path: Path) -> bool:
        return str(path) in self.list_blobs()

    def download_blob_to_file(self, blob_name, path):
        blob = self.bucket.blob(f"{path}/{blob_name}")
        if not os.path.exists(path):
            os.makedirs(path)
        blob.download_to_filename(f"{path}/{blob_name}")

    def download_blob_to_bytes(self, file_name):
        """Download blob to bytes in an in-memory buffer"""
        blob = self.bucket.get_blob(str(file_name)).download_as_string()
        return io.BytesIO(blob)

    # def upload_image(self, image: Image, bucket: str, path: str):
    #     self.image.save(img_path)
    #     self.upload_image_from_string(img_path, new_img_path)
    #     logger.info(f"Uploaded image to {new_img_path}")
    #
    #     img_ext = img_path.name.split(".")[1]
    #     blob = self.bucket_object.blob(str(new_img_path))
    #     blob.upload_from_string(
    #         self.get_in_memory_image(), content_type=f"image/{img_ext}"
    #     )

    # def replace_image(self, image: Image, img_path, new_img_path):
    #     """Delete image from old path and upload new image to new path"""
    #     # self.delete_blob(self.bucket_name, img_path)
    #     self.image.save(img_path)
    #     self.upload_image_from_string(img_path, new_img_path)
    #     logger.info(f"Uploaded image to {new_img_path}")

    def upload_image_from_bytes(self, image: Image, destination_path: Path):
        img_ext = destination_path.name.split(".")[1]
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        blob = self.bucket.blob(str(destination_path))
        blob.upload_from_string(buffer.getvalue(), content_type=f"image/{img_ext}")

    def upload_from_string(self, file_path: Path, content: str):
        blob = self.bucket.blob(str(file_path))
        ext = file_path.suffix
        if ext == "json":
            content = json.dumps(content)
        blob.upload_from_string(data=content, content_type=f"application/{ext}")

    def upload_json(self, file_path: Path, content: dict):
        blob = self.bucket.blob(str(file_path))
        dumped = json.dumps(content, indent=4)
        blob.upload_from_string(data=dumped, content_type="application/json")


    def download_json_blob(self, blob_path: Path) -> dict:
        blob = self.bucket.blob(str(blob_path))
        blob_str = blob.download_as_string()
        while not isinstance(blob_str, dict):
            blob_str = json.loads(blob_str)
        return blob_str

    def download_yaml_blob(self, blob_path: Path) -> dict:
        blob = self.bucket.blob(str(blob_path))
        blob_str = blob.download_as_string()
        blob_str = yaml.safe_load(blob_str)
        return blob_str

    def move_blob_to_temp_dir(self, blob_path):
        file_name = blob_path.name
        temp_file_path = os.path.join(tempfile.gettempdir(), file_name)
        blob = self.bucket.blob(str(blob_path))
        blob.download_to_filename(temp_file_path)
        return temp_file_path




