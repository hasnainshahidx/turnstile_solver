"""
clicker.py

Internal module to simulate human-like mouse movement and clicks on Cloudflare Turnstile using
either CDP (Chrome DevTools Protocol) or PyAutoGUI.

It is used to move the mouse to given coordinates (usually the checkbox)
and click on it in a human-like way.

Notes:
    - CDP clicks are generally less "trusted" from Cloudflare's perspective. For example,
      the resulting click event typically has `event.isTrusted === false`.
    - PyAutoGUI performs real OS-level mouse events, which are more likely to be considered
      genuine by Cloudflare. However, it requires a visible GUI (i.e. non-headless mode).
    - If your IP is clean and you're spoofing browser characteristics properly (e.g. using
      SeleniumBase or undetected-chromedriver), CDP clicks may still succeed in verification.
"""


import math
import random
import time
from typing import Literal, Tuple

import pyautogui


class TurnstileClicker:
    """
    Clicks on specific coordinates using either CDP or PyAutoGUI.
    Simulates a smooth human-like mouse path using a single Bézier curve.
    
    :param driver: Chrome WebDriver instance (Selenium, SeleniumBase, UC).
    :param method: Click method - 'cdp' (CDP events) or 'pyautogui' (screen control).

    Note:
    Use 'pyautogui' method only when running automation in a GUI environment (non-headless).
    In headless mode, only the 'cdp' method is supported.
    """

    # Shared script ID across all instances.
    # Ensures mousemove_listener script is injected only once.
    # Any instance can inject, reuse, or remove the script.
    SCRIPT_ID = None


    def __init__(self, driver, method: Literal["cdp", "pyautogui"]):
        self.driver = driver
        self.method = method

        if method == "cdp":
            if not TurnstileClicker.SCRIPT_ID:
                self._create_mousemove_listener()

        elif method == "pyautogui":
            pyautogui.PAUSE = 0.01

        else:
            raise ValueError("Invalid parameter: click_method must be either 'cdp' or 'pyautogui'.")

    def browser_to_screen_coords(self, element_x: int, element_y: int) -> Tuple[int, int]:
        """
        Convert browser-relative coordinates to screen coordinates.

        :param element_x: X relative to document
        :param element_y: Y relative to document
        :return: (screen_x, screen_y)
        """
        env = self.driver.execute_cdp_cmd("Runtime.evaluate", {
            "expression": """
                (function() {
                    return {
                        screenX: window.screenX,
                        screenY: window.screenY,
                        scrollX: window.scrollX,
                        scrollY: window.scrollY,
                        outerHeight: window.outerHeight,
                        innerHeight: window.innerHeight
                    };
                })();
            """,
            "returnByValue": True
        })["result"]["value"]

        chrome_offset_y = env["outerHeight"] - env["innerHeight"]

        screen_x = env["screenX"] + element_x - env["scrollX"]
        screen_y = env["screenY"] + chrome_offset_y + element_y - env["scrollY"]

        return int(screen_x), int(screen_y)

    def _create_mousemove_listener(self) -> None:
        """
        Inject JS to track the last known mouse position via `window._mousePos`.
        """

        js = """
            document.addEventListener('mousemove', e => {
                window._mousePos = { x: e.clientX, y: e.clientY };
            });
        """
        # Run it on future navigation
        res = self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument", {"source": js}
        )
        TurnstileClicker.SCRIPT_ID = res["identifier"]

        # Run it on current page also
        self.driver.execute_cdp_cmd("Runtime.evaluate", {"expression": js})

    def _get_mouse_pos(self) -> Tuple[int, int]:
        """
        Retrieve the last recorded mouse position from the page.
        If not defined, return a random point within the viewport.
        :return: (x, y)
        """
        js = """
            (function() {
                if (typeof window._mousePos === 'object' && window._mousePos !== null) {
                    return window._mousePos;
                } else {
                    return {
                        x: Math.floor(Math.random() * window.innerWidth),
                        y: Math.floor(Math.random() * window.innerHeight)
                    };
                }
            })()
        """
        res = self.driver.execute_cdp_cmd(
            "Runtime.evaluate", {"expression": js, "returnByValue": True},
        )["result"]["value"]
        return res["x"], res["y"]

    def _bezier_curve(self, p0: float, p1: float, p2: float, t: float) -> float:
        """
        Compute a point on a quadratic Bézier curve.

        :return: Interpolated point
        """
        return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t**2 * p2

    def _generate_human_like_path(
        self, start_x: int, start_y: int, end_x: int, end_y: int
    ) -> list:
        """
        Generate a smooth path from start to end using Bézier curve interpolation.

        :return: List of (x, y) points
        """
        dx, dy = end_x - start_x, end_y - start_y
        distance = math.hypot(dx, dy)
        steps = min(50, max(10, int(distance / 5)))
        ctrl_offset = distance * 0.25

        ctrl_x = (start_x + end_x) / 2 + random.uniform(-ctrl_offset, ctrl_offset)
        ctrl_y = (start_y + end_y) / 2 + random.uniform(-ctrl_offset, ctrl_offset)

        path = []
        for i in range(steps + 1):
            t = i / steps
            x = self._bezier_curve(start_x, ctrl_x, end_x, t) + random.uniform(
                -0.2, 0.2
            )
            y = self._bezier_curve(start_y, ctrl_y, end_y, t) + random.uniform(
                -0.2, 0.2
            )
            path.append((int(x), int(y)))

        return path

    def click(self, end_x: int, end_y: int) -> None:
        """
        Simulate a human-like mouse movement and click at the given coordinates.

        :param end_x: Target X-coordinate (relative to browser for CDP, document for PyAutoGUI)
        :param end_y: Target Y-coordinate
        """
        if self.method == "pyautogui":
            start = pyautogui.position()
            end = self.browser_to_screen_coords(end_x, end_y)
        else:
            start = self._get_mouse_pos()  # Start from the current sys-mouse position
            end = (end_x, end_y)

        path = self._generate_human_like_path(*start, *end)

        if self.method == "pyautogui":
            for x, y in path:
                pyautogui.moveTo(x, y)
            time.sleep(0.2)
            pyautogui.click(end)

        else:
            for x, y in path:
                self.driver.execute_cdp_cmd(
                    "Input.dispatchMouseEvent",
                    {"type": "mouseMoved", "x": x, "y": y, "buttons": 1},
                )
            time.sleep(0.3)

            for event_type in ["mousePressed", "mouseReleased"]:
                self.driver.execute_cdp_cmd(
                    "Input.dispatchMouseEvent",
                    {
                        "type": event_type,
                        "x": end_x,
                        "y": end_y,
                        "button": "left",
                        "clickCount": 1,
                    },
                )

    def remove_mousemove_listener(self) -> None:
        """
        Remove the injected JS mousemove listener from future pages.
        """
        if TurnstileClicker.SCRIPT_ID:
            self.driver.execute_cdp_cmd(
                "Page.removeScriptToEvaluateOnNewDocument",
                {"identifier": TurnstileClicker.SCRIPT_ID},
            )
            TurnstileClicker.SCRIPT_ID = None
