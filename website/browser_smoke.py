"""Optional browser checks against an already running local preview."""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def check_site(base_url: str, screenshot_dir: Path | None, channel: str | None) -> None:
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=channel)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="light")
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base_url, wait_until="networkidle")
        page.get_by_role("heading", name="Start building with AI agents.").wait_for()
        page.get_by_role("link", name="About AgentVerse", exact=True).click()
        assert page.get_by_role("heading", name="Who is AgentVerse for?").is_visible()
        assert page.locator("#why-agentverse").is_visible()
        assert page.get_by_role("link", name="About AgentVerse", exact=True).get_attribute("aria-current") == "page"
        page.get_by_role("link", name="AgentVerse home", exact=True).click()
        slide_count = page.locator(".hero-slide").count()
        assert slide_count > 0
        initial_height = page.locator(".hero-art").bounding_box()["height"]
        for index in range(slide_count):
            assert page.locator(".hero-slide:visible").count() == 1
            assert page.locator(f"#hero-slide-{index}").is_visible()
            assert page.locator(".hero-art").bounding_box()["height"] == initial_height
            page.get_by_role("button", name="Next scenario", exact=True).click()
        assert page.locator("#hero-slide-0").is_visible()
        page.get_by_role("button", name="Previous scenario", exact=True).click()
        assert page.locator(f"#hero-slide-{slide_count - 1}").is_visible()
        page.locator(".slide-dot").nth(1).click()
        assert page.locator("#hero-slide-1").is_visible()
        page.locator(".slide-dot").nth(1).press("ArrowLeft")
        assert page.locator("#hero-slide-0").is_visible()
        if screenshot_dir:
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot_dir / "agentverse-home-desktop.png"), full_page=True)
        page.get_by_role("link", name="Explore scenarios", exact=False).first.click()
        scenario_count = page.locator("[data-scenario]").count()
        scenario_paths = page.locator(".scenario-card h3 a").evaluate_all(
            "links => links.map(link => link.getAttribute('href'))"
        )
        page.get_by_role("searchbox").fill("maintenance")
        assert page.locator("[data-scenario]:visible").count() >= 1
        assert "q=maintenance" in page.url
        page.reload()
        assert page.get_by_role("searchbox").input_value() == "maintenance"
        page.get_by_label("Industry", exact=True).select_option("Manufacturing")
        assert page.locator('[data-scenario]:visible:not([data-industry="Manufacturing"])').count() == 0
        page.get_by_role("searchbox").fill("no-such-scenario-xyz")
        assert page.get_by_role("heading", name="No matching scenarios").is_visible()
        page.get_by_role("button", name="Clear filters").click()
        assert page.locator("[data-scenario]:visible").count() == scenario_count
        page.get_by_label("Technical level").select_option("beginner")
        assert page.locator("[data-scenario]:visible").count() == 1
        page.get_by_role("button", name="Clear filters").click()
        page.get_by_role("button", name="Switch to dark theme").click()
        assert page.locator("html").get_attribute("data-theme") == "dark"
        page.locator(".scenario-card h3 a").first.click()
        assert "scoutTheme=dark" in page.url
        assert page.locator("html").get_attribute("data-theme") == "dark"
        page.get_by_text("Explore the agents and participants", exact=True).click()
        assert page.locator(".agent-list").is_visible()
        assert page.get_by_role("link", name="Run this example").get_attribute("href").startswith(
            "https://github.com/Azure/AgentVerse/"
        )
        if screenshot_dir:
            page.screenshot(path=str(screenshot_dir / "agentverse-scenario-dark.png"), full_page=True)
        paths = [
            "index.html", "explore.html", "get-started.html", "building-blocks.html", "about.html",
            *scenario_paths,
        ]
        for width in (375, 768, 1440):
            page.set_viewport_size({"width": width, "height": 900})
            for path in paths:
                response = page.goto(base_url + path, wait_until="networkidle")
                assert response.status == 200, path
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth"
                ), f"Horizontal overflow at {width}px: {path}"
                assert page.locator("h1").count() == 1
        page.set_viewport_size({"width": 375, "height": 900})
        page.goto(base_url, wait_until="networkidle")
        if screenshot_dir:
            page.screenshot(path=str(screenshot_dir / "agentverse-home-mobile.png"), full_page=True)
        context.close()
        no_js = browser.new_context(java_script_enabled=False)
        page = no_js.new_page()
        page.goto(base_url, wait_until="networkidle")
        assert page.locator(".hero-slide").count() == slide_count
        assert page.locator(".hero-slide[inert]").count() == 0
        page.goto(base_url + "explore.html", wait_until="networkidle")
        assert page.locator("[data-scenario]:visible").count() == scenario_count
        page.locator(".scenario-card h3 a").first.click()
        assert page.get_by_role("heading", name="What\u2019s real. What\u2019s simulated.").is_visible()
        no_js.close()
        browser.close()
    assert not errors, errors
    print("Browser checks passed: carousel, filtering, reset, theme, navigation, no-JS, and responsive pages.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8098/")
    parser.add_argument("--screenshot-dir", type=Path)
    parser.add_argument("--channel", help="Use an installed browser, e.g. msedge.")
    args = parser.parse_args()
    check_site(args.base_url.rstrip("/") + "/", args.screenshot_dir, args.channel)
