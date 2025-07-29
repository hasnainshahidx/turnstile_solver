"""
# [turnstile_solver](https://github.com/hasnainshahidx/turnstile_solver)

**Click and solve Cloudflare Turnstile CAPTCHA — supports both headless and GUI modes.**

---

## 🔍 Features

- ✅ Supports **embedded** and **challenge page** Turnstile variants  
- ✅ Uses **Chrome DevTools Protocol** for DOM access and interaction  
- ✅ Human-like mouse movement using CDP or **PyAutoGUI**  
- ✅ Works in both **headless** and **visible** Chrome modes  
- ✅ Uses template-based **image matching** to locate the checkbox  
- ✅ Optional verification detection via **MutationObserver**

---

## ⚠️ Disclaimer
Note: This package is provided for educational and testing purposes only. Unauthorized use of this package to circumvent security measures is strictly prohibited. The author and contributors are not responsible for any misuse or consequences arising from the use of this package.

---

## 🚀 Usage Example

### ✅ Option 1: One-shot `solve()` function

Use this when you want a simple, one-time solve without worrying about managing state.

```python
from seleniumbase import Driver
from turnstile_solver import solve

driver = Driver(uc=True, headless=True)
driver.get("https://gitlab.com/users/sign_in")

success = solve(
    driver,
    detect_timeout=5,
    solve_timeout=30,
    interval=1,
    verify=True,
    click_method="cdp",  # or "pyautogui" for GUI mode only
    theme="auto",        # or "dark" / "light"
    grayscale=False,
    thresh=0.8,
    enable_logging=True
)

print("Solved:", success)
```

---

### ✅ Option 2: Reusable `Solver` class

Use this when solving Turnstile multiple times or when you want better performance and state control.

```python
from seleniumbase import Driver
from turnstile_solver import Solver

driver = Driver(uc=True, headless=True)
driver.get("https://gitlab.com/users/sign_in")

solver = Solver(
    driver,
    enable_logging=True,
    theme="auto",
    grayscale=False,
    thresh=0.8,
    click_method="cdp"
)

while True
  if solver.detect(timeout=5, interval=1):
      solved = solver.solve(timeout=30, interval=1, verify=True)
      print("Solved:", solved)
  else:
      print("Turnstile not detected")

solver.cleanup() # clean
```

---

### 🔍 Parameter Reference

| Parameter         | Type                                | Description |
|-------------------|-------------------------------------|-------------|
| `driver`          | `WebDriver`                         | Selenium driver (must be on a page with Turnstile). |
| `detect_timeout` / `solve_timeout` / `timeout` | `int`  | Max time (in seconds) to try detecting or solving. |
| `interval`        | `float`                             | Delay between retries (in seconds). Default: `1.0` |
| `verify`          | `bool`                              | If `True`, waits for verification. Otherwise just clicks. |
| `click_method`    | `"cdp"` \\| `"pyautogui"`            | `'cdp'` (works in headless) or `'pyautogui'` (GUI only). |
| `theme`           | `"auto"` \\| `"dark"` \\| `"light"`   | Match Turnstile theme for template matching. |
| `grayscale`       | `bool`                              | Use grayscale for matching (faster). |
| `thresh`          | `float`                             | Confidence threshold (0-1). Default: `0.8` |
| `enable_logging`  | `bool`                              | Print debug logs to console. |

---

### 🔁 Which One Should I Use?

| Scenario                             | Use               |
|--------------------------------------|-------------------|
| Quick one-time solve                 | `solve()`         |
| Multiple Turnstiles on same session  | `Solver` class    |
| Full control / performance tuning    | `Solver` class    |
| Script or CLI use                    | `solve()`         |

---

## Limitations

While this library is designed to work in both **headless** and **GUI** modes, it's important to understand the difference in trust levels between click methods:

- **CDP (Chrome DevTools Protocol)** clicks are faster and work in headless mode, but they are generally **less trusted** by Cloudflare.
- **PyAutoGUI** simulates **real human mouse movements**, making clicks more realistic and harder to detect, **but it only works in GUI mode**.

**However**, if you're using a **clean IP address** and a **well-spoofed browser environment**, CDP clicks may still be sufficient to pass the challenge with a low risk score.

For better results and stronger browser spoofing, consider using **[SeleniumBase](https://github.com/seleniumbase/SeleniumBase)** instead of undetectable-chromedriver. It offers more advanced stealth capabilities out of the box.

---

## 📜 License

MIT License

---

## 💬 Feedback or Contributions

Found a bug or have a suggestion?  
Feel free to [open an issue](https://github.com/hasnainshahidx/turnstile_solver/issues) or submit a pull request.  
Contributions are welcome and appreciated!

## 🙏 Note from the Author

This is my first open-source project, developed at the age of 18.  
As a young developer, I'm continuously learning—so there might be imperfections or areas for improvement.  
Any feedback, suggestions, or contributions are more than welcome to help make this project better!

## 📬 Contact & Support

For questions or support:

- 🌐 [Hasnain Shahid](https://hasnainshahidx.github.io/#contact)
- 📧 Email: hasnainshahid822@gmail.com
"""

from .solver import solve, Solver

__all__ = ["solve", "Solver"]
