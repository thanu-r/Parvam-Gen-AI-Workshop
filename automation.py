from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time

# Replace these with your Scholar student login credentials.
STUDENT_EMAIL="tanuthanisha@gmail.com"
STUDENT_PASSWORD = "Thanu@1234"

SCHOLAR_LOGIN_URL = "https://scholar.parvam.in/student/login"


def create_browser() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # Keep browser open by disabling automatic close on script finish
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def find_element(driver, locators, timeout=15, clickable=False):
    condition = EC.element_to_be_clickable if clickable else EC.presence_of_element_located
    for by, value in locators:
        try:
            return WebDriverWait(driver, timeout).until(
                condition((by, value))
            )
        except TimeoutException:
            continue
    raise NoSuchElementException(f"Unable to locate element from {locators}")


def login_scholar(driver):
    driver.get(SCHOLAR_LOGIN_URL)

    # Some pages use a register page with a login link or button.
    login_tab_locators = [
        (By.XPATH, "//a[contains(translate(., 'LOGIN', 'login'), 'login') and not(contains(., 'Register'))]"),
        (By.XPATH, "//button[contains(translate(., 'LOGIN', 'login'), 'login')]")
    ]

    for locator in login_tab_locators:
        try:
            login_tab = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(locator)
            )
            login_tab.click()
            break
        except TimeoutException:
            continue

    email_input = find_element(
        driver,
        [
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[name*='email']"),
            (By.XPATH, "//input[contains(translate(@placeholder, 'EMAIL', 'email'), 'email')]"),
            (By.XPATH, "//input[contains(translate(@id, 'EMAIL', 'email'), 'email')]")
        ],
    )
    password_input = find_element(
        driver,
        [
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.CSS_SELECTOR, "input[name*='password']"),
            (By.XPATH, "//input[contains(translate(@placeholder, 'PASSWORD', 'password'), 'password')]"),
            (By.XPATH, "//input[contains(translate(@id, 'PASSWORD', 'password'), 'password')]")
        ],
    )

    email_input.clear()
    email_input.send_keys(STUDENT_EMAIL)
    password_input.clear()
    password_input.send_keys(STUDENT_PASSWORD)

    submit_locators = [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "input[type='submit']"),
        (By.XPATH, "//button[contains(translate(., 'LOGIN', 'login'), 'login')]")
    ]
    submit_button = find_element(driver, submit_locators, clickable=True)
    submit_button.click()

    try:
        WebDriverWait(driver, 20).until(
            EC.url_contains("dashboard")
        )
        print("Login successful: dashboard detected.")
    except TimeoutException:
        print("Login may have failed or dashboard did not load within expected time.")


def keep_session_open():
    print("Browser opened and login attempted. Session remains active until you press Ctrl+C.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping automation and leaving browser open for manual inspection.")


if __name__ == "__main__":
    if not STUDENT_EMAIL or not STUDENT_PASSWORD:
        print("Please update STUDENT_EMAIL and STUDENT_PASSWORD before running this script.")
        exit(1)

    driver = create_browser()
    login_scholar(driver)
    keep_session_open()