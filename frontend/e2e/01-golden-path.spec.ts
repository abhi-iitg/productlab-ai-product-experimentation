import { expect, test } from "./support/fixtures";
import {
  EVIDENCE_PRIMARY,
  EVIDENCE_PRIMARY_EDITED,
  EVIDENCE_SECONDARY,
  EXPERIMENT,
  HUMAN_FEEDBACK,
  HUMAN_FEEDBACK_EDITED_SUMMARY,
  PROJECT,
} from "./support/data";

/**
 * One continuous product-manager journey, run serially so each step reuses
 * the state the previous step created (project -> evidence -> personas ->
 * experiment -> execution -> analysis -> insights -> decision memo -> real
 * feedback) instead of repeating the full workflow from scratch in every
 * test. State is threaded between tests via the module-level `state`
 * object and `page.goto()`, since each test gets its own `page`.
 */
test.describe.serial("golden path: project brief through decision and real feedback", () => {
  const state: {
    projectId?: number;
    evidenceId?: number;
    personaNames?: string[];
    experimentId?: number;
  } = {};

  test("root redirects to /projects and shows the empty project state", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/projects$/);
    await expect(page.getByRole("heading", { name: "Projects", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "No projects yet" })).toBeVisible();
  });

  test("creates a project, enforcing required-field validation first", async ({ page }) => {
    await page.goto("/projects/new");

    await page.getByRole("button", { name: "Create project" }).click();
    await expect(page.getByText("Name is required.")).toBeVisible();
    await expect(page.getByText("Problem statement is required.")).toBeVisible();
    await expect(page.getByText("Target user is required.")).toBeVisible();
    await expect(page.getByText("Product hypothesis is required.")).toBeVisible();
    await expect(page.getByText("Success metric is required.")).toBeVisible();

    await page.locator("#name").fill(PROJECT.name);
    await page.locator("#problem_statement").fill(PROJECT.problemStatement);
    await page.locator("#target_user").fill(PROJECT.targetUser);
    await page.locator("#product_hypothesis").fill(PROJECT.productHypothesis);
    await page.locator("#success_metric").fill(PROJECT.successMetric);

    await page.getByRole("button", { name: "Create project" }).click();

    await expect(page).toHaveURL(/\/projects\/\d+$/);
    state.projectId = Number(page.url().match(/\/projects\/(\d+)$/)?.[1]);
    expect(state.projectId).toBeGreaterThan(0);
  });

  test("opens the project overview and edits the product brief", async ({ page }) => {
    await page.goto(`/projects/${state.projectId}`);
    await expect(page.getByText(PROJECT.problemStatement)).toBeVisible();

    await page.getByRole("button", { name: "Edit project" }).click();
    await expect(page.getByText("Update the product brief for " + PROJECT.name + ".")).toBeVisible();

    await page.locator("#problem_statement").fill(PROJECT.updatedProblemStatement);
    await page.getByRole("button", { name: "Save changes" }).click();

    await expect(page.getByText("Project updated.")).toBeVisible();
    await expect(page.getByText(PROJECT.updatedProblemStatement)).toBeVisible();
  });

  test("persona generation is disabled before any evidence exists", async ({ page }) => {
    await page.goto(`/projects/${state.projectId}/personas`);
    await expect(page.getByRole("heading", { name: "No personas yet" })).toBeVisible();
    await expect(
      page.getByText("Add evidence first, then generate personas grounded in that evidence.")
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Generate personas" })).toBeDisabled();
  });

  test("adds an evidence item and inspects its content and evidence ID", async ({ page }) => {
    await page.goto(`/projects/${state.projectId}/evidence`);
    await expect(page.getByRole("heading", { name: "No evidence yet" })).toBeVisible();

    await page.getByRole("button", { name: "Add your first evidence item" }).click();
    await expect(page.getByRole("heading", { name: "Add evidence" })).toBeVisible();

    await page.locator("#title").fill(EVIDENCE_PRIMARY.title);
    await page.locator("#content").fill(EVIDENCE_PRIMARY.content);
    await page.locator("#source_label").fill(EVIDENCE_PRIMARY.sourceLabel);
    await page.getByRole("button", { name: "Add evidence", exact: true }).click();

    await expect(page.getByText("Evidence added.")).toBeVisible();
    await expect(page.getByText(EVIDENCE_PRIMARY.title)).toBeVisible();

    await page.getByRole("button", { name: EVIDENCE_PRIMARY.title }).click();
    const detailDialog = page.getByRole("dialog");
    await expect(detailDialog.getByText(EVIDENCE_PRIMARY.content)).toBeVisible();
    const idText = await page.getByText(/^Evidence #\d+$/).textContent();
    state.evidenceId = Number(idText?.replace("Evidence #", ""));
    expect(state.evidenceId).toBeGreaterThan(0);
  });

  test("edits an evidence item", async ({ page }) => {
    await page.goto(`/projects/${state.projectId}/evidence`);

    await page.getByRole("button", { name: "Edit evidence" }).click();
    await expect(page.getByRole("heading", { name: "Edit evidence" })).toBeVisible();

    await page.locator("#title").fill(EVIDENCE_PRIMARY_EDITED.title);
    await page.locator("#content").fill(EVIDENCE_PRIMARY_EDITED.content);
    await page.getByRole("button", { name: "Save changes" }).click();

    await expect(page.getByText("Evidence updated.")).toBeVisible();
    await expect(page.getByText(EVIDENCE_PRIMARY_EDITED.title)).toBeVisible();
  });

  test("evidence delete requires confirmation before removing it", async ({ page }) => {
    await page.goto(`/projects/${state.projectId}/evidence`);

    // Create a throwaway second item so the primary evidence (used to
    // ground personas in later steps) is never the one deleted here.
    await page.getByRole("button", { name: "Add evidence", exact: true }).click();
    await page.locator("#title").fill(EVIDENCE_SECONDARY.title);
    await page.locator("#content").fill(EVIDENCE_SECONDARY.content);
    await page.getByRole("button", { name: "Add evidence", exact: true }).click();
    await expect(page.getByText("Evidence added.")).toBeVisible();

    const secondaryCard = page
      .locator('[data-slot="card"]')
      .filter({ hasText: EVIDENCE_SECONDARY.title });
    await secondaryCard.getByRole("button", { name: "Delete evidence" }).click();

    const confirmDialog = page.getByRole("alertdialog");
    await expect(confirmDialog.getByText("Delete this evidence item?")).toBeVisible();
    await expect(
      confirmDialog.getByText(`"${EVIDENCE_SECONDARY.title}" will be permanently removed`)
    ).toBeVisible();

    // Cancel first: the item must still be present.
    await confirmDialog.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByText(EVIDENCE_SECONDARY.title)).toBeVisible();

    await secondaryCard.getByRole("button", { name: "Delete evidence" }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Delete evidence", exact: true }).click();

    await expect(page.getByText("Evidence deleted.")).toBeVisible();
    await expect(page.getByText(EVIDENCE_SECONDARY.title)).not.toBeVisible();
  });

  test("generates evidence-grounded personas through the fake provider", async ({ page }) => {
    await page.goto(`/projects/${state.projectId}/personas`);

    await page.getByRole("button", { name: "Generate personas" }).first().click();
    const generateDialog = page.getByRole("dialog");
    await expect(generateDialog.getByRole("heading", { name: "Generate personas" })).toBeVisible();

    await page.locator("#persona_count").click();
    await page.getByRole("option", { name: "2", exact: true }).click();

    await generateDialog.getByRole("button", { name: "Generate personas" }).click();
    await expect(page.getByText(/^Generated 2 personas\.$/)).toBeVisible();

    const cardTitles = page.locator('[data-slot="card-title"]');
    await expect(cardTitles).toHaveCount(2);
    state.personaNames = await cardTitles.allTextContents();
    expect(state.personaNames).toHaveLength(2);

    // Evidence references are shown on every persona card.
    await expect(page.getByText("Evidence-backed claims").first()).toBeVisible();
    await expect(page.getByText(new RegExp(`Evidence #${state.evidenceId}:`)).first()).toBeVisible();

    // The fake provider always marks the first generated persona with an
    // unsupported assumption, visually distinguished (not color alone —
    // its own heading and section) from the evidence-backed claims above.
    await expect(page.getByText("Unsupported assumptions")).toBeVisible();
  });

  test("experiments list shows responsible AI language and enables experiment creation", async ({
    page,
  }) => {
    await page.goto(`/projects/${state.projectId}/experiments`);
    await expect(page.getByRole("heading", { name: "No experiments yet" })).toBeVisible();
    await expect(
      page.getByText(
        "Synthetic feedback supports hypothesis generation and experiment planning. It does not replace real-user research or predict market success."
      )
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "New experiment" })).toBeEnabled();
  });

  test("blocks experiment creation once planned runs exceed the 30-run cap", async ({ page }) => {
    // Generate 4 more personas (total 6) so 6 personas x 2 variants x 3
    // repeats = 36 > 30, without disturbing the original 2 personas used
    // by every later step.
    await page.goto(`/projects/${state.projectId}/personas`);
    await page.getByRole("button", { name: "Generate personas" }).click();
    const generateDialog = page.getByRole("dialog");
    await page.locator("#persona_count").click();
    await page.getByRole("option", { name: "4", exact: true }).click();
    await generateDialog.getByRole("button", { name: "Generate personas" }).click();
    await expect(page.getByText(/^Generated 4 personas\.$/)).toBeVisible();

    await page.goto(`/projects/${state.projectId}/experiments/new`);
    await page.locator("#name").fill(EXPERIMENT.name);
    await page.locator("#objective").fill(EXPERIMENT.objective);
    await page.locator("#hypothesis").fill(EXPERIMENT.hypothesis);
    await page.locator("#scenario").fill(EXPERIMENT.scenario);
    await page.getByRole("textbox", { name: "Evaluation criterion 1" }).fill(EXPERIMENT.evaluationCriteria[0]);

    // Select every persona checkbox (all 6) and repeat count 3.
    const checkboxes = page.locator('[data-slot="checkbox"]');
    const personaCheckboxCount = await checkboxes.count();
    for (let i = 0; i < personaCheckboxCount; i++) {
      await checkboxes.nth(i).click();
    }
    await page.locator("#repeat_count").click();
    await page.getByRole("option", { name: "3", exact: true }).click();

    const banner = page.getByRole("status");
    await expect(banner).toContainText("Maximum allowed is 30");
    await expect(banner).toContainText("Reduce personas or the repeat count to continue.");

    await page.locator("#variant_a_name").fill(EXPERIMENT.variantAName);
    await page.locator("#variant_a_description").fill(EXPERIMENT.variantADescription);
    await page.locator("#variant_b_name").fill(EXPERIMENT.variantBName);
    await page.locator("#variant_b_description").fill(EXPERIMENT.variantBDescription);

    await expect(page.getByRole("button", { name: "Create experiment" })).toBeDisabled();
  });

  test("creates a valid two-variant experiment with a live planned-run calculation", async ({
    page,
  }) => {
    await page.goto(`/projects/${state.projectId}/experiments/new`);
    await page.locator("#name").fill(EXPERIMENT.name);
    await page.locator("#objective").fill(EXPERIMENT.objective);
    await page.locator("#hypothesis").fill(EXPERIMENT.hypothesis);
    await page.locator("#scenario").fill(EXPERIMENT.scenario);
    await page.getByRole("textbox", { name: "Evaluation criterion 1" }).fill(EXPERIMENT.evaluationCriteria[0]);

    const banner = page.getByRole("status");
    await expect(banner).toContainText("Planned runs: 0");

    // Select only the original two personas by name.
    for (const name of state.personaNames ?? []) {
      await page.locator("label", { hasText: name }).first().getByRole("checkbox").click();
    }
    await expect(banner).toContainText("Planned runs: 4");
    await expect(banner).toContainText("(2 personas × 2 variants × 1 repeats)");

    await page.locator("#variant_a_name").fill(EXPERIMENT.variantAName);
    await page.locator("#variant_a_description").fill(EXPERIMENT.variantADescription);
    await page.locator("#variant_b_name").fill(EXPERIMENT.variantBName);
    await page.locator("#variant_b_description").fill(EXPERIMENT.variantBDescription);

    await page.getByRole("button", { name: "Create experiment" }).click();
    await expect(page.getByText("Experiment created.")).toBeVisible();
    await expect(page).toHaveURL(/\/experiments\/\d+$/);
    state.experimentId = Number(page.url().match(/\/experiments\/(\d+)$/)?.[1]);

    await expect(page.getByText(`Variant A: ${EXPERIMENT.variantAName}`)).toBeVisible();
    await expect(page.getByText(`Variant B: ${EXPERIMENT.variantBName}`)).toBeVisible();
    for (const name of state.personaNames ?? []) {
      await expect(page.getByText(name)).toBeVisible();
    }
  });

  test("execution confirmation communicates immutability and synthetic limitations, then executes", async ({
    page,
  }) => {
    await page.goto(`/projects/${state.projectId}/experiments/${state.experimentId}`);
    await page.getByRole("button", { name: "Execute experiment" }).click();

    await expect(page.getByText("Execute this experiment?")).toBeVisible();
    await expect(page.getByText("This will run 4 simulations across both variants.")).toBeVisible();
    await expect(page.getByText("Once started, the experiment's settings become immutable.")).toBeVisible();
    await expect(page.getByText("Synthetic results do not replace real-user testing.")).toBeVisible();

    await page.getByRole("button", { name: "Confirm and execute" }).click();
    await expect(page.getByText(/^Execution finished: \d+ completed, \d+ failed\.$/)).toBeVisible({
      timeout: 20_000,
    });
  });

  test("completed runs appear, and run detail exposes structured fields without raw prompts", async ({
    page,
  }) => {
    await page.goto(`/projects/${state.projectId}/experiments/${state.experimentId}`);
    await page.getByRole("tab", { name: "Runs" }).click();

    const rows = page.locator("table tbody tr");
    await expect(rows).toHaveCount(4);

    await rows.first().click();
    await expect(page.getByText("Response summary")).toBeVisible();
    await expect(page.getByText("Positive signals")).toBeVisible();
    await expect(page.getByText(/^Run #\d+$/)).toBeVisible();

    // Structured fields only — never a raw prompt or provider payload.
    const dialogText = await page.getByRole("dialog").innerText();
    expect(dialogText.toLowerCase()).not.toContain("system prompt");
    expect(dialogText.toLowerCase()).not.toContain("you are a");
  });

  test("analysis tab displays Variant A and Variant B metrics", async ({ page }) => {
    await page.goto(`/projects/${state.projectId}/experiments/${state.experimentId}`);
    await page.getByRole("tab", { name: "Analysis" }).click();

    await expect(page.getByText(`Variant A: ${EXPERIMENT.variantAName}`)).toBeVisible();
    await expect(page.getByText(`Variant B: ${EXPERIMENT.variantBName}`)).toBeVisible();
    await expect(page.getByText("Task completion rate").first()).toBeVisible();
  });

  test("generates insights through the fake provider with run references displayed", async ({
    page,
  }) => {
    await page.goto(`/projects/${state.projectId}/experiments/${state.experimentId}`);
    await page.getByRole("tab", { name: "Insights" }).click();

    await page.getByRole("button", { name: "Generate insights" }).click();
    await expect(page.getByText(/^Generated \d+ insights\.$/)).toBeVisible();
    await expect(page.getByText(/^Runs: #\d+/).first()).toBeVisible();
  });

  test("generates a decision memo with Proceed language and a real-user test plan", async ({
    page,
  }) => {
    await page.goto(`/projects/${state.projectId}/experiments/${state.experimentId}`);
    await page.getByRole("tab", { name: "Decision Memo" }).click();

    await page.getByRole("button", { name: "Generate decision memo" }).click();
    await expect(page.getByText("Decision memo generated.")).toBeVisible();

    await expect(page.getByText("Proceed to real-user validation")).toBeVisible();
    await expect(page.getByText("Recommended real-user test plan")).toBeVisible();
    await expect(page.getByText("Stopping rule")).toBeVisible();
  });

  test("adds real feedback with the privacy and qualitative-sample notices visible", async ({
    page,
  }) => {
    await page.goto(`/projects/${state.projectId}/experiments/${state.experimentId}`);
    await page.getByRole("tab", { name: "Real Feedback" }).click();

    await expect(page.getByRole("note").filter({ hasText: "Enter anonymized feedback only" })).toBeVisible();
    await expect(
      page.getByRole("note").filter({ hasText: "may represent a small qualitative sample" })
    ).toBeVisible();

    await page.getByRole("button", { name: "Add feedback" }).first().click();
    const feedbackDialog = page.getByRole("dialog");
    await page.locator("#participant_label").fill(HUMAN_FEEDBACK.participantLabel);
    await page.locator("#feedback_summary").fill(HUMAN_FEEDBACK.summary);

    await page.getByRole("radiogroup", { name: "Clarity (1-5)" }).getByRole("radio").nth(3).click();
    await page
      .getByRole("radiogroup", { name: "Perceived value (1-5)" })
      .getByRole("radio")
      .nth(3)
      .click();
    await page
      .getByRole("radiogroup", { name: "Adoption intent (1-5)" })
      .getByRole("radio")
      .nth(3)
      .click();

    await feedbackDialog.getByRole("button", { name: "Add", exact: true }).first().click();
    await page
      .getByRole("textbox", { name: "Positive signals 1" })
      .fill(HUMAN_FEEDBACK.positiveSignal);

    await feedbackDialog.getByRole("button", { name: "Add feedback", exact: true }).click();
    await expect(page.getByText("Feedback added.")).toBeVisible();
    await expect(page.getByText(HUMAN_FEEDBACK.participantLabel, { exact: true })).toBeVisible();
  });

  test("comparison view shows shared, human-only, and synthetic-only themes", async ({ page }) => {
    await page.goto(`/projects/${state.projectId}/experiments/${state.experimentId}`);
    await page.getByRole("tab", { name: "Real Feedback" }).click();

    await expect(page.getByText("Real vs. synthetic comparison")).toBeVisible();
    await expect(page.getByText("Shared themes")).toBeVisible();
    await expect(page.getByText("Synthetic-only themes")).toBeVisible();
    await expect(page.getByText("Real-only themes")).toBeVisible();
    await expect(
      page.getByRole("note").filter({ hasText: "The comparison highlights agreement and gaps" })
    ).toBeVisible();
  });

  test("edits and deletes real feedback", async ({ page }) => {
    await page.goto(`/projects/${state.projectId}/experiments/${state.experimentId}`);
    await page.getByRole("tab", { name: "Real Feedback" }).click();

    await page.getByRole("button", { name: "Edit feedback" }).click();
    await page.locator("#feedback_summary").fill(HUMAN_FEEDBACK_EDITED_SUMMARY);
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByText("Feedback updated.")).toBeVisible();
    await expect(page.getByText(HUMAN_FEEDBACK_EDITED_SUMMARY)).toBeVisible();

    await page.getByRole("button", { name: "Delete feedback" }).click();
    const confirmDialog = page.getByRole("alertdialog");
    await expect(confirmDialog.getByText("Delete this feedback?")).toBeVisible();
    await confirmDialog.getByRole("button", { name: "Delete feedback", exact: true }).click();
    await expect(page.getByText("Feedback deleted.")).toBeVisible();
    await expect(
      page.getByText(HUMAN_FEEDBACK.participantLabel, { exact: true })
    ).not.toBeVisible();
  });
});
