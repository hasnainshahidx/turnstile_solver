"""
Internal module to monitor Cloudflare Turnstile verification state.

This class uses JavaScript MutationObserver to detect whether the Turnstile
has been solved, based on widget type: embedded checkbox or full-page challenge.
"""

from typing import Literal


class TurnstileObserver:
    """
    Monitors the Turnstile widget and detects when it has been verified.
    Works for both 'embedded' and 'challenge' types by injecting JS observers.
    
    :param driver: Selenium WebDriver instance.
    """

    # Shared script IDs across all instances.
    # Ensures each observer script is injected only once.
    # Any instance can inject, reuse, or remove the script.
    SCRIPT_IDS = {"challenge": None, "embedded": None}

    def __init__(self, driver):
        self.driver = driver
        self.detect_timeout = 5  # turnstile detection timeout set with the Solver.detect()

        # Tracks if Turnstile was previously detected but not yet verified
        self._was_detected = False

    def _observe_embedded(self, solve_timeout, detect_timeout) -> None:
        """
        Injects JS to observe attribute changes on the embedded Turnstile <input>.
        If any attribute changes, verification is considered successful.
        """
        js = f"""
            const widgetStartTime = Date.now();

            if (window.top === window.self) {{
                function observeWidget() {{
                    if ((Date.now() - widgetStartTime) / 1000 >= {detect_timeout}) {{
                        window._turnstileDetected = true;
                        return;
                    }};

                    const widget = document.querySelector(".cf-turnstile[data-sitekey]");
                    if (!widget) return setTimeout(observeWidget, 1000);

                    const input = widget.querySelector("input");
                    if (!input) return setTimeout(observeWidget, 1000);

                    window._turnstileDetected = true;

                    const observer = new MutationObserver(() => {{
                        sessionStorage.setItem("turnstile_verified", "true");
                        observer.disconnect();
                    }});
                    observer.observe(input, {{ attributes: true }});

                    setTimeout(() => observer.disconnect(), {solve_timeout} * 1000);
                }}
                observeWidget();
            }}
        """

        # Run it on future navigation
        res = self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": js})
        TurnstileObserver.SCRIPT_IDS["embedded"] = res["identifier"]

        # Run it on current page also
        self.driver.execute_cdp_cmd("Runtime.evaluate", {"expression": js})

    def _observe_challenge(self, solve_timeout, detect_timeout) -> None:
        """
        Injects JS to observe visibility of challenge success text.
        If it becomes visible, verification is considered successful.
        """
        js = f"""
            const challengeStartTime = Date.now();

            if (window.top === window.self) {{
                function observeChallenge() {{
                    if ((Date.now() - challengeStartTime) / 1000 >= {detect_timeout}) {{
                        window._turnstileDetected = false;
                        return;
                    }};

                    const target = document.querySelector("#challenge-success-text");
                    if (!target || !target.parentElement) return setTimeout(observeChallenge, 1000);

                    window._turnstileDetected = true;

                    function check() {{
                        if (target.getClientRects().length > 0) {{
                            sessionStorage.setItem("turnstile_verified", "true");
                            observer.disconnect();
                        }}
                    }}

                    const observer = new MutationObserver(check);
                    observer.observe(target.parentElement, {{
                        childList: true,
                        attributes: true,
                        characterData: true,
                        subtree: false
                    }});

                    check(); // Initial check
                    setTimeout(() => observer.disconnect(), {solve_timeout} * 1000);
                }}

                observeChallenge();
            }}
        """

        # Run it on future navigation
        res = self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": js})
        TurnstileObserver.SCRIPT_IDS["challenge"] = res["identifier"]

        # Run it on current page also
        self.driver.execute_cdp_cmd("Runtime.evaluate", {"expression": js})

    def start(self, cf_type: Literal["challenge", "embedded"], solve_timeout: int|float) -> None:
        """
        Start observing the page for Turnstile verification state.

        :param cf_type: Turnstile type - 'embedded' or 'challenge'.
        :param solve_timeout: Time to wait for solving the Turnstile (in seconds).
        """
        if not isinstance(solve_timeout, (int, float)) or solve_timeout <= 0:
            raise ValueError("'solve_timeout' must be a positive int or float")
        if not isinstance(self.detect_timeout, (int, float)) or self.detect_timeout <= 0:
            raise ValueError("'detect_timeout' must be a positive int or float")

        if cf_type == "embedded":
            if not TurnstileObserver.SCRIPT_IDS[cf_type]:
                self._observe_embedded(solve_timeout, self.detect_timeout)

        elif cf_type == "challenge":
            if not TurnstileObserver.SCRIPT_IDS[cf_type]:
                self._observe_challenge(solve_timeout, self.detect_timeout)

        else:
            raise ValueError("cf_type must be 'embedded' or 'challenge'.")

    def is_verified(self) -> bool:
        """
        Check if Turnstile has been verified. Uses a flag in sessionStorage.

        :return: True if verified, False otherwise.
        """
        result = self.driver.execute_cdp_cmd("Runtime.evaluate", {
            "expression": """
                (function() {
                    const val = sessionStorage.getItem("turnstile_verified");
                    if (val) sessionStorage.removeItem("turnstile_verified");
                    return {
                        verified: val,
                        detected: (typeof window._turnstileDetected !== "undefined") ? window._turnstileDetected : null
                    };
                })()
            """,
            "returnByValue": True
        })["result"]

        verified = result.get("value", {}).get("verified", False)
        detected = result.get("value", {}).get("detected", False)

        if verified == 'true':
            return True

        if detected is True:
            self._was_detected = True

        elif detected is False and self._was_detected:
            # If it was detected earlier but is now missing,
            # it's likely the domain changed or the observer was removed.
            # Treat as verified in that case.
            return True

        return False

    def remove(self) -> None:
        """
        Remove the injected JS observer from future navigation.
        """
        for key, script_id in TurnstileObserver.SCRIPT_IDS.items():
            if script_id:
                self.driver.execute_cdp_cmd("Page.removeScriptToEvaluateOnNewDocument", {
                    "identifier": script_id,
                })
                TurnstileObserver.SCRIPT_IDS[key] = None
