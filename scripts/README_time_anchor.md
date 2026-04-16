# Time Anchor System

A lightweight time awareness system to help maintain temporal context during long conversation sessions.

## How It Works

- `.current_time` file is updated every 5 minutes with the current time
- Format: `2026-04-16 14:32:00 CST | 02:32 PM | Day: Thursday`
- Located at: `/root/.openclaw/workspace/.current_time`

## Usage

Before making assumptions about time, read `.current_time`:

```bash
cat /root/.openclaw/workspace/.current_time
```

## Rules for Time Awareness

1. **Check the anchor** before saying things like "go to sleep" or "good morning"
2. **Remember the user's timezone** (Asia/Shanghai, GMT+8)
3. **Track session duration** - note when conversations start and how long they've been running
4. **Never assume** - if unsure, check the file or ask

## Cron Job

Updates every 5 minutes via cron:
```
*/5 * * * * /root/.openclaw/workspace/scripts/update_time_anchor.sh
```

---
Last updated: 2026-04-16
