import { expect, test } from "@playwright/test";
import { byTestId, shot, signIn } from "./helpers";

// Phase 5 check (prompts/05-gap-bridge.md). Needs Postgres with seeded data: `make db seed`.
test("Sorano: readiness gaps, matches with exclusions, and the 82% India entry team", async ({ page }) => {
  await signIn(page, "viewer");
  await page.getByRole("link", { name: /Sorano Instruments/ }).click();

  await expect(byTestId(page, "readiness-radar")).toBeVisible();
  for (const gap of ["R1", "R4", "R6"]) await expect(byTestId(page, `gap-${gap}`)).toContainText("critical");
  await expect(byTestId(page, "gap-R2")).toContainText("Covered by TrustFit");
  await expect(byTestId(page, "gap-R5")).toContainText("significant");
  await expect(byTestId(page, "gap-R3")).toContainText("minor");
  await shot(page, "05-1-sorano-readiness");

  await page.getByRole("link", { name: "Matches", exact: true }).click();
  const ranking = byTestId(page, "primary-ranking");
  await expect(ranking.locator("tbody tr").first()).toContainText("Deccan Instrumentation (Demo)");
  await expect(byTestId(page, "rank-deccan-instrumentation")).toContainText("72.9");
  await expect(byTestId(page, "excluded-western-flow")).toContainText("Competitor conflict: represents Flowtek (Demo)");
  await expect(byTestId(page, "excluded-konkan-trade")).toContainText("Knock-out");
  await expect(byTestId(page, "shortlist-R4")).toContainText("Certification support (BIS and others) 100%, verified");
  await shot(page, "05-2-sorano-matches");

  await page.getByRole("link", { name: "India entry team", exact: true }).click();
  await expect(byTestId(page, "team-coverage")).toContainText("82%");
  for (const id of ["deccan-instrumentation", "certipath", "nihon-india-bridge", "swift-cargo"])
    await expect(byTestId(page, `member-${id}`)).toBeVisible();
  await expect(byTestId(page, "uncovered")).toContainText("Localisation (minor, not covered)");
  await expect(byTestId(page, "coverage-matrix")).toBeVisible();
  await shot(page, "05-3-sorano-team");

  await byTestId(page, "member-certipath").getByRole("link").first().click();
  await expect(byTestId(page, "company-name")).toHaveText("CertiPath Compliance (Demo)");
  await expect(byTestId(page, "what-turns-it-green")).toBeVisible();
});

test("the wizard's readiness step gates the save until all 16 are answered", async ({ page }) => {
  await signIn(page, "viewer");
  await page.goto("/sme/new");
  await page.getByLabel("Company name").fill("Kaze Valves (Demo)");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await byTestId(page, "state-picker").getByRole("button", { name: "Gujarat" }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  const save = page.getByRole("button", { name: "Save brief" });
  await expect(save).toBeDisabled();
  for (const q of await page.locator("[data-testid^=question-]").all()) await q.getByRole("radio").nth(1).click();
  await expect(page.getByText("16 of 16 answered")).toBeVisible();
  await shot(page, "05-4-wizard-readiness");
  await save.click();
  await expect(page).toHaveURL(/\/sme\/kaze-valves-demo-/);
  await expect(byTestId(page, "readiness-radar")).toBeVisible();
  // every answer 1: readiness 25%; R1 severity (100 - 25) x distributor relevance 1.2 = 90
  await expect(byTestId(page, "gap-R1")).toContainText("25% ready");
  await expect(byTestId(page, "gap-R1")).toContainText("90 gap severity");
  await page.getByRole("link", { name: "Brief", exact: true }).click();
  await expect(page.getByRole("button", { name: "Gujarat · primary" })).toBeVisible();
});
