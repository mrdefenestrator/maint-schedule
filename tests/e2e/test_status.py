"""Status page e2e tests: filter chips, severe mode, theme switcher."""

import pytest


@pytest.mark.e2e
def test_status_filter_chips(page, flask_server):
    page.goto(f"{flask_server}/vehicle/test_vehicle")
    page.locator('button[data-status="overdue"]').click()
    page.wait_for_url("**/vehicle/test_vehicle?status=overdue")
    overdue_count = page.locator("#status-table").get_by_text("Overdue").count()
    ok_count = page.locator("#status-table").get_by_text("OK").count()
    assert overdue_count >= 1
    assert ok_count == 0


@pytest.mark.e2e
def test_severe_mode(page, flask_server):
    page.goto(f"{flask_server}/vehicle/test_vehicle")
    page.wait_for_selector('input[name="severe"]')
    with page.expect_navigation():
        page.check('input[name="severe"]')
    assert "severe=true" in page.url


@pytest.mark.e2e
def test_theme_switcher(page, flask_server):
    page.goto(flask_server)
    # Cycle theme 3 times: system → light → dark → system
    for _ in range(3):
        page.click("#theme-btn")
    # After 3 clicks back to system: icon-system should be visible
    system_icon = page.locator("#icon-system")
    assert not system_icon.evaluate("el => el.classList.contains('hidden')")
