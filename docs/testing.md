# 测试

统一测试命令（**在项目根目录执行**）：

    .venv\Scripts\python.exe -m pytest -q

或使用统一脚本（任意目录执行）：

    powershell -ExecutionPolicy Bypass -File scripts\test.ps1

- 收集目录固定在 `tests/`（pytest.ini: `testpaths = tests`）；`pythonpath = .` 已指向项目根，`backend` 包任意位置可导入。
- pytest 9 仅在根目录运行时采用 `testpaths`，请勿在子目录运行。
- 当前基线：**3 passed**（2026-10-06），详见 docs/implementation-status.md。
- 仿真演示：先启动后端，再执行 `python scripts/run_simulation.py`。
