from playwright.sync_api import Page, expect


SECTIONS = [
    ("Home", "/", "4S Ranch Men's Soccer League"),
    ("Teams", "/teams/", "Teams"),
    ("Schedule", "/schedule/", "Schedule"),
    ("Standings", "/standings/", "Standings"),
    ("Coaches", "/coaches/", "Coaches"),
    ("Admin", "/admin/", "Admin"),
    ("Rules", "/rules/", "Rules"),
]


def test_navigation_opens_each_section(page: Page) -> None:
    for label, path, heading in SECTIONS:
        page.goto(path)
        assert page.url.endswith(path)
        expect(page.get_by_role("heading", name=heading, exact=True)).to_be_visible()
        expect(page.get_by_role("navigation", name="Main navigation").get_by_role(
            "link", name=label
        )).to_have_attribute("aria-current", "page")


def test_navigation_fits_phone_viewport(page: Page) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto("/")

    nav = page.get_by_role("navigation", name="Main navigation")
    for label, _, _ in SECTIONS:
        expect(nav.get_by_role("link", name=label)).to_be_visible()

    # Content should fit the viewport without making the whole page scroll sideways.
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
