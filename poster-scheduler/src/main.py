from google.api_core.exceptions import NotFound
from src.utils.image_utils import PostManager, ImageChecker
from src.utils.instagram import InstagramAdapter
from src.utils.cloud_storage import CloudStorageAdapter
import os
import logging
from src.utils.log import setup_custom_logger
from src.utils.types import ImageDirectories
from pathlib import Path

PROJECT = os.getenv("GOOGLE_PROJECT_ID")
BUCKET = f"{PROJECT}-images"
ACCOUNT = os.getenv("ACCOUNT", "test")
UPLOAD_TYPE = os.getenv("UPLOAD_TYPE", "post")
HIGHLIGHT = os.getenv("HIGHLIGHT", "new") if UPLOAD_TYPE == "story" else None
DOWN_SAMPLED_DIR = Path(f"{ACCOUNT}/down_sampled")
PROCESSED_DIR = Path(f"{ACCOUNT}/processed")
UNPROCESSED_DIR = (
    Path(f"{ACCOUNT}/stories")
    if UPLOAD_TYPE == "story"
    else Path(f"{ACCOUNT}/unprocessed")
)
dirs = ImageDirectories(
    unprocessed=UNPROCESSED_DIR,
    down_sampled=DOWN_SAMPLED_DIR,
    processed=PROCESSED_DIR,
)

setup_custom_logger("insta_poster_logger")
logger = logging.getLogger("insta_poster_logger")


class InstaPosterApp:
    def __init__(self, project, bucket, account, upload_type, highlight):
        self.project = project
        self.bucket = bucket
        self.account = account
        self.dirs = dirs
        self.upload_type = upload_type
        self.highlight = highlight
        self.insta = None
        self.gcs = None
        self.pm = None
        self.images_to_post = None

    def post(self):
        logger.info(f"Starting {self.upload_type} upload...")
        self.gcs = CloudStorageAdapter(self.bucket)
        self.pm = PostManager(self.bucket)
        self.images_to_post = self.pm.get_images_to_post(
            subdirectory=self.dirs.unprocessed
        )
        if not self.images_to_post:
            return

        self.insta = InstagramAdapter(
            self.bucket, self.account, self.upload_type, self.project, self.highlight
        )

        caption, location, hashtags = self.refine_images()

        self.post_images(caption, location, hashtags)

        if ACCOUNT == "prod":
            self.delete_posted_images(str(self.pm.lowest_id))

        logger.info("Post complete!")

    def refine_images(self) -> tuple[str]:
        """
        - Loop through all images
        - Get each image's AR
        - If all constant and either 1:1 or 4:5, do nothing
        - Else, if all landscape, add border to make 1:1
        - Else, if portrait and squares
        """
        logger.info("Refining images...")
        aspect_ratios = []
        imgs_buffer = []
        ic = ImageChecker(self.upload_type)

        for img_name in self.images_to_post:
            unprocessed_path = self.dirs.unprocessed.joinpath(img_name)
            img_bytes = self.gcs.download_blob_to_bytes(unprocessed_path)
            ic.set_image(img_bytes)
            aspect_ratios.append(ic.get_aspect_ratio())
            imgs_buffer.append(img_bytes)

        # All ARs in album are needed before adding the borders
        target_ar = ic.get_border_aspect_ratio(aspect_ratios)
        logger.info(f"Overall aspect ratio for album is {target_ar}")

        yaml_path = ic.get_config_path(self.dirs.unprocessed, self.images_to_post[0])
        try:
            contents = self.gcs.download_yaml_blob(yaml_path)
            caption = contents["caption"]
            location = self.insta.get_location_obj(contents["location"])
            hashtags = self.insta.get_hash_tags(contents["hashtags"])
        except (NotFound, IndexError):
            caption = None
            location = None
            hashtags = self.insta.get_hash_tags([])

        for idx, (img_bytes, img_name) in enumerate(
            zip(imgs_buffer, self.images_to_post)
        ):
            ic.set_image(img_bytes)
            if ic.image_too_large():
                ic.down_sample_image()
            down_sampled_image_path = self.dirs.down_sampled.joinpath(img_name)
            self.gcs.upload_image_from_bytes(
                image=ic.image, destination_path=down_sampled_image_path
            )

            ic.add_border(target_ar)
            if idx == 0 and self.upload_type == "story" and location and caption:
                ic.add_captions(location=location.name, caption=caption)
            processed_image_path = self.dirs.processed.joinpath(img_name)
            self.gcs.upload_image_from_bytes(
                image=ic.image, destination_path=processed_image_path
            )

        return caption, location, hashtags

    def post_images(self, caption: str, location: str, hashtags: str):
        logger.info("Posting images...")
        self.copy_processed_images()

        if self.upload_type == "post":
            if len(self.images_to_post) > 1:
                self.insta.upload_album(
                    dirs.processed, self.images_to_post, caption, location
                )
            else:
                self.insta.upload_picture(
                    dirs.processed, self.images_to_post[0], caption, location
                )
            self.insta.add_comment(hashtags)
        elif self.upload_type == "story":
            self.insta.upload_pictures_to_story(
                dirs.processed,
                self.images_to_post,
                caption,
                location,
                hashtags,
                highlight=self.highlight,
            )

    def copy_processed_images(self):
        for image in self.images_to_post:
            self.gcs.download_blob_to_file(image, self.dirs.processed)

    def delete_posted_images(self, id: str):
        logger.info("Deleting images...")
        self.gcs.delete_all_blobs(prefix=str(dirs.unprocessed.joinpath(id)))


if __name__ == "__main__":
    insta_poster = InstaPosterApp(
        project=PROJECT,
        bucket=BUCKET,
        account=ACCOUNT,
        upload_type=UPLOAD_TYPE,
        highlight=HIGHLIGHT,
    )
    insta_poster.post()
