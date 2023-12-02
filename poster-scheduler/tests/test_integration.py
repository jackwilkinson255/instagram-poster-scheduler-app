import logging
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from src.utils.log import setup_custom_logger
from src.utils.cloud_storage import CloudStorageAdapter
from src.utils.instagram import InstagramAdapter, InstagramType
from src.utils.image_utils import PostManager
from src.main import InstaPosterApp
from src.utils.types import ImageDirectories

PROJECT = "{{ PROJECT_ID }}"
ACCOUNT = "test"
UPLOAD_TYPE = "post"
HIGHLIGHT = "new"
DOWN_SAMPLED_DIR = Path("tests/down_sampled")
PROCESSED_DIR = Path("tests/processed")
UNPROCESSED_DIR = (
    Path("tests/stories") if UPLOAD_TYPE == "story" else Path("tests/unprocessed")
)
BUCKET = f"{PROJECT}-images"

setup_custom_logger("testing_logger")
logger = logging.getLogger("testing_logger")

"""
Test cases
Post/Album:
- Post with two photos, json config file
- Post with two photos, no json config file
Story/Highlight:
- Story with two photos, added to highlight, json config file
- Story with two photos, added to highlight, no json config file
- Story with two photos, uploaded to latest highlight

Image Checker:
- Orientations,
- Type of post
"""

UNPROCESSED_LOCAL_DIR = "images/unprocessed"
SUB_DIR = "unprocessed"
print(f"Working dir: {Path.cwd()}")

IMAGES_TO_POST = [
    "1A_DSF3888.jpg",
    "1C_DSF3905.jpg",
    "6A_DSF4294.jpg",
    "6B_DSF3994.jpg",
]
JSON_FILES = [
    "1.json",
    "6.json",
]

dirs = ImageDirectories(
    unprocessed=UNPROCESSED_DIR,
    down_sampled=DOWN_SAMPLED_DIR,
    processed=PROCESSED_DIR,
)


@pytest.fixture
def upload_files_to_bucket(request):
    gcs = CloudStorageAdapter(BUCKET)
    file_names = request.param
    tests_dir = Path.joinpath(Path.cwd(), UNPROCESSED_LOCAL_DIR)
    file_paths = [Path.joinpath(tests_dir, file_name) for file_name in file_names]
    print(f"\nUploading: {file_names}")
    for file_path in file_paths:
        gcs.upload_file_to_gcs(file_path, UNPROCESSED_DIR)


def delete_files_in_bucket():
    gcs = CloudStorageAdapter(BUCKET)
    print("\nDeleting files in bucket...")
    for directory in [UNPROCESSED_DIR, DOWN_SAMPLED_DIR, PROCESSED_DIR]:
        gcs.delete_all_blobs(directory)


def delete_instagram_content():
    print("\nDeleting instagram content...")
    insta = InstagramAdapter(BUCKET, ACCOUNT, UPLOAD_TYPE, PROJECT, HIGHLIGHT)
    for insta_type in InstagramType:
        for media in insta.list_users_media(insta_type):
            insta.delete_users_media(media)


@pytest.fixture
def move_to_working_dir():
    os.chdir("..")


@pytest.fixture
def setup_post(move_to_working_dir):
    yield
    delete_files_in_bucket()
    # delete_instagram_content()


@pytest.mark.parametrize(
    "upload_files_to_bucket", [IMAGES_TO_POST, IMAGES_TO_POST + JSON_FILES]
)
def test_post_story_without_config(upload_files_to_bucket, setup_post):
    pm = PostManager(BUCKET)
    images_to_post = pm.get_images_to_post(UNPROCESSED_DIR)
    if not images_to_post:
        return
    app = InstaPosterApp(
        project=PROJECT,
        bucket=BUCKET,
        account="test",
        upload_type=UPLOAD_TYPE,
        highlight=None,
    )
    caption, location, hashtags = app.refine_images()
    app.post_images(caption, location, hashtags)


test_data = [
    (0, "new", 0),
    (1, "new", 1),
    (0, "latest", 2),
    (1, "latest", 3),
    (0, "123", 4),
    (1, "123", 5),
]

expected_insta_cl = {
    "insta.cl.highlight_create": (
        1,
        0,
        0,
        0,
        0,
        0,
    ),
    "insta.cl.photo_upload_to_story": (
        1,
        1,
        1,
        1,
        1,
        1,
    ),
    "insta.cl.highlight_add_stories": (
        0,
        1,
        1,
        1,
        1,
        1,
    ),
}

expected_insta = {
    "insta.save_highlight_pk": (
        1,
        0,
        0,
        0,
        0,
        0,
    ),
    "insta.get_latest_highlight_pk": (
        0,
        0,
        1,
        1,
        0,
        0,
    ),
    "insta.validate_highlight_pk": (
        0,
        0,
        0,
        0,
        1,
        1,
    ),
    "insta.get_story_hashtag_list": (
        1,
        0,
        1,
        0,
        1,
        0,
    ),
}


@patch("src.utils.instagram.get_current_service_account")
@patch("src.utils.instagram.CloudStorageAdapter")
@patch("src.utils.instagram.logging")
@pytest.mark.parametrize(
    "idx, highlight, test_idx",
    test_data,
)
def test_upload_picture_to_story(get_sa, gcs, logger, idx, highlight, test_idx):
    insta = InstagramAdapter(bucket=BUCKET, login=False)
    # Set up mock objects
    insta.cl = MagicMock()
    for func in expected_insta.keys():
        exec(f"{func} = MagicMock()")
    insta.highlight = MagicMock()
    insta.highlight.pk = 1234

    insta.upload_picture_to_story(
        path_=Path("test"),
        file_name="test_file",
        idx=idx,
        hashtags=None,
        highlight=highlight,
    )

    expected_insta_cl.update(expected_insta)

    for func in expected_insta_cl.keys():
        call_count = eval(f"{func}.call_count")
        expected = expected_insta_cl[func][test_idx]
        assert call_count == expected
