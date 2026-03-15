"""History e2e tests: log service, edit entry, delete entry."""

import pytest


VEHICLE_HISTORY_URL = "**/vehicle/test_vehicle/history"


def _expand_first_entry(page):
    """Expand the first history entry accordion."""
    page.locator("div.overflow-hidden .cursor-pointer").first.click()
    page.wait_for_timeout(300)


@pytest.mark.e2e
def test_sparkline_visible_on_history(page, flask_server):
    """Sparkline card appears on history tab when mileage data exists."""
    page.goto(f"{flask_server}/vehicle/test_vehicle/history")
    sparkline = page.locator("#sparkline-chart")
    assert sparkline.count() == 1
    assert "View full chart" in page.content()


@pytest.mark.e2e
def test_sparkline_links_to_chart(page, flask_server):
    """Clicking sparkline navigates to chart page."""
    page.goto(f"{flask_server}/vehicle/test_vehicle/history")
    page.locator("a:has(#sparkline-chart)").click()
    page.wait_for_url("**/chart")
    assert "/vehicle/test_vehicle/chart" in page.url
    assert page.locator("#mileage-chart").count() == 1


@pytest.mark.e2e
def test_chart_filter_input_exists(page, flask_server):
    """Chart page has a filter input and legend."""
    page.goto(f"{flask_server}/vehicle/test_vehicle/chart")
    assert page.locator("#rule-filter").count() == 1
    assert "Single service" in page.content()
    assert "Multiple services" in page.content()


@pytest.mark.e2e
def test_chart_back_to_history(page, flask_server):
    """Chart page has a back link to history."""
    page.goto(f"{flask_server}/vehicle/test_vehicle/chart")
    page.get_by_text("Back to history").click()
    page.wait_for_url("**/history")
    assert "/vehicle/test_vehicle/history" in page.url


@pytest.mark.e2e
def test_log_service(page, flask_server):
    page.goto(f"{flask_server}/vehicle/test_vehicle/history")
    page.get_by_text("Add entry").click()
    page.wait_for_selector("#modal-content form")
    page.select_option("#rule_key", value="engine oil and filter/replace")
    page.locator("#modal-content #mileage").fill("15500")
    page.locator("#modal-content #performed_by").fill("self")
    with page.expect_navigation():
        page.locator("#modal-content form").evaluate("form => form.requestSubmit()")
    # log_service redirects to status page (/vehicle/test_vehicle)
    assert "15,500" in page.content()


@pytest.mark.e2e
def test_edit_history_entry(page, flask_server):
    page.goto(f"{flask_server}/vehicle/test_vehicle/history")
    _expand_first_entry(page)
    page.get_by_role("button", name="Edit entry").click()
    page.wait_for_selector("#modal-content form")
    page.locator("#modal-content #notes").fill("Updated notes text")
    with page.expect_navigation():
        page.locator("#modal-content form").evaluate("form => form.requestSubmit()")
    assert "Updated notes text" in page.content()


@pytest.mark.e2e
def test_delete_history_entry(page, flask_server):
    page.goto(f"{flask_server}/vehicle/test_vehicle/history")
    initial_count = page.locator("div.overflow-hidden").count()
    _expand_first_entry(page)
    page.get_by_role("button", name="Delete entry").click()
    page.wait_for_selector("#modal-content form")
    with page.expect_navigation():
        page.locator("#modal-content form").evaluate("form => form.requestSubmit()")
    final_count = page.locator("div.overflow-hidden").count()
    assert final_count < initial_count
