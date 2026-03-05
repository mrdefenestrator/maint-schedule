"""Navigation e2e tests: index page, vehicle tabs, back navigation."""
import pytest


@pytest.mark.e2e
def test_index_loads(page, flask_server):
    page.goto(flask_server)
    assert "Maintenance" in page.title()
    page.wait_for_selector("h2.font-semibold")
    assert page.locator("h2.font-semibold").count() >= 1


@pytest.mark.e2e
def test_vehicle_tabs(page, flask_server):
    page.goto(flask_server)
    page.locator("h2.font-semibold").first.click()
    page.wait_for_url("**/vehicle/test_vehicle")
    assert page.get_by_text("Status", exact=True).count() >= 1
    assert page.get_by_text("History", exact=True).count() >= 1
    assert page.get_by_text("Rules", exact=True).count() >= 1


@pytest.mark.e2e
def test_back_navigation(page, flask_server):
    page.goto(f"{flask_server}/vehicle/test_vehicle")
    page.locator('a[title="Back to dashboard"]').click()
    page.wait_for_url(flask_server + "/")
    assert page.locator("h2.font-semibold").count() >= 1
