import fs from "node:fs";
import { expect, test } from "@playwright/test";
import { byTestId, signIn } from "./helpers";

// The API prints these PDFs with Playwright from the same pages (needs `pip install -e "apps/api[pdf]"`).
test("the SME report and the Trust report download as PDFs", async ({ page }) => {
  test.setTimeout(120_000);
  await signIn(page, "viewer");
  await page.goto("/sme/sorano/report");
  await expect(byTestId(page, "team-coverage")).toContainText("82%");
  const [smePdf] = await Promise.all([page.waitForEvent("download"), byTestId(page, "pdf-button").click()]);
  expect(smePdf.suggestedFilename()).toBe("trustfit-sorano.pdf");
  const smeBytes = fs.readFileSync(await smePdf.path());
  expect(smeBytes.subarray(0, 4).toString()).toBe("%PDF");

  await page.goto("/report/company/subros?role=supplier");
  await expect(byTestId(page, "score")).toHaveText("87");
  const [trustPdf] = await Promise.all([page.waitForEvent("download"), byTestId(page, "pdf-button").click()]);
  expect(trustPdf.suggestedFilename()).toBe("trustfit-subros-supplier.pdf");
  await trustPdf.saveAs("../../artifacts/screenshots/06-trust-report-subros.pdf");
  await smePdf.saveAs("../../artifacts/screenshots/06-sme-report-sorano.pdf");
});
