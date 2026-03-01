# Hugging Face Space Git Steps (vs GitHub)

Space repo:
`https://huggingface.co/spaces/yuvidewan2005/happiness_bot`

## 1. One-time setup (local repo)

From `happybot` folder, confirm remotes:

```powershell
git remote -v
```

If `space` remote is missing, add it:

```powershell
git remote add space https://huggingface.co/spaces/yuvidewan2005/happiness_bot
```

## 2. Normal edit -> commit -> push flow

```powershell
git add .
git commit -m "Your message"
```

Push to GitHub (`origin`):

```powershell
git push origin master
```

Push same commit to Hugging Face Space (`space` -> `main`):

```powershell
git push space master:main
```

## 3. Authentication for Hugging Face push

When prompted during `git push space ...`:

- Username: your Hugging Face username (`yuvidewan2005`)
- Password: Hugging Face **Access Token** (role: `Write`)

Do not use email or normal HF login password for Git push.

Create token here:
`https://huggingface.co/settings/tokens`

## 4. If push to Space is rejected (fetch first / non-fast-forward)

If the Space has commits you do not have locally (common for new Space starter files), and you want local repo to replace Space:

```powershell
git push --force space master:main
```

If you want to keep both histories and merge instead:

```powershell
git fetch space
git merge space/main --allow-unrelated-histories
git push space master:main
```

## 5. Key difference: GitHub vs Hugging Face Space

- GitHub remote in your repo is `origin` and branch is `master`.
- Hugging Face Space remote is `space` and deploy branch is usually `main`.
- So for Space you typically push as `master:main`.
- Space rebuild/deploy starts after push to Space repo.

## 6. Useful daily commands

Check what will be committed:

```powershell
git status
```

See latest commits:

```powershell
git log --oneline -n 5
```

Push one commit to both remotes:

```powershell
git push origin master
git push space master:main
```

