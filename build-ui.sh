#!/bin/bash

if [ -d "ui/dist" ]; then
    echo "Removing existing ui/dist..."
    rm -rf ui/dist
fi
cd ui

npm install

echo "Running Install"
npm ci
echo "Running Lint"
npm run lint
echo "Running Build"
npm run build