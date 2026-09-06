# Publish Dashboard For Public Bot Invites

This project already contains a static invite dashboard at `docs/index.html`.

## What You Need

- A GitHub account
- This project pushed to a GitHub repository
- Your Discord app set with Guild Install enabled

## 1) Push This Project To GitHub

From your project folder:

```bash
git init
git add .
git commit -m "Add public invite dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

## 2) Turn On GitHub Pages

1. Open your repository on GitHub.
2. Go to Settings -> Pages.
3. Under Source, choose Deploy from a branch.
4. Branch: `main`, Folder: `/docs`.
5. Save.

GitHub will publish your page at:

`https://YOUR_USERNAME.github.io/YOUR_REPO/`

## 3) Share Your Public Dashboard Link

Send people your GitHub Pages URL. They can enter the Client ID and click Invite.

## Direct Invite URL Format

The dashboard generates this URL pattern:

`https://discord.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot%20applications.commands&permissions=81984`

## Troubleshooting

- If Discord shows install/scope errors, check Installation settings in the Discord Developer Portal.
- Keep Guild Install enabled.
- Make sure users adding the bot have permission to add bots in their server.
