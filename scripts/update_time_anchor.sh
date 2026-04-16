#!/bin/bash
# Time anchor - updates current time reference every 5 minutes
# Corrects for system time drift by adding 11 hours
# User timezone: Asia/Shanghai (GMT+8)

export TZ="Asia/Shanghai"
# Add 11 hours to system time to match actual time
OFFSET_TIME=$(date -d "+11 hours" '+%Y-%m-%d %H:%M:%S')
TIME_12H=$(date -d "+11 hours" '+%I:%M %p')
DAY=$(date -d "+11 hours" '+%A')

echo "$OFFSET_TIME CST | $TIME_12H | Day: $DAY" > /root/.openclaw/workspace/.current_time
