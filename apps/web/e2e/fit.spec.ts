import { expect, test } from "@playwright/test";
import { byTestId, shot, signIn } from "./helpers";

// Phase 4 check (prompts/04-fit.md). Needs Postgres with seeded data: `make db seed`.
test("Sorano: Deccan is a Strong fit at 90; Western Flow is Not a fit (represents Flowtek)", async ({ page }) => {
  await signIn(page, "viewer");
  await expect(page).toHaveURL(/\/sme$/);
  await page.getByRole("link", { name: /Sorano Instruments/ }).click();
  await page.getByRole("link", { name: "Matches" }).click();
  await expect(byTestId(page, "match-deccan-instrumentation").getByTestId("fit-category")).toHaveText("Strong fit");
  await expect(byTestId(page, "match-western-flow")).toContainText("represents Flowtek (Demo)");
  await shot(page, "04-1-sorano-matches");

  await page.getByRole("link", { name: "Deccan Instrumentation (Demo)" }).click();
  await expect(byTestId(page, "fit-score")).toHaveText("90");
  await expect(byTestId(page, "fit-category")).toHaveText("Strong fit");
  await expect(byTestId(page, "fit-card")).toContainText("Shortlist");
  await expect(page.getByText("TrustFit Score is not a credit rating or investment advice.").first()).toBeVisible();
  await shot(page, "04-2-sorano-deccan");

  await page.goto(page.url().replace("deccan-instrumentation", "western-flow"));
  await expect(byTestId(page, "fit-category")).toHaveText("Not a fit");
  await expect(byTestId(page, "fit-conflict")).toContainText("represents Flowtek (Demo)");
  await expect(byTestId(page, "fit-card")).toContainText("Skip, even if trusted");
  await shot(page, "04-3-sorano-western-flow");
});

test("the wizard saves a new SME brief", async ({ page }) => {
  await signIn(page, "viewer");
  await page.goto("/sme/new");
  await page.getByLabel("Company name").fill("Kaze Pumps (Demo)");
  await page.getByLabel("City (Japan)").fill("Nagoya");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await byTestId(page, "state-picker").getByRole("button", { name: "Maharashtra" }).click();
  await page.getByRole("button", { name: "Industrial b2b" }).click();
  await page.getByRole("button", { name: "Flow meters" }).click();
  await shot(page, "04-4-wizard-brief");
  await page.getByRole("button", { name: "Save brief" }).click();
  await expect(page).toHaveURL(/\/sme\/kaze-pumps-demo-/);
  await page.getByRole("link", { name: "Brief", exact: true }).click();
  await expect(page.getByRole("button", { name: "Maharashtra · primary" })).toBeVisible();
});
