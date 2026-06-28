# Staggered GTT OMS — AI Features Setup Guide
# Powered by Google Gemini API (Free)

## Models Used

| Model | Use Case | Free Tier Limits |
|---|---|---|
| **Gemini 3.5 Flash** | Fast tasks (sentiment, NLP parsing) | 15 req/min, 1,500 req/day |
| **Gemini 3.1 Pro** | Smart tasks (analysis, suggestions, portfolio) | 2 req/min, 50 req/day |

## Getting Your Free Gemini API Key

1. Go to [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Select "Create API key in new project" or choose an existing Google Cloud project
5. Copy the key (starts with "AIza...")
6. Open Staggered GTT OMS
7. Go to **AI Settings ⚙️** panel
8. Paste key in the "Gemini API Key" field
9. Click "Save Key"
10. Click "Test Connection" to verify

The key is **AES-256 encrypted** and stored locally in your database.

## Free Tier Limits

**Gemini 3.1 Pro:**
- 2 requests per minute
- 50 requests per day
- 1M tokens per minute

**Gemini 3.5 Flash:**
- 15 requests per minute  
- 1,500 requests per day
- 1M tokens per minute

**For your GTT OMS usage:**
One stock analysis session uses 3-5 API calls. The 50 req/day limit on Pro equals 10-15 complete analysis sessions/day. This is MORE than sufficient for personal use and managing up to 10 client accounts.

## Rate Limit Handling

The app automatically handles rate limits:
- Retries up to 3 times with exponential backoff
- Shows a friendly message if the limit is reached
- App continues working normally without AI features

If you hit the 50 req/day limit on Gemini 3.1 Pro:
- Wait until midnight (resets daily)
- Or upgrade to the Gemini API paid tier ($0.00125/1K tokens)

## Installing Dependencies

```powershell
pip install -r requirements.txt
```

Key packages:
- `google-generativeai>=0.8.0`
- `ta>=0.11.0`
- `newsapi-python>=0.2.7`

## Testing AI Features

1. Get your API key from `aistudio.google.com/apikey`
2. Open the app, unlock with master password
3. Go to the **AI Settings ⚙️** panel
4. Paste your API key, click **Save**, click **Test Connection**
5. Should show a green "Connected" message
6. Connect Breeze session (Session panel)
7. Fetch holdings (Holdings panel)
8. Click **AI Analyze** on any stock row
9. Analysis appears in 5-10 seconds

## Troubleshooting

- **"API Key not configured"**
  Go to AI Settings panel and save your Gemini key.

- **"Gemini returned no candidates / blocked"**
  Safety filters triggered on financial content. This is already handled — the app uses `BLOCK_NONE` settings. If it persists, try rephrasing the stock name.

- **"Rate limit exceeded"**
  Hit 2 req/min limit on Gemini 3.1 Pro. Wait 30 seconds and retry. Or hit 50 req/day limit — wait until midnight IST.

- **"Model not found"**
  Check `google-generativeai` package version. Run: `pip install --upgrade google-generativeai`

- **AI features show error but app still works**
  Expected behavior — AI is optional. Core GTT order placement is unaffected.

## Cost (Spoiler: Free)

- **Personal use:** ₹0/month
- **10 client accounts:** ₹0/month

It only costs money if you exceed 50 analyses/day on Gemini 3.1 Pro (which is very unlikely for private use).

## Changelog

**May 2026:**
- Migrated from Amazon Bedrock (Claude) to Google Gemini
- Using Gemini 3.1 Pro for analysis (free tier)
- Using Gemini 3.5 Flash for simple tasks (free tier)
- Removed all AWS/boto3 dependencies
- Added encrypted Gemini API key storage in local DB
