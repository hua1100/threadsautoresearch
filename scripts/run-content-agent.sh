#!/bin/zsh -l
cd /Users/hua/threadsautoresearch
claude -p --dangerously-skip-permissions "讀 program.md，執行 Content Agent" >> /Users/hua/threadsautoresearch/logs/content-$(date +%Y-%m-%d).log 2>&1
