from pathlib import Path
from PIL import Image, ImageOps
import os
import re
from io import BytesIO
import logging
from PIL import ImageFont
from pilmoji import Pilmoji
from src.utils.cloud_storage import CloudStorageAdapter

MAX_PIXEL_WIDTH = 1080
MAX_PIXEL_HEIGHT = 1350
MAX_PIXEL_HEIGHT_STORY = 1920
MAX_ASPECT_RATIO = 1.0
MIN_ASPECT_RATIO = 0.8
STORY_ASPECT_RATIO = 0.5625
EXTRA_BORDER = 0
BORDER_COLOR = "black"
VALID_IMAGE_EXTS = [".jpg", ".png"]

logger = logging.getLogger("insta_poster_logger")


class ImageChecker:
    def __init__(self, upload_type):
        self.border_height = None
        self.downsampled_width = None
        self.downsampled_height = None
        self.aspect_ratio = None
        self.height = None
        self.width = None
        self.image = None
        self.upload_type = upload_type
        self.max_pixel_height = (
            MAX_PIXEL_HEIGHT if self.upload_type == "post" else MAX_PIXEL_HEIGHT_STORY
        )

    def image_too_large(self) -> bool:
        return (self.width > MAX_PIXEL_WIDTH) or (self.height > self.max_pixel_height)

    def get_aspect_ratio(self) -> float:
        self.width, self.height = self.image.size
        return self.width / self.height

    def wrong_aspect_ratio(self) -> bool:
        self.aspect_ratio = self.width / self.height
        return (self.aspect_ratio > MAX_ASPECT_RATIO) or (
            self.aspect_ratio < MIN_ASPECT_RATIO
        )

    def get_correct_aspect_ratio(self) -> float:
        if self.aspect_ratio > MAX_ASPECT_RATIO:
            return MAX_ASPECT_RATIO
        else:
            return MIN_ASPECT_RATIO

    def crop_image(self, coords: tuple[int]):
        self.image = self.image.crop(coords)

    def down_sample_image(self):
        height = self.height
        width = self.width

        if height > self.max_pixel_height:
            width = int((width / height) * self.max_pixel_height)
            height = self.max_pixel_height

        if width > MAX_PIXEL_WIDTH:
            height = int((height / width) * MAX_PIXEL_WIDTH)
            width = MAX_PIXEL_WIDTH

        self.image = self.image.resize((width, height))

    def add_border(self, target_ar: int) -> list[int]:
        y = self.height
        x = self.width
        ar = self.get_aspect_ratio()
        x_prime = MAX_PIXEL_WIDTH
        y_prime = int(MAX_PIXEL_WIDTH / target_ar)
        # If we need to crop and add border
        if round(ar, 1) != target_ar:
            # If image is portrait

            # If image is landscape
            if self.upload_type == "story" or ar > 1:
                # if target_ar == 0.8:
                x_bar = EXTRA_BORDER
                x_hat = x_prime - 2 * x_bar
                y_hat = (y * x_hat) / x
                y_bar = int((y_prime - y_hat) / 2)
            else:
                y_bar = EXTRA_BORDER
                y_hat = y_prime - 2 * y_bar
                x_hat = (x * y_hat) / y
                x_bar = int((x_prime - x_hat) / 2)

        # Otherwise just down sample image
        else:
            x_hat = int(x_prime)
            x_bar = 0
            y_hat = int(y_prime)
            y_bar = 0

        self.downsampled_width = int(x_hat)
        self.downsampled_height = int(y_hat)
        self.border_height = y_bar
        self.image = self.image.resize(
            (self.downsampled_width, self.downsampled_height)
        )
        border = (x_bar, y_bar, x_bar, y_bar)
        self.image = ImageOps.expand(self.image, border=border, fill=BORDER_COLOR)

        return [int(x_hat), int(y_hat), int(x_bar), int(y_bar)]

    def get_border_aspect_ratio(self, image_ars: list[float]) -> float:
        """Get the border's aspect ratio"""
        if self.upload_type == "story":
            return STORY_ASPECT_RATIO
        ar_min = MAX_ASPECT_RATIO
        if isinstance(image_ars, float):
            image_ars = [image_ars]
        for ar in image_ars:
            if ar < ar_min:
                ar_min = MIN_ASPECT_RATIO
        return ar_min

    def set_image(self, image_bytes: BytesIO):
        self.image = Image.open(image_bytes)
        self.width, self.height = self.image.size

    def add_captions(
        self,
        location: str,
        caption: str,
        font_path: str = str(
            Path.joinpath(Path.cwd(), "src/utils/fonts/Roboto-Medium.ttf")
        ),
    ):
        font_size = 30
        _font = ImageFont.truetype(font_path, font_size)
        margin = 10
        text_x_pos = 10
        text_y_pos = self.downsampled_height + self.border_height + margin
        with Pilmoji(self.image) as pilmoji:
            pilmoji.text(
                xy=(text_x_pos, text_y_pos),
                text=location,
                align="left",
                font=_font,
                fill=(255, 255, 255),
            )
            pilmoji.text(
                xy=(text_x_pos, text_y_pos + font_size + margin),
                text=caption,
                align="left",
                font=_font,
                fill=(255, 255, 255),
            )

    @staticmethod
    def get_config_path(path, img_name):
        id_pattern = re.compile(r"^[0-9]+")
        _id = re.search(id_pattern, img_name).group()
        return os.path.join(path, f"{_id}.yaml")


class PostManager:
    def __init__(self, bucket):
        self.bucket = bucket
        self.cs = CloudStorageAdapter(bucket)
        self.num_id_pattern = re.compile(r"^[0-9]+")
        self.lowest_id = None

    def get_lowest_id(self, files: list[str]) -> int:
        ids = []
        for file in files:
            if file.endswith(".jpg"):
                num_id = self.num_id_pattern.search(file)
                if num_id:
                    ids.append(int(num_id.group()))

        if ids:
            return min(ids)
        else:
            return 0

    def get_images_with_same_id(self, id: int, files: list[str]) -> list[str]:
        selected_images = []
        for file in files:
            for img_ext in VALID_IMAGE_EXTS:
                if file.lower().endswith(img_ext):
                    num_id = self.num_id_pattern.search(file)
                    if num_id:
                        num_id = int(num_id.group())
                        if num_id == id:
                            selected_images.append(file)
        return selected_images

    def get_images_to_post(self, subdirectory=None) -> list[str]:
        """Select the most recent photo/s from the bucket"""
        file_paths = self.cs.list_blobs(prefix=subdirectory)
        file_names = []
        images_to_post = []
        for file in file_paths:
            file_name = Path(file).name
            if file_name:
                file_names.append(file_name)

        self.lowest_id = self.get_lowest_id(file_names)

        if self.lowest_id:
            images_to_post = self.get_images_with_same_id(self.lowest_id, file_names)
            logger.info(f"Images to post: {images_to_post}")
        else:
            logger.info("No images to post! Exiting...")

        return images_to_post
