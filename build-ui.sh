#!/bin/bash

if [ -d "ui/dist" ]; then
    echo "Removing existing ui/dist..."
    rm -rf ui/dist
fi
cd ui

npm install

npm ci
npm run lint
npm run build