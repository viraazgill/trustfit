import path from "node:path";
import { expect, type Page, test } from "@playwright/test";
import { byTestId, signIn } from "./helpers";

// The whole live demo, click by click (docs/06-demo-script.md), with a screenshot of every step in
// artifacts/demo/. Needs Postgres with freshly seeded data: `make db seed`.
const DEMO = path.resolve(__dirname, "../../../artifacts/demo");
const step = (page: Page, name: string) => page.screenshot({ path: path.join(DEMO, `${name}.png`), fullPage: true });

test("the five-minute demo", async ({ browser }) => {
  test.setTimeout(180_000);

  // Before the demo: the landing page, then an analyst tab and an SME tab.
  const analyst = await (await browser.newContext()).newPage();
  await analyst.goto("/");
  await expect(analyst.getByRole("heading", { name: "Trust decides eligibility. Fit justifies the visit." })).toBeVisible();
  await step(analyst, "00-landing");
  await signIn(analyst, "analyst");

  // Part 1: Trust on a real company
  // 1. Subros as a supplier
  await analyst.goto("/companies/subros?role=supplier");
  await expect(byTestId(analyst, "score")).toHaveText("87");
  await step(analyst, "01-subros-supplier");
  // 2. 87, Very strong, but Amber
  await expect(byTestId(analyst, "band")).toHaveText("Very strong");
  await expect(byTestId(analyst, "verdict").first()).toHaveText("Amber");
  // 3. the reasons, and the pale bars: Legal, Governance, Reputation and Payment conduct under half verified
  await expect(byTestId(analyst, "reasons")).toContainText("Integrity is 32.5% verified, under the 50% minimum");
  await expect(byTestId(analyst, "reasons")).toContainText("Verification gates pending");
  for (const cat of ["A", "C", "D", "E"]) await expect(byTestId(analyst, `category-${cat}`)).toContainText("under half verified");
  await byTestId(analyst, "reasons").scrollIntoViewIfNeeded();
  await step(analyst, "03-reasons-and-pale-bars");
  // 4. outlook Watch
  await expect(byTestId(analyst, "outlook")).toContainText("Watch");
  // 5. what-if: integrity checks clean -> 82.5, 90, Green
  await analyst.getByRole("button", { name: "What-if" }).click();
  await analyst.getByRole("button", { name: "Integrity checks clean" }).click();
  await expect(analyst.getByRole("dialog").getByText("82.5 verified")).toBeVisible();
  await step(analyst, "05a-what-if-drawer");
  await analyst.keyboard.press("Escape");
  await expect(analyst.getByRole("dialog")).toBeHidden();
  await expect(byTestId(analyst, "score")).toHaveText("90");
  await expect(byTestId(analyst, "verdict").first()).toHaveText("Green");
  await expect(byTestId(analyst, "confidence")).toContainText("82.5");
  await step(analyst, "05b-what-if-green");
  // 6. JV partner -> 86
  await analyst.getByRole("button", { name: "Exit what-if" }).click();
  await analyst.getByRole("tab", { name: "JV partner" }).click();
  await expect(byTestId(analyst, "score")).toHaveText("86");
  await step(analyst, "06-jv-partner");

  // Part 2: Fit and the Gap Bridge for an SME
  const sme = await (await browser.newContext()).newPage();
  await signIn(sme, "viewer");
  // 7. Sorano's readiness: critical R1, R4, R6; R2 covered by TrustFit
  await sme.goto("/sme/sorano");
  for (const gap of ["R1", "R4", "R6"]) await expect(byTestId(sme, `gap-${gap}`)).toContainText(/critical/i);
  await expect(byTestId(sme, "gap-R2")).toContainText("Covered by TrustFit");
  await step(sme, "07-sorano-readiness");
  // 8. matches: Deccan Strong fit 90 and Green; Western Flow trusted but Not a fit; Konkan knocked out
  await sme.getByRole("link", { name: "Matches", exact: true }).click();
  const deccan = byTestId(sme, "rank-deccan-instrumentation");
  await expect(deccan).toContainText("90");
  await expect(deccan.getByTestId("fit-category")).toHaveText("Strong fit");
  await expect(byTestId(sme, "excluded-western-flow")).toContainText("Competitor conflict: represents Flowtek (Demo)");
  await expect(byTestId(sme, "excluded-western-flow")).toContainText("Trust 92");
  await expect(byTestId(sme, "excluded-konkan-trade")).toContainText("Knock-out");
  await step(sme, "08a-matches");
  await deccan.getByRole("link", { name: "Deccan Instrumentation (Demo)" }).click();
  await expect(byTestId(sme, "fit-score")).toHaveText("90");
  await expect(byTestId(sme, "verdict").first()).toHaveText("Green");
  await step(sme, "08b-deccan-strong-fit");
  await sme.goto("/sme/sorano/company/western-flow");
  await expect(byTestId(sme, "fit-category")).toHaveText("Not a fit");
  await expect(byTestId(sme, "score")).toHaveText("92");
  await step(sme, "08c-western-flow-trusted-not-a-fit");
  // 9. the India entry team: Deccan + CertiPath + Nihon-India Bridge + Swift Cargo, 82%; Localisation open
  await sme.goto("/sme/sorano/team");
  await expect(byTestId(sme, "team-coverage")).toContainText("82%");
  for (const id of ["deccan-instrumentation", "certipath", "nihon-india-bridge", "swift-cargo"])
    await expect(byTestId(sme, `member-${id}`)).toBeVisible();
  await expect(byTestId(sme, "uncovered")).toContainText("Localisation (minor, not covered)");
  await step(sme, "09-india-entry-team");
  // 10. close on the one-page report (and the Japanese view)
  await sme.goto("/sme/sorano/report");
  await expect(byTestId(sme, "team-coverage")).toContainText("82%");
  await step(sme, "10a-sme-report");
  await sme.getByRole("radio", { name: "日本語" }).click();
  await expect(sme.getByText("インド進出チーム").first()).toBeVisible();
  await step(sme, "10b-sme-report-japanese");
  await sme.getByRole("radio", { name: "EN" }).click();
});
