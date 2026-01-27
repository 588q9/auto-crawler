# AI Agent 运行规则

- 使用本项目虚拟环境 Python：`venv\Scripts\python.exe`
- 所有运行、编译、测试命令必须使用上述路径，不使用系统环境变量中的 `python`
- 示例：
  - 编译：`"venv\Scripts\python.exe" -m py_compile main.py`
  - 查看 CLI：`"venv\Scripts\python.exe" main.py --help`
- 环境变量：
  - `CONFIG_PATH` 指向配置文件（默认 `config/config.yaml`）
  - `COOKIE_HEADER` 或 `MOODLE_COOKIE` 提供完整 Cookie 头，用于签到/刷课鉴权
- 运行约定：
  - 运行签到：`"venv\Scripts\python.exe" main.py checkin run --once` 或 `--once` 省略启动每日调度
  - 运行刷课：`"venv\Scripts\python.exe" main.py course watch_course_incomplete --course-id <ID>`
- Docker 仅用于容器运行；在宿主机开发与验证一律使用本地 venv Python
