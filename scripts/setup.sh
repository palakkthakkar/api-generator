#!/bin/bash
# ================================================
# SentinelAPI — Quick Setup Script
# Run from the project root: bash scripts/setup.sh
# ================================================
 
set -e
echo "🛡️  Setting up SentinelAPI..."
 
# ── Create all directories ──
mkdir -p sdk/sentinel_sdk
mkdir -p server/app/{routes,services,models,ml,workers}
mkdir -p server/tests
mkdir -p dashboard/src/{components,hooks,utils}
mkdir -p scripts
mkdir -p docker
mkdir -p models
 
# ── Create all __init__.py files ──
touch sdk/sentinel_sdk/__init__.py
touch server/app/__init__.py
touch server/app/routes/__init__.py
touch server/app/services/__init__.py
touch server/app/models/__init__.py
touch server/app/ml/__init__.py
touch server/app/workers/__init__.py
 
# ── Create .env ──
cat > server/.env << 'EOF'
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://sentinel:sentinel@localhost:5432/sentinel
EOF
 
# ── Create .gitignore ──
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.pyo
.env
node_modules/
*.egg-info/
dist/
build/
.venv/
venv/
models/*.pt
models/*.pkl
.DS_Store
EOF
 
echo ""
echo "✅ Project structure ready. Next steps:"
echo "   1. Copy SDK files into sdk/sentinel_sdk/"
echo "   2. Copy server files into server/app/"
echo "   3. Copy dashboard files into dashboard/src/"
echo "   4. Start Redis:     redis-server"
echo "   5. Start Postgres:  docker run -d -p 5432:5432 -e POSTGRES_USER=sentinel -e POSTGRES_PASSWORD=sentinel -e POSTGRES_DB=sentinel postgres:16-alpine"
echo "   6. Start server:    cd server && pip install -r requirements.txt && uvicorn app.main:app --port 8100 --reload"
echo "   7. Start aggregator: cd server && python -m app.workers.aggregator"
echo "   8. Start dashboard: cd dashboard && npm install && npm start"
echo ""