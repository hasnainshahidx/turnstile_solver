"""
solver.py

Public API to solve Cloudflare Turnstile challenges using Selenium + CDP.

This module provides two interfaces:

1. Solver class:
   - Reusable object for detecting and solving Turnstile challenges.
   - Recommended if you need to solve multiple widgets or prefer performance and state reuse.

2. solve() function:
   - One-shot utility that handles full setup, detect, solve, and cleanup.
   - Best for simple, single-use cases or scripting.

Usage:
------
# One-shot solve (simplest)
from solver import solve
solve(driver, verify=True)

# Reusable solver instance (better for repeated solving)
from solver import Solver
solver = Solver(driver)
if solver.detect():
    solver.solve()
"""

import time
from typing import Literal

from turnstile_solver.clicker import TurnstileClicker
from turnstile_solver.detector import TurnstileDetector
from turnstile_solver.matcher import TurnstileMatcher
from turnstile_solver.observer import TurnstileObserver


def _validate_timeout_interval(timeout, interval):
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("timeout must be a positive int or float")
    if not isinstance(interval, (int, float)) or interval <= 0:
        raise ValueError("interval must be a positive int or float")
    if interval > timeout:
        raise ValueError("interval cannot be greater than timeout")


class Solver:
    """
    Reusable interface to detect and solve Cloudflare Turnstile challenges.

    :param driver: Selenium WebDriver instance.
    :param enable_logging: If True, logs progress messages to stdout.
    :param theme: Expected theme of the Turnstile widget; used to match template.
                Options: "auto", "dark", "light".
    :param grayscale: Use grayscale mode for matching (faster but less precise).
    :param thresh: Matching threshold (0 to 1) for image template detection.
    :param click_method: Method to use for clicking:
        - "cdp": Click using CDP (headless-compatible, default)
        - "pyautogui": Use OS-level mouse click (GUI only)

    :methods:
        detect(): Detect Cloudflare Turnstile widget.
        solve(): Attempt to solve the Turnstile widget.
    """

    def __init__(
        self,
        driver,
        enable_logging: bool = False,
        theme: Literal["auto", "dark", "light"] = "auto",
        grayscale: bool = False,
        thresh: float = 0.8,
        click_method: Literal["cdp", "pyautogui"] = "cdp",
    ):
        self.driver = driver
        self.enable_logging = enable_logging
        self.theme = theme
        self.grayscale = grayscale
        self.thresh = thresh
        self.click_method = click_method
        self._detected = None

        self.driver.execute_cdp_cmd("Page.enable", {})  # Enable CDP
        self._initialize_components()

    def _initialize_components(self):
        self._detector = TurnstileDetector(self.driver)
        self._observer = TurnstileObserver(self.driver)
        self._matcher = TurnstileMatcher(self.driver, self.theme, self.grayscale, self.thresh)
        self._clicker = TurnstileClicker(self.driver, method=self.click_method)

    def _log(self, message: str):
        if self.enable_logging:
            print(message)

    def cleanup(self):
        """Remove any listeners and observers"""
        if self._clicker:
            self._clicker.remove_mousemove_listener()
        if self._observer:
            self._observer.remove()

    def detect(self, timeout: int|float = 5, interval: int|float = 1) -> bool | str:
        """
        Detect Cloudflare Turnstile widget.

        :param timeout: Seconds to keep trying. Must be > 0.
        :param interval: Seconds between retries. Must be > 0 and <= timeout.
        :return: Type of Turnstile detected ("challenge" or "embedded"), or False if not found.
        """
        _validate_timeout_interval(timeout, interval)
        self._observer.detect_timeout = timeout  # Set detection timeout

        start_time = time.time()
        while time.time() - start_time <= timeout:
            if self._detector.detect():
                self._detected = self._detector.type
                self._log(f"Turnstile detected: type = {self._detected}")
                return self._detected
            time.sleep(interval)

        self._log("No Turnstile widget detected.")
        return False

    def solve(self, timeout: int|float = 30, interval: int|float = 1, verify: bool = False) -> bool:
        """
        Attempt to solve the Turnstile widget.

        :param timeout: Max seconds to retry clicking/verifying. Must be > 0.
        :param interval: Time between retries. Must be > 0 and <= timeout.
        :param verify: Whether to wait for Turnstile verification status.
        :return: True if solved, False if not.
        """
        _validate_timeout_interval(timeout, interval)
        if not isinstance(verify, bool):
            raise ValueError("'verify' must be a boolean")
        if not self._detected:
            raise RuntimeError(
                "Call detect() before solve() and ensure it returned True (widget detected)."
            )

        if verify:
            self._observer.start(cf_type=self._detected, solve_timeout=timeout)

        start_time = time.time()
        while time.time() - start_time <= timeout:

            if verify and self._observer.is_verified():
                self._log(f"Turnstile verified: type = {self._detected}")
                return True

            coords = self._matcher.match()
            if coords:
                x, y = coords[0] + 30, coords[1] + 25
                self._clicker.click(x, y)
                self._log(f"Clicked Turnstile using '{self.click_method}' at ({x}, {y})")
                if not verify:
                    return True

            time.sleep(interval)

        self._log(f"Turnstile not {'verified' if verify else 'clicked'} within timeout.")
        return False


def solve(
    driver,
    detect_timeout: int = 5,
    solve_timeout: int|float = 30,
    interval: int|float = 1,
    verify: bool = False,
    enable_logging: bool = False,
    theme: Literal["auto", "dark", "light"] = "auto",
    grayscale: bool = False,
    thresh: float = 0.8,
    click_method: Literal["cdp", "pyautogui"] = "cdp",
) -> bool | None:
    """
    One-shot helper to detect and solve a Cloudflare Turnstile widget.

    Use this function for quick, single-use scenarios. Internally creates a Solver instance,
    solves the challenge, and handles cleanup.

    :param driver: Selenium WebDriver instance.
    :param detect_timeout: Max seconds to try detecting the widget.
    :param solve_timeout: Max seconds to try solving it.
    :param interval: Delay between retries.
    :param verify: Whether to wait for Turnstile verification status.
    :param enable_logging: If True, logs progress messages to stdout.
    :param theme: Expected theme of the Turnstile widget; used to match template.
                  Options: "auto", "dark", "light".
    :param grayscale: Use grayscale mode for matching (faster but less precise).
    :param thresh: Matching threshold (0 to 1) for image template detection.
    :param click_method: Method to use for clicking:
                         - "cdp": Click using CDP (headless-compatible, default)
                         - "pyautogui": Use OS-level mouse click (GUI only)

    :return:
        - True: Successfully solved.
        - False: Detected but not solved in time.
        - None: No Turnstile widget detected.
    """
    solver = Solver(
        driver,
        enable_logging=enable_logging,
        theme=theme,
        grayscale=grayscale,
        thresh=thresh,
        click_method=click_method,
    )

    try:
        if not solver.detect(timeout=detect_timeout, interval=interval):
            return None

        return solver.solve(timeout=solve_timeout, interval=interval, verify=verify)
    finally:
        solver.cleanup()
