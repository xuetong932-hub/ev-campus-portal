# Deployment guide

This guide takes the project from a folder on your computer to a public web
address that anyone can open. It has two parts:

* **Part A** – put the files on GitHub (≈ 10 minutes)
* **Part B** – deploy the GitHub repository to Streamlit Community Cloud (≈ 10 minutes)

Final addresses:

| | Address |
|---|---|
| GitHub repository | https://github.com/xuetong932-hub/ev-campus-portal |
| Public web app | https://xuetong-ev-campus.streamlit.app |

---

## Before you start

You need:

* A **GitHub account** (here: `xuetong932-hub`).
* The **empty public repository** `ev-campus-portal` on that account.
  If it does not exist yet: https://github.com/new → name `ev-campus-portal` →
  **Public** → leave *Add a README*, *.gitignore* and *license* **unticked** → **Create repository**.
* This project folder (`ev-campus-portal`) on your computer.

Check that the folder contains these items at its top level (not inside another folder):

```
app.py   ui.py   auth.py   ev_core.py   assessment1_billing_reference.py
data_pipeline.py   train_ev_model.py   test_app.py
ev_campus_dataset.csv   cleaned_ev_dataset.csv   ev_model.pkl   model_metadata.json
requirements.txt   README.md   .gitignore   .streamlit/   reports/   docs/   (+ summary CSV/JSON files)
```

> `app.py` **must** be at the top level of the repository, and `.streamlit/config.toml`
> must be inside a folder named exactly `.streamlit`. Otherwise Streamlit Cloud will not find them.

---

## Part A – Upload to GitHub

Choose **one** of the two methods.

### Method 1 – Web upload (no tools needed)

1. Open https://github.com/xuetong932-hub/ev-campus-portal and sign in.
2. On the empty repository page, click the link **"uploading an existing file"**
   (or **Add file → Upload files** if the repository already has content).
3. Open the `ev-campus-portal` folder in File Explorer.
4. In File Explorer, make hidden items visible: **View → Show → Hidden items**
   (so `.gitignore` and `.streamlit` are visible).
5. Press **Ctrl + A** to select **everything inside** the folder (not the folder itself)
   and drag it onto the GitHub upload area. Folders such as `reports`, `docs` and
   `.streamlit` keep their structure.
6. Wait until every file shows in the list (45 files, ≈ 3 MB).
7. Commit message: `Initial release: Campus EV Charging Research Portal`.
8. Select **Commit directly to the main branch** → **Commit changes**.
9. Refresh the repository page and check:
   * `app.py` and `requirements.txt` are at the top level;
   * the folder `.streamlit` exists and contains `config.toml`;
   * the README is displayed with screenshots below the file list.

If `.streamlit` is missing (some browsers skip folders starting with a dot):
**Add file → Create new file**, type `.streamlit/config.toml` as the name, paste
the contents of the local `config.toml`, and commit.

### Method 2 – Git command line

Run these in a terminal opened **inside** the `ev-campus-portal` folder:

```bash
git init -b main
git add .
git commit -m "Initial release: Campus EV Charging Research Portal"
git remote add origin https://github.com/xuetong932-hub/ev-campus-portal.git
git push -u origin main
```

A browser window asks you to sign in to GitHub the first time.

On Windows, if the push fails with *"error adding trust anchors"*, run this once
inside the folder and push again:

```bash
git config http.sslBackend schannel
```

---

## Part B – Deploy on Streamlit Community Cloud

1. Open **https://share.streamlit.io** and click **Continue with GitHub**.
   Approve the permissions Streamlit asks for (it needs to read your repositories).
2. Click **Create app** (top right).
3. Choose **Deploy a public app from GitHub**.
4. Fill in the form:

   | Field | Value |
   |---|---|
   | Repository | `xuetong932-hub/ev-campus-portal` |
   | Branch | `main` |
   | Main file path | `app.py` |
   | App URL (optional) | `xuetong-ev-campus` |

   If the App URL is taken, Streamlit shows a warning; pick another name and
   update the links in `README.md` afterwards. Streamlit also rejects custom
   subdomains that contain the word **"portal"**, which is why this project uses
   `xuetong-ev-campus` rather than the repository name.
5. Click **Advanced settings**:
   * **Python version: 3.12** ← required, because `ev_model.pkl` was trained on 3.12.
   * Secrets: leave empty (the app needs none).
   * Click **Save**.
6. Click **Deploy**.
7. Streamlit installs the packages from `requirements.txt` (about 2–4 minutes).
   You can watch the log in the **Manage app** panel at the bottom right.
8. When the sign-in page with the starry sky appears, the deployment is finished.

### Check the live app

Open https://xuetong-ev-campus.streamlit.app in a **private/incognito window**
(to be sure it works for people who are not signed in to Streamlit) and test:

- [ ] The sign-in page shows the moving stars and the charging-station photo.
- [ ] `SESS-1000` signs in and the Dashboard shows **18,630.09 kWh** total energy.
- [ ] Analytics shows three charts (not broken images).
- [ ] Live Prediction shows a **green** Normal banner; battery temperature 48 → **yellow**; temperature 35 and start hour 14 → **red**.
- [ ] Registering a new ID works and the onboarding guide appears on first sign-in.

### Sharing

* The app is public: anyone with the link can open it, no Streamlit account needed.
* Community Cloud apps **sleep after a few days without visitors**. A sleeping app
  shows "This app has gone to sleep"; click **Yes, get this app back up** and it
  starts in about 30 seconds. Open the link yourself shortly before it is marked.

---

## Updating the app later

Every commit to the `main` branch redeploys automatically within a minute or two.

* Web: open a file on GitHub → pencil icon → edit → **Commit changes**.
* Git: `git add . && git commit -m "message" && git push`.

If you change the data or retrain the model locally, commit the regenerated
`cleaned_ev_dataset.csv`, `ev_model.pkl`, `model_metadata.json` and `reports/` too.

---

## Troubleshooting the deployment

| Message in the Streamlit log or app | Fix |
|---|---|
| `ModuleNotFoundError` | A package is missing from `requirements.txt`, or the file is not at the top level. |
| "Cannot load the saved model … scikit-learn" | Python version is not 3.12 or `requirements.txt` was changed. **Manage app → ⋮ → Settings → Python version 3.12**, then **Reboot app**. |
| Analytics charts are broken images | `starlette==1.3.1` is missing from `requirements.txt`. |
| "Main module does not exist" | Main file path must be `app.py`, and `app.py` must be at the repository root. |
| Theme is light instead of dark | `.streamlit/config.toml` was not uploaded (see the note in Part A). |
| Registered users vanish after some time | Expected: Community Cloud resets files on restart. See README → Limitations. |
