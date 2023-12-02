import json
import shutil
import os
import time
from pathlib import Path
import pytest
from src.utils.cloud_storage import CloudStorageAdapter
from src.utils.image_utils import PostManager, ImageChecker
from src.utils.instagram import InstagramAdapter

BUCKET_DIR = "tests/image_bucket"
UNPROCESSED_DIR = Path("tests/unprocessed")
BUCKET = "{{ PROJECT_ID }}-images"

gcs = CloudStorageAdapter(BUCKET)
ic = ImageChecker("post")


@pytest.fixture
def move_images_to_bucket():
    source_dir = "tests/images"
    # Get a list of files in the source directory
    file_list = os.listdir(source_dir)

    if os.path.exists(BUCKET_DIR):
        shutil.rmtree(BUCKET_DIR)

    os.mkdir(BUCKET_DIR)

    # Move each file from the source directory to the destination directory
    for file_name in file_list:
        # Create the full file paths
        source_file = os.path.join(source_dir, file_name)
        destination_file = os.path.join(BUCKET_DIR, file_name)

        # Move the file
        shutil.copy(source_file, destination_file)


def test_load_group_1(move_images_to_bucket):
    pm = PostManager()
    images_to_post = pm.get_images_to_post(BUCKET_DIR)
    expected = [
        "1A_DSF3888.jpg",
        "1B_DSF3894.jpg",
        "1C_DSF3905.jpg",
        "1D_DSF3911.jpg",
        "1E_DSF3917.jpg",
    ]
    assert images_to_post == expected


def upload_yaml_to_bucket(blob_path):
    local_yaml_path = Path.joinpath(Path.cwd(), "resources/1.yaml")
    gcs.upload_file_to_gcs(local_yaml_path, blob_path)


@pytest.fixture
def setup_yaml():
    blob_path = Path("test/yaml_test")
    upload_yaml_to_bucket(blob_path)
    time.sleep(1)
    yield
    gcs.delete_blob(Path.joinpath(blob_path, "1.yaml"))


def test_get_yaml_config(setup_yaml):
    yaml_path = ic.get_config_path("test/yaml_test", "1A_DOCK123.jpg")
    contents = gcs.download_yaml_blob(yaml_path)


TEST_DATA = (
    ([1.0, 1.0, 1.0, 1.0], 1.0),
    ([0.8, 0.8, 0.8, 0.8], 0.8),
    ([1.0, 1.0, 1.5, 1.0], 1.0),
    ([0.7, 1.0, 0.5, 1.0], 0.8),
)


@pytest.mark.parametrize("image_ars, exp", TEST_DATA)
def test_get_border_aspect_ratio(image_ars, exp):
    assert ImageChecker.get_border_aspect_ratio(image_ars) == exp


def test_get_hash_tags():
    max_hash_tags = 30
    hash_tags = ["rome", "travel", "nature", "photography", "fujifilm", "landscape"]
    hash_tags_str = InstagramAdapter.get_hash_tags(hash_tags)

    hash_tags_list = hash_tags_str.split()
    assert len(hash_tags_list) == max_hash_tags
    for hash_tag in hash_tags_list:
        assert hash_tag.startswith("#")


@pytest.fixture()
def highlight_pks():
    highlight_json_path = Path.joinpath(Path.cwd(), "resources/highlight_pks.json")
    with open(highlight_json_path, "r") as highlight_json:
        return json.load(highlight_json)


def test_get_latest_highlight(highlight_pks):
    insta = InstagramAdapter(BUCKET, login=False)
    latest_pk = insta.get_latest_highlight_pk()
    assert latest_pk == "65456323"
