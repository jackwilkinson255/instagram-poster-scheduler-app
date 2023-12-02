import io
import os
from pathlib import Path
from unittest.mock import patch
import pytest
from _pytest.fixtures import fixture
from src.utils.image_utils import ImageChecker

LOCAL_BUCKET_DIR = Path("./tests/images")
DOWNSAMPLED_DIR = LOCAL_BUCKET_DIR.joinpath("downsampled")
PROCESSED_DIR = LOCAL_BUCKET_DIR.joinpath("processed")
STORIES_DIR = LOCAL_BUCKET_DIR.joinpath("processed_stories")
UNPROCESSED_DIR = LOCAL_BUCKET_DIR.joinpath("unprocessed")
BUCKET = "{{ PROJECT_ID }}-images"
TEST_IMAGE = "tests/images/1A_DSF3888.jpg"
EXPECTED_DOWN_SAMPLED_WIDTH = 900
EXPECTED_DOWN_SAMPLED_HEIGHT = 1350
EXPECTED_BORDER_DIFF_WIDTH = 90
EXPECTED_BORDER_DIFF_HEIGHT = 0


@pytest.fixture
def read_in_memory_image():
    img_file = "tests/images/1A_DSF3888.jpg"
    with open(img_file, "rb") as file:
        image = file.read()
    return image
    # return io.BytesIO(image)


@pytest.fixture()
def ic():
    ic = ImageChecker()
    ic.set_image(TEST_IMAGE)
    return ic


def write_in_memory_image(image):
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")


def test_down_sample_image(ic):
    """Test down sampling to max 1080px width and 1350px height"""
    ic.down_sample_image()
    assert ic.image.width == EXPECTED_DOWN_SAMPLED_WIDTH
    assert ic.image.height == EXPECTED_DOWN_SAMPLED_HEIGHT


def test_add_border():
    ic = ImageChecker(upload_type="post")
    imgs_expected = {
        "1B_DSF3894.jpg": {0.8: [1020, 680, 30, 335], 1: [1020, 680, 30, 200]},
        "1A_DSF3888.jpg": {0.8: [860, 1290, 110, 30], 1: [680, 1020, 200, 30]},
        "1E_DSF3917.jpg": {0.8: [1020, 1020, 30, 165], 1: [1080, 1080, 0, 0]},
        "2A_DSF3965.jpg": {0.8: [1080, 1350, 0, 0], 1: [815, 1020, 132, 30]},
    }

    for img in imgs_expected.keys():
        for ar in imgs_expected[img].keys():
            img_path = f"tests/images/{img}"
            ic.set_image(img_path)
            expected = imgs_expected[img][ar]
            actual = ic.add_border(target_ar=ar)
            for act, exp in zip(actual, expected):
                assert act == exp
            # Uncomment to write resulting images
            # ic.image.save(Path.joinpath(PROCESSED_DIR, f"test_add_border_ar_{ar}_{img}"))


@fixture
def change_working_dir():
    os.chdir("..")


def test_add_captions(change_working_dir):
    ic = ImageChecker(upload_type="story")
    imgs_expected = {
        "1B_DSF3894.jpg": {0.8: [1020, 680, 30, 335], 1: [1020, 680, 30, 200]},
        "1A_DSF3888.jpg": {0.8: [860, 1290, 110, 30], 1: [680, 1020, 200, 30]},
        "1E_DSF3917.jpg": {0.8: [1020, 1020, 30, 165], 1: [1080, 1080, 0, 0]},
        "2A_DSF3965.jpg": {0.8: [1080, 1350, 0, 0], 1: [815, 1020, 132, 30]},
    }
    ar = ic.get_border_aspect_ratio(None)
    for img in imgs_expected.keys():
        img_path = Path.joinpath(UNPROCESSED_DIR, img)
        ic.set_image(img_path)
        # expected = imgs_expected[img][ar]
        actual = ic.add_border(target_ar=ar)
        font_path = str(Path.joinpath(Path.cwd(), "src/utils/fonts/Roboto-Medium.ttf"))
        ic.add_captions(
            location="Rome, Italy 📍", caption="Basking in the sun", font_path=font_path
        )
        # for act, exp in zip(actual, expected):
        #     assert act == exp
        # Uncomment to write resulting images
        ic.image.show()
        ic.image.save(Path.joinpath(STORIES_DIR, f"test_add_border_ar_{ar}_{img}"))

    assert True
