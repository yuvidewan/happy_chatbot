# Hugging Face Space: New Space Deploy Steps (Exact)

Use this when your old Space is blocked or unstable and you want a clean deploy.

---

## 0. What you need

- Local repo path: `C:\Users\yuvra\Desktop\PROJECTS\happybot`
- Hugging Face account logged in on browser
- Hugging Face access token with `Write` permission

Create token: `https://huggingface.co/settings/tokens`

---

## 1. Create a brand-new Space (UI)

1. Open: `https://huggingface.co/new-space`
2. Fill values:
- Owner: your account
- Space name: example `happiness-bot-v2`
- SDK: `Docker`
- Visibility: Public or Private
3. Click `Create Space`.

After creation, copy the new repo URL from page header. It will look like:
`https://huggingface.co/spaces/<your-username>/<new-space-name>`

---

## 2. Set required variable in the new Space

Open new Space -> `Settings` -> `Variables and secrets` -> `New variable`.

Add exactly:
- Name: `HAPPYBOT_BASE_MODEL_ID`
- Value: `Qwen/Qwen2.5-0.5B-Instruct`

Important:
- Do not use `=` in the value.
- Do not use `model` as variable name.
- Keep this in **Variables** (not required in Secrets for this value).

---

## 3. Add new git remote locally

From project folder:

```powershell
cd C:\Users\yuvra\Desktop\PROJECTS\happybot
git remote -v
```

Add new Space remote (replace URL):

```powershell
git remote add space2 https://huggingface.co/spaces/<your-username>/<new-space-name>
```

If `space2` already exists and points wrong:

```powershell
git remote remove space2
git remote add space2 https://huggingface.co/spaces/<your-username>/<new-space-name>
```

Verify:

```powershell
git remote -v
```

---

## 4. Push your code to the new Space

```powershell
git add .
git commit -m "Deploy to new HF Space"   # skip if no changes
git push origin master
git push space2 master:main
```

When prompted for credentials during `git push space2 ...`:
- Username: your HF username
- Password: your HF **token** (not HF account password)

---

## 5. Wait for build and test

1. Open new Space page.
2. Wait for status to become `Running`.
3. Open:
- `https://<new-subdomain>.hf.space/health`
- `https://<new-subdomain>.hf.space/`
4. Send one chat prompt in UI.

Expected behavior:
- App loads.
- First chat may be slow due to model download/cold start.

---

## 6. If push is rejected (non-fast-forward)

For a fresh Space where you want local repo to overwrite:

```powershell
git push --force space2 master:main
```

---

## 7. Daily deploy after this

```powershell
git add .
git commit -m "Update"
git push origin master
git push space2 master:main
```

---

## 8. Troubleshooting quick map

- Error: `Base Llama model not found`
  - Ensure variable exists in new Space:
    - `HAPPYBOT_BASE_MODEL_ID=Qwen/Qwen2.5-0.5B-Instruct`
  - Confirm latest code is pushed to Space.

- Space shows `503` during startup
  - Wait for initial model download/build.
  - Check Space logs in UI.

- Restart fails with generic UI error
  - Push one empty commit to trigger rebuild:

```powershell
git commit --allow-empty -m "Trigger HF rebuild"
git push origin master
git push space2 master:main
```
