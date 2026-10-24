import { expect, test } from "@playwright/test";
import { byTestId, shot, signIn } from "./helpers";

// Phase 4 check (prompts/04-fit.md). Needs Postgres with seeded data: `make db seed`.
test("Sorano: Deccan is a Strong fit at 90; Western Flow is Not a fit (represents Flowtek)", async ({ page }) => {
  await signIn(page, "viewer");
  await expect(page).toHaveURL(/\/sme$/);
  await page.getByRole("link", { name: /Sorano Instruments/ }).click();
  await page.getByRole("link", { name: "Matches" }).click();
  const deccan = byTestId(page, "rank-deccan-instrumentation");
  await expect(deccan.getByTestId("fit-category")).toHaveText("Strong fit");
  await expect(byTestId(page, "excluded-western-flow")).toContainText("represents Flowtek (Demo)");
  await shot(page, "04-1-sorano-matches");

  await deccan.getByRole("link", { name: "Deccan Instrumentation (Demo)" }).click();
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

// The wizard (brief + readiness) is covered end to end in bridge.spec.ts.
