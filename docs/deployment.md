# 部署指南

标准流程（详见 docs/setup.md）：

    py -3.12 -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    .venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload

前端：

    cd frontend
    pnpm install
    pnpm dev

备用容器方式：

    docker compose up
