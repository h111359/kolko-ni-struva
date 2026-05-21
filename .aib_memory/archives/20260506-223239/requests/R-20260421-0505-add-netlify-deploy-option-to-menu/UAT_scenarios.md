# UAT Scenarios — R-20260421-0505

## UAT-01: End-to-end deploy with live Netlify credentials

**Preconditions:**
- Netlify CLI installed globally (`npm install -g netlify-cli`) or `npx netlify` available.
- A valid Netlify account with an existing site.
- `NETLIFY_AUTH_TOKEN` not set in environment (to test prompt flow).
- `NETLIFY_SITE_ID` not set in environment (to test prompt flow).
- Node.js and npm installed.
- `react-app/` is a valid Vite project with `npm run build` working.

**Steps:**
1. Run `python menu.py`.
2. At the menu, enter `5`.
3. Observe the credential prompts with instructions.
4. Follow the on-screen instructions to obtain a Netlify personal access token from the Netlify dashboard.
5. Paste the token at the `NETLIFY_AUTH_TOKEN` prompt.
6. Follow the on-screen instructions to obtain the site ID from the Netlify site settings.
7. Paste the site ID at the `NETLIFY_SITE_ID` prompt.
8. Observe `npm run build` executing in `react-app/`.
9. Observe `netlify deploy --prod` executing and producing a deploy URL.

**Expected outcome:**
- Build completes successfully.
- Deploy completes with a production URL printed.
- No credentials written to disk.
- Returning to the menu prompt after completion.
