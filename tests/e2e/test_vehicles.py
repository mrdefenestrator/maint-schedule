"""Vehicle CRUD e2e tests: create, edit, delete."""

import pytest


@pytest.mark.e2e
def test_create_vehicle(page, flask_server):
    page.goto(flask_server)
    page.get_by_text("Add vehicle").click()
    page.wait_for_selector("#modal-content form")
    page.locator("#modal-content #slug").fill("test-new")
    page.locator("#modal-content #make").fill("Honda")
    page.locator("#modal-content #model").fill("Civic")
    page.locator("#modal-content #year").fill("2023")
    page.locator("#modal-content #purchase_date").fill("2023-01-01")
    page.locator("#modal-content #purchase_miles").fill("0")
    page.locator("#modal-content button[type='submit']").click()
    page.wait_for_url("**/vehicle/test-new")
    assert "Honda" in page.content()


@pytest.mark.e2e
def test_edit_vehicle(page, flask_server):
    # Navigate directly to the full edit page (no HTMX modal)
    page.goto(f"{flask_server}/vehicle/test_vehicle/edit")
    page.fill("#model", "Racer")
    page.locator("button[type='submit']").click()
    page.wait_for_url("**/vehicle/test_vehicle")
    page.wait_for_selector("h1")
    assert "Racer" in page.content()


@pytest.mark.e2e
def test_delete_vehicle(page, flask_server):
    page.goto(f"{flask_server}/vehicle/test_vehicle")
    page.locator('button[title="Delete vehicle"]').click()
    page.wait_for_selector("#modal-content form")
    page.locator("#modal-content button[type='submit']").click(force=True)
    page.wait_for_url(f"{flask_server}/")
    assert "/vehicle/" not in page.url
