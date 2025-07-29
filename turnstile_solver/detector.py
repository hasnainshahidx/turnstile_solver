
"""
Internal module to detect the presence and type of Cloudflare Turnstile on a page.

This uses Chrome DevTools Protocol (CDP) to inspect the DOM and determine whether
an embedded widget or full challenge page is present.
"""

from typing import Optional
from selenium.common.exceptions import WebDriverException

class TurnstileDetector:
    """
    Detects whether a Turnstile widget is present on the page,
    and identifies its type: 'embedded' or 'challenge'.
    
    :param driver: Selenium WebDriver instance.
    """

    def __init__(self, driver):
        self.driver = driver

        self.node_id: Optional[int] = None
        self.type: Optional[str] = None

    def detect(self) -> Optional[dict]:
        """
        Detect and classify the Turnstile widget using CDP.

        :return: Dict like {"type": "embedded"} or {"type": "challenge"}, or None if not found.
        """
        try:
            root = self.driver.execute_cdp_cmd("DOM.getDocument", {"depth": 2})
            self.node_id = root["root"]["nodeId"]

            if self._has_embedded_widget():
                self.type = "embedded"
                return True

            if self._has_challenge_page():
                self.type = "challenge"
                return True

            return None

        # This is an expected error if the DOM changes (e.g., page reload or dynamic updates)
        # causing the previously obtained nodeId to become invalid.
        # Common CDP error: "No node with given id found"
        except WebDriverException:
            return None

    def _has_embedded_widget(self) -> bool:
        """
        Check if an embedded Turnstile widget exists via #cf-turnstile[data-sitekey].
        If found, scroll it into view (centered).
        
        :return: True if embedded widget found, else False.
        """
        result = self.driver.execute_cdp_cmd("DOM.querySelector", {
            "nodeId": self.node_id,
            "selector": ".cf-turnstile[data-sitekey]"
        })
        node_id = result.get("nodeId")
        if node_id:
            # Scroll into center of viewport for image
            self.driver.execute_cdp_cmd("DOM.scrollIntoViewIfNeeded", {
                "nodeId": node_id,
                "center": True
            })
            return True
        return False

    def _has_challenge_page(self) -> bool:
        """
        Check if the page is a Cloudflare challenge page via .footer-inner content.
        If found, scroll it into view (centered).

        :return: True if challenge page detected, else False.
        """
        footer = self.driver.execute_cdp_cmd("DOM.querySelector", {
            "nodeId": self.node_id,
            "selector": ".footer-inner"
        })

        footer_id = footer.get("nodeId")
        if not footer_id:
            return False

        # Get HTML content of the footer
        html = self.driver.execute_cdp_cmd("DOM.getOuterHTML", {
            "nodeId": footer_id
        }).get("outerHTML", "")

        return all(kw in html for kw in ["Ray ID", "Performance &", "security by", "Cloudflare"])
