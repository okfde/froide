#!/bin/bash

if [ -f "node_modules/.linked" ]; then
    pnpm link "$(< node_modules/.linked)"
fi
