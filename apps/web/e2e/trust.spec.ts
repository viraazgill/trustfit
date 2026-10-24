import { expect, test } from "@playwright/test";
import { SHOTS, shot, signIn } from "./helpers";

// Demo script part 1 (docs/06-demo-script.md). Needs Postgres with seeded data: `make db seed`.
test("Subros: 87 Amber, integrity what-if turns it Green at 90, JV partner 86", async ({ page }) => {
  await signIn(page, "analyst");

  await page.goto("/companies");
  await expect(page.getByRole("link", { name: "Subros Ltd" })).toBeVisible();
  await expect(page.getByText("Fictional demo data").first()).toBeVisible();
  await shot(page, "03-1-companies");

  await page.getByRole("link", { name: "Subros Ltd" }).click();
  await expect(page.getByTestId("score")).toHaveText("87");
  await expect(page.getByTestId("band")).toHaveText("Very strong");
  await expect(page.getByTestId("verdict").first()).toHaveText("Amber");
  await expect(page.getByTestId("outlook")).toContainText("Watch");
  await expect(page.getByTestId("reasons")).toContainText("Integrity is 32.5% verified, under the 50% minimum");
  await shot(page, "03-2-subros-supplier");

  await page.getByRole("button", { name: "What-if" }).click();
  await page.getByRole("button", { name: "Integrity checks clean" }).click();
  await expect(page.getByText("Preset: A1, A3, A4, A5, C1, C2")).toBeVisible();
  await expect(page.getByRole("dialog").getByText("82.5 verified")).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/03-3a-what-if-drawer.png` });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(page.getByTestId("what-if-banner")).toBeVisible();
  await expect(page.getByTestId("score")).toHaveText("90");
  await expect(page.getByTestId("verdict").first()).toHaveText("Green");
  await expect(page.getByTestId("confidence")).toContainText("82.5");
  await shot(page, "03-3-subros-what-if-green");

  await page.getByRole("button", { name: "Exit what-if" }).click();
  await page.getByRole("tab", { name: "JV partner" }).click();
  await expect(page.getByTestId("score")).toHaveText("86");
  await expect(page.getByTestId("verdict").first()).toHaveText("Amber");
  await shot(page, "03-4-subros-jv-partner");
});

test("evidence grid and flags page render for Subros", async ({ page }) => {
  await signIn(page, "analyst");
  await page.goto("/companies/subros/evidence");
  await expect(page.getByTestId("evidence-A1")).toBeVisible();
  await expect(page.getByTestId("evidence-H2")).toBeVisible();
  await shot(page, "03-5-subros-evidence");
  await page.screenshot({ path: `${SHOTS}/03-5a-subros-evidence-top.png` });
  await page.goto("/companies/subros/flags");
  await expect(page.getByText("Verification gates")).toBeVisible();
  await shot(page, "03-6-subros-flags");
});

test("a knock-out company is Red and not eligible", async ({ page }) => {
  await signIn(page, "analyst");
  await page.goto("/companies/konkan-trade");
  await expect(page.getByTestId("score")).toHaveText("Not eligible");
  await expect(page.getByTestId("verdict").first()).toHaveText("Red");
});
