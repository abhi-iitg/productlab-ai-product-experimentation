import { test as base, expect } from "@playwright/test";

/**
 * Chrome itself (not application code) logs this for every failed network
 * request — including the 4xx responses the app is deliberately testing it
 * handles gracefully (see 02-error-and-responsive.spec.ts). It is not a
 * signal of an application bug, so it is excluded from the check below.
 */
const BENIGN_CONSOLE_PATTERNS = [/^Failed to load resource:/];

/**
 * Extends the base Playwright test with an autouse fixture that fails the
 * test if the page logs any unexpected browser console error or uncaught
 * exception — one of the required E2E coverage checks (see the project's
 * Stage 9A brief: "fail on unexpected console errors").
 */
export const test = base.extend<{ failOnConsoleErrors: void }>({
  failOnConsoleErrors: [
    async ({ page }, use) => {
      const errors: string[] = [];

      page.on("console", (message) => {
        if (message.type() !== "error") return;
        const text = message.text();
        if (BENIGN_CONSOLE_PATTERNS.some((pattern) => pattern.test(text))) return;
        errors.push(text);
      });
      page.on("pageerror", (error) => {
        errors.push(error.message);
      });

      await use();

      expect(errors, `Unexpected browser console error(s):\n${errors.join("\n")}`).toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };
