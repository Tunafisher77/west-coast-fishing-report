# Google Apps Script email setup

This is a one-time setup. The mail gateway is separate from the MLB project.

## 1. Create the Apps Script project

1. Open https://script.google.com and create a **New project**.
2. Name it **West Coast Fishing Report Mailer**.
3. Replace the contents of `Code.gs` with `apps-script/Code.gs` from this repository.
4. Open **Project Settings**, enable **Show "appsscript.json" manifest file**, and replace the manifest with `apps-script/appsscript.json`.

## 2. Create the shared secret

Generate a long random value locally or with a password manager. Do not post it in chat or commit it.

In Apps Script **Project Settings > Script Properties**, add:

- `FISHING_WEBHOOK_TOKEN` = the random value
- `FISHING_REPORT_TO` = the destination email address

Run `testFishingReportEmail` in the Apps Script editor and approve the requested mail permission. Confirm that the test arrives.

## 3. Deploy the web app

1. Select **Deploy > New deployment**.
2. Choose **Web app**.
3. Execute as: **Me**.
4. Who has access: **Anyone**.
5. Deploy and copy the URL ending in `/exec`.

The endpoint is public only so GitHub Actions can reach it; every mail request still requires the long shared token.

## 4. Add GitHub secrets

In the repository, open **Settings > Secrets and variables > Actions** and add:

- `APPS_SCRIPT_WEB_APP_URL` = the deployed `/exec` URL
- `FISHING_WEBHOOK_TOKEN` = the same random value

Never store either value in a repository file.

## 5. Validate

Open **Actions > Daily West Coast Fishing Report > Run workflow**. A successful run will:

1. test the model;
2. retrieve current sources;
3. build the HTML report;
4. send the email through Apps Script;
5. archive the source snapshot and report.

If either secret is absent, the workflow safely skips email but still creates the report artifact.
