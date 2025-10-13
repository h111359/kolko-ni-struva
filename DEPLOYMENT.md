# Kolko Ni Struva - Deployment Guide

## Overview

The `update-kolko-ni-struva.py` script now automatically deploys a ready-to-serve website to the `kolko-ni-struva/` folder after updating data.

## Quick Start

### Update and Deploy (Default)

```bash
./update.sh
```

This will:
1. Download today's and yesterday's data from kolkostruva.bg
2. Merge data into `data.csv` (keeps latest 2 days)
3. **Automatically deploy** all files to `kolko-ni-struva/` folder

### Update Without Deployment

```bash
./update.sh --no-deploy
```

Use this for testing or when you don't want to update the deployed folder.

## Deployment Structure

After running `./update.sh`, the `kolko-ni-struva/` folder contains:

```
kolko-ni-struva/
├── index.html                          # Website structure
├── script.js                           # Application logic with date selector
├── style.css                           # Styles
├── data.csv                            # Price data (latest 2 days by default)
├── category-nomenclature.json          # Category names
├── cities-ekatte-nomenclature.json     # City names (EKATTE codes)
└── trade-chains-nomenclature.json      # Trade chain names
```

This folder is **self-contained** and ready to deploy to any web server!

## Website Features

### Date Selector

- **Dynamic date selection**: Users can switch between available dates using a dropdown
- **Auto-loads latest date**: Website opens with the most recent data
- **Responsive updates**: All reports refresh when date changes
- **Bulgarian date format**: Displays dates as DD.MM.YYYY

### Reports

1. **Цени по категория** - Average prices by category for a selected city
2. **Продукти** - Product list filtered by city and category
3. **Сравнение по места** - Price comparison across cities for a category

All reports automatically filter by the selected date.

## Command Line Options

### Basic Usage

```bash
./update.sh [OPTIONS]
```

### Options

| Option | Description |
|--------|-------------|
| `--dates YYYY-MM-DD [...]` | Download specific dates (default: today and yesterday) |
| `--keep-all` | Keep all historical data instead of only latest 2 days |
| `--no-deploy` | Skip deploying files to kolko-ni-struva folder |
| `--netlify` | Deploy to Netlify after local deployment |

### Examples

**Download specific dates:**
```bash
./update.sh --dates 2025-10-12 2025-10-11
```

**Keep all historical data:**
```bash
./update.sh --keep-all
```

**Update without deployment (testing):**
```bash
./update.sh --no-deploy
```

**Combine options:**
```bash
./update.sh --dates 2025-10-12 --keep-all --no-deploy
```

**Update and deploy to Netlify:**
```bash
./update.sh --netlify
```

## Netlify Deployment

### Setup

The script includes automatic deployment to Netlify. Your site ID is: `b2c0c6b5-58f2-4620-892b-0f5a4d9513f2`

#### Prerequisites

1. **Install Netlify CLI** (one-time setup):
   ```bash
   npm install -g netlify-cli
   ```

2. **Get your Netlify Access Token**:
   - Go to https://app.netlify.com/user/applications/personal
   - Click "New access token"
   - Give it a name (e.g., "kolko-ni-struva-deploy")
   - Copy the token

3. **Set the environment variable**:
   
   **Option A: Temporary (current session only)**
   ```bash
   export NETLIFY_AUTH_TOKEN='your-netlify-token-here'
   ```
   
   **Option B: Permanent (add to ~/.bashrc or ~/.zshrc)**
   ```bash
   echo 'export NETLIFY_AUTH_TOKEN="your-netlify-token-here"' >> ~/.bashrc
   source ~/.bashrc
   ```

### Usage

**Deploy to Netlify:**
```bash
./update.sh --netlify
```

This will:
1. Download and merge data
2. Deploy files to local `kolko-ni-struva/` folder
3. Upload everything to Netlify

**Full workflow with Netlify:**
```bash
# Set token (if not set permanently)
export NETLIFY_AUTH_TOKEN='your-token-here'

# Update and deploy
./update.sh --netlify
```

### Netlify Site URL

After deployment, your site will be available at:
- **Site ID**: `b2c0c6b5-58f2-4620-892b-0f5a4d9513f2`
- **URL**: Check your Netlify dashboard or deployment output

### Troubleshooting Netlify

**Token not found:**
```
Error: Netlify token not found! Set NETLIFY_AUTH_TOKEN environment variable.
```
Solution: Set the `NETLIFY_AUTH_TOKEN` environment variable (see Setup above)

**CLI not found:**
```
Error: Netlify CLI not found! Install it with: npm install -g netlify-cli
```
Solution: Install Netlify CLI: `npm install -g netlify-cli`

**Check token is set:**
```bash
echo $NETLIFY_AUTH_TOKEN
```

## Deployment Process

The `deploy_to_folder()` function:

1. **Clears** the `kolko-ni-struva/` folder completely
2. **Recreates** the folder structure
3. **Copies** all 7 essential files
4. **Logs** progress and file sizes
5. **Handles errors** gracefully (continues if files are missing)

The `deploy_to_netlify()` function (optional, with `--netlify` flag):

1. **Checks** for NETLIFY_AUTH_TOKEN environment variable
2. **Verifies** deploy directory exists
3. **Uploads** entire folder to Netlify using netlify-cli
4. **Reports** deployment status and live URL

## Web Server Deployment

The `kolko-ni-struva/` folder can be deployed to any web server:

### Local Testing

```bash
cd kolko-ni-struva
python3 -m http.server 8000
# Open http://localhost:8000 in browser
```

### Apache

Copy the folder to your web server:
```bash
sudo cp -r kolko-ni-struva /var/www/html/
```

### Nginx

Update nginx config to serve the folder:
```nginx
location /kolko-ni-struva {
    root /path/to/;
    index index.html;
}
```

### Static Hosting (GitHub Pages, Netlify, etc.)

**Netlify (Automated):**
```bash
# Set your token once
export NETLIFY_AUTH_TOKEN='your-token-here'

# Deploy automatically
./update.sh --netlify
```

**Manual Upload:**
Simply upload the contents of `kolko-ni-struva/` folder to your static hosting service.

## Automation

### Daily Updates with Cron

Add to crontab:
```bash
# Run daily at 2 AM (without Netlify)
0 2 * * * cd /home/hromar/Desktop/vscode/kolko-ni-struva && ./update.sh >> update.log 2>&1

# Run daily at 2 AM (with Netlify deployment)
0 2 * * * cd /home/hromar/Desktop/vscode/kolko-ni-struva && export NETLIFY_AUTH_TOKEN='your-token' && ./update.sh --netlify >> update.log 2>&1
```

This will:
- Download fresh data daily
- Keep data.csv with latest 2 days
- Auto-deploy updated website
- (Optional) Upload to Netlify
- Log output to `update.log`

### Environment Variables for Cron

For cron jobs with Netlify, you can:

1. **Store token in a file** (more secure):
   ```bash
   echo 'your-netlify-token' > ~/.netlify-token
   chmod 600 ~/.netlify-token
   ```
   
   Then in cron:
   ```bash
   0 2 * * * cd /home/hromar/Desktop/vscode/kolko-ni-struva && export NETLIFY_AUTH_TOKEN=$(cat ~/.netlify-token) && ./update.sh --netlify >> update.log 2>&1
   ```

2. **Use a wrapper script**:
   Create `update-and-deploy.sh`:
   ```bash
   #!/bin/bash
   cd /home/hromar/Desktop/vscode/kolko-ni-struva
   source scraper_venv/bin/activate
   export NETLIFY_AUTH_TOKEN=$(cat ~/.netlify-token)
   python update-kolko-ni-struva.py --netlify
   ```
   
   Make it executable: `chmod +x update-and-deploy.sh`
   
   In cron:
   ```bash
   0 2 * * * /home/hromar/Desktop/vscode/kolko-ni-struva/update-and-deploy.sh >> update.log 2>&1
   ```

## File Sizes

Typical file sizes after deployment:

- `index.html`: ~6 KB
- `script.js`: ~14 KB
- `style.css`: ~8 KB
- `data.csv`: ~240 MB (2 days of data)
- `category-nomenclature.json`: ~4 KB
- `cities-ekatte-nomenclature.json`: ~160 KB
- `trade-chains-nomenclature.json`: ~5 KB

**Total**: ~240 MB (mostly data.csv)

## Troubleshooting

### Files not deploying

Check if files exist in the root folder:
```bash
ls -lh index.html script.js style.css data.csv *.json
```

### Large data.csv

If data.csv is too large, use `--keep-all` flag less frequently or manually clean old dates:
```bash
# Keep only last 2 days
./update.sh
```

### Permission errors

Ensure you have write permissions:
```bash
chmod -R u+w kolko-ni-struva/
```

### Netlify deployment fails

**Check token:**
```bash
echo $NETLIFY_AUTH_TOKEN
```

**Test Netlify CLI:**
```bash
netlify --version
netlify status --auth $NETLIFY_AUTH_TOKEN
```

**Manual deployment:**
```bash
cd kolko-ni-struva
netlify deploy --prod --site b2c0c6b5-58f2-4620-892b-0f5a4d9513f2 --auth $NETLIFY_AUTH_TOKEN
```

## Version Control

Add to `.gitignore` if you don't want to commit deployed files:
```
kolko-ni-struva/
.netlify-token
```

The deployment folder can be regenerated anytime by running `./update.sh`.

**Important**: Never commit your Netlify token to git!

## Next Steps

1. **Set up Netlify token** (one-time):
   ```bash
   export NETLIFY_AUTH_TOKEN='your-token-here'
   echo 'export NETLIFY_AUTH_TOKEN="your-token-here"' >> ~/.bashrc
   ```

2. **Test Netlify deployment**:
   ```bash
   ./update.sh --netlify
   ```

3. **Schedule daily updates** with cron (including Netlify)

4. **Monitor** deployment logs and data.csv size

5. **Backup** important data periodically

---

**Site ID**: `b2c0c6b5-58f2-4620-892b-0f5a4d9513f2`

**Last Updated**: October 14, 2025
