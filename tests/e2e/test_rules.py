"""Rules e2e tests: add, edit, delete rule."""

import pytest


VEHICLE_RULES_URL = "**/vehicle/test_vehicle/rules"


def _expand_first_rule(page):
    """Expand the first rule accordion."""
    page.locator("div.overflow-hidden .cursor-pointer").first.click()
    page.wait_for_timeout(300)


@pytest.mark.e2e
def test_add_rule(page, flask_server):
    page.goto(f"{flask_server}/vehicle/test_vehicle/rules")
    page.get_by_text("Add rule").click()
    page.wait_for_selector("#modal-content form")
    page.locator("#modal-content #item").fill("spark plugs")
    page.locator("#modal-content #verb").fill("replace")
    page.locator("#modal-content #interval_miles").fill("30000")
    page.locator("#modal-content #interval_months").fill("24")
    with page.expect_navigation():
        page.locator("#modal-content form").evaluate("form => form.requestSubmit()")
    assert "spark plugs" in page.content()


@pytest.mark.e2e
def test_edit_rule(page, flask_server):
    page.goto(f"{flask_server}/vehicle/test_vehicle/rules")
    _expand_first_rule(page)
    page.get_by_role("button", name="Edit rule").click()
    page.wait_for_selector("#modal-content form")
    page.locator("#modal-content #interval_miles").fill("4000")
    with page.expect_navigation():
        page.locator("#modal-content form").evaluate("form => form.requestSubmit()")
    assert "4,000" in page.content()


@pytest.mark.e2e
def test_delete_rule(page, flask_server):
    page.goto(f"{flask_server}/vehicle/test_vehicle/rules")
    initial_count = page.locator("div.overflow-hidden").count()
    _expand_first_rule(page)
    page.get_by_role("button", name="Delete rule").click()
    page.wait_for_selector("#modal-content form")
    with page.expect_navigation():
        page.locator("#modal-content form").evaluate("form => form.requestSubmit()")
    final_count = page.locator("div.overflow-hidden").count()
    assert final_count < initial_count
