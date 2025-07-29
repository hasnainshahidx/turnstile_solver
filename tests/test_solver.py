import unittest
from selenium import webdriver

from turnstile_solver import solve

class TestSolver(unittest.TestCase):

    def test_solve_returns_none_when_not_found(self):
        driver = webdriver.Chrome()
        driver.maximize_window()
        driver.set_window_position(0, 0)
        driver.get("https://2captcha.com/demo/cloudflare-turnstile-challenge")

        result = solve(
            driver,
            solve_timeout=30,
            interval=1,
            verify=True,
            enable_logging=True
        )
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
