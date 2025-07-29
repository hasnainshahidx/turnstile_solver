"""
matcher.py

Performs visual detection of Cloudflare Turnstile captchas using OpenCV template matching.
Supports both light and dark themes, with optional grayscale matching for performance.
"""

import base64
import os
from typing import Literal

import cv2
import numpy as np

# pylint:disable=E1101


def get_cdp_screenshot(driver) -> np.ndarray:
    """
    Capture a screenshot using Chrome DevTools Protocol, save it to disk,
    and return it as a NumPy array (BGR format).

    :param driver: Selenium WebDriver instance.
    :return: Screenshot as a NumPy array in BGR format.
    """
    result = driver.execute_cdp_cmd("Page.captureScreenshot", {
        "format": "png",
        "fromSurface": True
    })
    img_bytes = base64.b64decode(result["data"])

    return np.frombuffer(img_bytes, dtype=np.uint8)

class TurnstileMatcher:
    """
    Performs template matching using OpenCV to detect a Turnstile captcha
    in screenshots. Supports light, dark, or both themes with optional
    grayscale matching for speed.
    
    :param driver: Selenium WebDriver instance with CDP support.
    :param theme: Template theme to use. "auto" loads both.
    :param grayscale: Match using grayscale images for performance.
    :param thresh: Minimum similarity threshold (0.0 < thresh <= 1.0).
    """

    def __init__(
        self,
        driver,
        theme: Literal["light", "dark", "auto"] = "auto",
        grayscale: bool = False,
        thresh: float = 0.8
    ):
        self.driver = driver
        self.theme = theme
        self.grayscale = grayscale
        self.thresh = thresh

        # Convert relative path to absolute path
        base_dir = os.path.dirname(__file__)
        self.images = {
            "light": os.path.join(base_dir, "assets", "light_turnstile.png"),
            "dark": os.path.join(base_dir, "assets", "dark_turnstile.png"),
        }

        self._validate_params()
        self.templates = self._load_templates()

    def _validate_params(self):
        """
        Validate input parameters for theme, grayscale, and threshold.

        :raises ValueError: If any parameter is invalid.
        """
        if self.theme not in {"light", "dark", "auto"}:
            raise ValueError("Invalid parameter: 'theme' must be 'light', 'dark', or 'auto'.")

        if not isinstance(self.grayscale, bool):
            raise ValueError("Invalid parameter: 'grayscale' must be a boolean.")

        if not isinstance(self.thresh, float) or not 0.0 < self.thresh <= 1.0:
            raise ValueError(
                "Invalid parameter: 'thresh' must be between 0.0 and 1.0 (exclusive of 0.0)."
            )

    def _load_templates(self) -> list[np.ndarray]:
        """
        Load Turnstile template images from disk.

        :return: List of loaded template images.
        :raises FileNotFoundError: If any template image is missing.
        """
        paths = (
            list(self.images.values())
            if self.theme == "auto"
            else [self.images[self.theme]]
        )
        flag = cv2.IMREAD_GRAYSCALE if self.grayscale else cv2.IMREAD_COLOR

        templates = []
        for path in paths:
            img = cv2.imread(str(path), flag)
            if img is None:
                raise FileNotFoundError(f"Template image not found: {path}")
            templates.append(img)

        return templates

    def match(self) -> tuple[int, int] | None:
        """
        Match the given image array against templates and return match location.

        :param canvas_array: Encoded screenshot as 1D uint8 image array.
        :return: (x, y) top-left coordinates of best match if above threshold, else None.
        """
        flag = cv2.IMREAD_GRAYSCALE if self.grayscale else cv2.IMREAD_COLOR
        screenshot = get_cdp_screenshot(self.driver)
        canvas = cv2.imdecode(screenshot, flag)

        best_val = 0.0
        best_loc = None

        for template in self.templates:
            if (
                canvas.shape[0] < template.shape[0]
                or canvas.shape[1] < template.shape[1]
            ):
                continue

            result = cv2.matchTemplate(canvas, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > best_val and max_val >= self.thresh:
                best_val = max_val
                best_loc = max_loc

        return best_loc
