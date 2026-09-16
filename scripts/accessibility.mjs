import { AxeBuilder } from "@axe-core/playwright";
import { chromium } from "playwright";

const baseUrl = process.env.DOCS_BASE_URL ?? "http://127.0.0.1:8000";
const pages = ["/", "/getting-started/create-project/", "/reference/api/", "/troubleshooting/"];
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const failures = [];

for (const path of pages) {
  const page = await context.newPage();
  await page.goto(`${baseUrl}${path}`, { waitUntil: "networkidle" });
  const results = await new AxeBuilder({ page }).analyze();
  for (const violation of results.violations) {
    const targets = violation.nodes.flatMap((node) => node.target).join(", ");
    failures.push(`${path}: ${violation.id}: ${violation.help}: ${targets}`);
  }
  await page.close();
}

await context.close();
await browser.close();
if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}
console.log(`axe accessibility checks passed for ${pages.length} representative pages`);
