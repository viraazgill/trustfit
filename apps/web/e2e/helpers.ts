import path from "node:path";
import { expect, type Page } from "@playwright/test";

export const SHOTS = path.resolve(__dirname, "../../../artifacts/screenshots");

export async function signIn(page: Page, role: "analyst" | "admin" | "viewer") {
  const email = process.env[`SEED_${role.toUpperCase()}_EMAIL`] ?? `${role}@trustfit.local`;
  const password = process.env[`SEED_${role.toUpperCase()}_PASSWORD`] ?? `change-me-${role}`;
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

export async function shot(page: Page, name: string) {
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
}
