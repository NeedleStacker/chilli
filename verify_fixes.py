from playwright.sync_api import sync_playwright, Page, expect
import time

def run_verification(page: Page):
    """
    Verifies all frontend fixes for the chili plant monitoring system.
    """
    print("Navigating to the application homepage...")
    page.goto("http://127.0.0.1:5000/")

    # 1. Verify logger status is correct on initial load
    print("Verifying initial logger status...")
    expect(page.locator("#loggerStatusTXT")).to_contain_text("Logger nije pokrenut")
    print("Initial logger status is correct.")

    # Start the logger to get some data for the other tests
    print("Starting the logger...")
    page.get_by_role("button", name="RUN").click()
    expect(page.locator("#loggerStatusTXT")).to_contain_text("RUNNING", timeout=10000)
    print("Logger started successfully.")

    expect(page.locator("#logsBody tr:first-child")).to_be_visible(timeout=15000)
    print("Log data is visible.")

    # 2. Verify delete confirmation dialog
    print("Verifying delete confirmation dialog...")
    page.once("dialog", lambda dialog: dialog.accept())

    first_log_id = page.locator("#logsBody tr:first-child td:first-child").inner_text()
    page.locator("#deleteIdsInput").fill(first_log_id)
    page.get_by_role("button", name="Obriši").click()

    expect(page.locator("#deleteStatus")).to_contain_text("Obrisano 1 zapisa.", timeout=5000)
    print("Delete confirmation and functionality verified.")

    # Take a screenshot of the main page
    print("Taking screenshot of main page...")
    page.screenshot(path="main_page.png")
    print("Main page screenshot saved.")

    # 3. Verify the "All Data" page functionality
    print("Navigating to 'All Data' page...")
    page.get_by_role("link", name="Svi podaci").click()
    expect(page).to_have_title("Chilli - Svi podaci")

    expect(page.locator("#logsBody tr")).to_have_count(lambda c: c > 0, timeout=10000)
    print("'All Data' page loaded.")

    # Test the 'soil_percent < 30' button
    print("Testing 'soil_percent < 30' filter button...")
    page.get_by_role("button", name="soil_percent < 30").click()
    expect(page.locator("#whereInput")).to_have_value("soil_percent < 30")
    page.get_by_role("button", name="Primijeni filter").click()
    time.sleep(2)

    # Test the 'timestamp' button
    print("Testing 'timestamp' filter button...")
    page.get_by_role("button", name="timestamp (zadnjih 30 dana)").click()
    expect(page.locator("#whereInput")).to_contain_text("timestamp BETWEEN")
    page.get_by_role("button", name="Primijeni filter").click()
    time.sleep(2)
    print("All 'All Data' page buttons verified.")

    # Final screenshot of the all_data page
    print("Taking screenshot of 'All Data' page...")
    page.screenshot(path="all_data_page.png")
    print("All Data page screenshot saved.")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        try:
            run_verification(page)
        finally:
            browser.close()

if __name__ == "__main__":
    main()