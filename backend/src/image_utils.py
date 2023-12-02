from pathlib import Path
import re
import logging
from src.cloud_storage import CloudStorageAdapter

MAX_PIXEL_WIDTH = 1080
MAX_PIXEL_HEIGHT = 1350
MAX_PIXEL_HEIGHT_STORY = 1920
MAX_ASPECT_RATIO = 1.0
MIN_ASPECT_RATIO = 0.8
STORY_ASPECT_RATIO = 0.5625
EXTRA_BORDER = 0
BORDER_COLOR = "black"
VALID_IMAGE_EXTS = ["jpg", "jpeg", "png"]

logger = logging.getLogger("insta_poster_logger")

class PostManager:
    def __init__(self, bucket):
        self.bucket = bucket
        self.cs = CloudStorageAdapter(bucket)
        self.num_id_pattern = re.compile(r"^[0-9]+")
        self.lowest_id = None

    def get_image_file_ids(self, files: list[str]) -> list[int]:
        ids = []
        for file in files:
            for ext in VALID_IMAGE_EXTS:
                if file.endswith(ext):
                    num_id = self.num_id_pattern.search(file)
                    if num_id:
                        ids.append(int(num_id.group()))
        if ids:
            return ids
        else:
            return [0]

    def get_max_id(self, files: list[str]) -> str:
        return max(files)

    def get_images_with_same_id(self, id: int, files: list[str]) -> list[str]:
        selected_images = []
        for file in files:
            for ext in VALID_IMAGE_EXTS:
                if file.endswith(ext):
                    num_id = self.num_id_pattern.search(file)

                    if num_id:
                        num_id = int(num_id.group())
                        if num_id == id:
                            selected_images.append(file)
        return sorted(selected_images)

    def get_file_names(self, subdirectory: str) -> list[str]:
        file_paths = self.cs.list_blobs(prefix=subdirectory)
        file_names = []
        for file in file_paths:
            file_name = Path(file).name
            if file_name:
                file_names.append(file_name)
        return file_names

    def get_images_to_post(self, subdirectory=None) -> list[str]:
        """Select the most recent photo/s from the bucket"""
        images_to_post = []
        file_names = self.get_file_names(subdirectory)
        self.lowest_id = self.get_lowest_id(file_names)

        if self.lowest_id:
            images_to_post = self.get_images_with_same_id(self.lowest_id, file_names)
            logger.info(f"Images to post: {images_to_post}")
        else:
            logger.info("No images to post! Exiting...")

        return images_to_post

