#!/bin/bash

linked=$(pnpm list --json | jq -r '.[0].dependencies.[]|select(.version | startswith("link:"))')
packages=$(echo $linked | jq -r '.from')
paths=$(echo $linked | jq -r '.version|sub("link:";"")')

if [ -z "$paths" ]; then
    exit 0;
fi

echo "$paths" > node_modules/.linked

pnpm unlink "$packages"
git add pnpm-lock.yaml pnpm-workspace.yaml
