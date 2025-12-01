#!/usr/bin/env bash
set -o errexit
set -o pipefail

echo "🔵 Step 1 — Installing Python dependencies"
pip install -r backend/requirements.txt

echo "🟢 Step 2 — Installing frontend dependencies"
cd frontend
npm install

echo "🟣 Step 3 — Building React app"
npm run build

echo "🟠 Step 4 — Copying build into backend/build"
rm -rf ../backend/build
mkdir -p ../backend/build
cp -R build/* ../backend/build/

echo "✅ Build completed successfully!"
