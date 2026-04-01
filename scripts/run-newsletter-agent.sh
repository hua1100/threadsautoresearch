#!/bin/zsh -l
cd /Users/hua/threadsautoresearch
claude -p --dangerously-skip-permissions "讀 program.md，執行 Newsletter Agent" >> /Users/hua/threadsautoresearch/logs/newsletter-$(date +%Y-%m-%d).log 2>&1
