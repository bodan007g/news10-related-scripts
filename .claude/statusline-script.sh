#!/bin/bash

# Read JSON input from stdin
input=$(cat)

# Extract information from JSON
model_name=$(echo "$input" | jq -r '.model.display_name')
current_dir=$(echo "$input" | jq -r '.workspace.current_dir')
transcript_path=$(echo "$input" | jq -r '.transcript_path')
output_style=$(echo "$input" | jq -r '.output_style.name')

# Calculate context length (approximate token count from transcript)
if [ -f "$transcript_path" ]; then
    # Rough estimation: 1 token ≈ 4 characters for English text
    char_count=$(wc -c < "$transcript_path" 2>/dev/null || echo "0")
    context_tokens=$((char_count / 4))
    if [ $context_tokens -gt 1000 ]; then
        context_display=$(printf "%.1fk" $(echo "scale=1; $context_tokens / 1000" | bc 2>/dev/null || echo "$((context_tokens / 1000))"))
    else
        context_display="${context_tokens}"
    fi
else
    context_display="0"
fi

# Get git status (skip locks to avoid blocking)
cd "$current_dir" 2>/dev/null || cd /
git_info=""
if git rev-parse --git-dir >/dev/null 2>&1; then
    # Get branch name
    branch=$(git branch --show-current 2>/dev/null || git rev-parse --short HEAD 2>/dev/null || echo "detached")
    
    # Get file changes (skip if .git/index.lock exists)
    if [ ! -f ".git/index.lock" ]; then
        changes=$(git status --porcelain 2>/dev/null | wc -l)
        if [ $changes -gt 0 ]; then
            git_info=" ${branch}(${changes})"
        else
            git_info=" ${branch}"
        fi
    else
        git_info=" ${branch}"
    fi
fi

# Current directory display (show last 2 path components)
short_dir=$(echo "$current_dir" | awk -F'/' '{if(NF>2) print $(NF-1)"/"$NF; else print $0}')

# Claude usage info (simplified - shows model and style)
model_short=$(echo "$model_name" | sed 's/Claude //' | sed 's/ Sonnet//')
usage_info="${model_short}"
if [ "$output_style" != "null" ] && [ "$output_style" != "default" ]; then
    usage_info="${usage_info}:${output_style}"
fi

# Combine all information with colors (using printf for ANSI codes)
printf "\033[2m%s \033[0m\033[36m%s\033[0m\033[2m ctx:%s%s\033[0m" \
    "$usage_info" \
    "$short_dir" \
    "$context_display" \
    "$git_info"