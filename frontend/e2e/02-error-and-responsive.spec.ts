import { expect, test } from "./support/fixtures";

test.describe("error and responsive behavior", () => {
  test("a not-found project shows a safe error state, not a raw API error", async ({ page }) => {
    await page.goto("/projects/999999999");

    await expect(page.getByRole("heading", { name: "Project not found" })).toBeVisible();
    await expect(
      page.getByText("It may have been deleted, or the link may be incorrect.")
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Back to projects" })).toBeVisible();

    // Never leak a raw HTTP status/detail payload onto the page.
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toContain("Internal server error");
    expect(bodyText).not.toContain("Traceback");
  });

  test("mobile viewport renders the mobile nav and a usable layout", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/projects");

    await expect(page.getByRole("heading", { name: "Projects", exact: true })).toBeVisible();

    const openMenu = page.getByRole("button", { name: "Open menu" });
    await expect(openMenu).toBeVisible();
    await openMenu.click();

    await expect(page.getByText("Menu")).toBeVisible();
    await expect(page.getByRole("button", { name: "Projects" }).last()).toBeVisible();
  });
});
