Phase 6: make the demo bulletproof and memorable.

Read docs/06-demo-script.md.

1. Landing page `/`: the line "Trust decides eligibility. Fit justifies the visit.", the three modules
   in one row, and two buttons: "See a Trust Score (Subros)" and "Try the SME journey (Sorano, demo data)".
2. Demo mode: `SCORING_AS_OF` support end to end, a "Reset demo data" button for admins
   (runs the seed with `--reset`), and a visible "Demo data" ribbon on fictional records.
3. PDF: `GET /smes/{id}/report.pdf` and a Trust report PDF, printed with Playwright from the same pages
   (print stylesheet, A4). The PDF must match the screen.
4. Japanese toggle (EN/JA) on SME pages with next-intl. Put every Japanese string in
   `messages/ja.json` with a `// REVIEW` note file listing them for a human to check. Numbers and
   company names stay as they are.
5. Disclaimer on every SME page and PDF: "TrustFit Score is not a credit rating or investment advice."
6. Deploy: web to Vercel, API to Render or Railway, Postgres on Neon; document the environment
   variables in the README; CI deploys on merge to main only after tests pass.
7. One Playwright end-to-end test that runs the whole demo script in docs/06-demo-script.md and saves
   screenshots of every step to `artifacts/demo/`.
8. Performance: scoring a company and building the Sorano bridge each respond in under 1 second locally.

Done when the end-to-end test passes against the deployed URL and against `docker compose up`
offline. Commit "feat: demo polish, PDF, i18n, deploy". Show me the screenshots folder.
