# Tractus

一个最小可用的 Flask 后端示例：通过 OpenAI SDK 调用 OpenAI 兼容接口（这里默认是 DashScope compatible mode）。

## 项目结构（中文说明）

这是一个典型的 Python `src/` 布局项目：业务代码都放在 `src/tractus/` 下，通过 `pip install -e .` 以“可编辑安装”方式让包可被导入。

目录大致如下：

```text
Tractus/
  src/
    tractus/
      __init__.py
      app.py
      cli.py
      config.py
      llm.py
      swagger/
        health.yml
        chat.yml
  pyproject.toml
  README.md
  .env.example
  .env                (本地机密，不要提交)
  .gitignore
  .venv/              (本地虚拟环境)
```

### 根目录文件

- `pyproject.toml`
  - 项目元数据与依赖（Flask / OpenAI SDK / dotenv / flasgger 等）
  - `poethepoet` 的任务定义：`poe serve ...`、`poe chat ...`
- `.env` / `.env.example`
  - `.env`：本地保存密钥与配置（已被 `.gitignore` 忽略，不会提交）
  - `.env.example`：模板文件，给团队成员复制后填写
- `.gitignore`
  - 忽略 `.env`、`.venv/`、构建产物等

### 后端包（src/tractus）

- `src/tractus/app.py`
  - Flask 应用工厂 `create_app()`
  - 提供接口：
    - `GET /health`：健康检查
    - `POST /chat`：一次性对话（传入 message，可选 model）
  - 集成 Swagger UI（flasgger）：
    - `GET /apidocs/`：Swagger UI
    - `GET /apispec_1.json`：Swagger 规范 JSON
- `src/tractus/swagger/*.yml`
  - Swagger 文档描述（从 `app.py` 中抽离到 YAML，避免代码臃肿）
  - `health.yml` 对应 `/health`，`chat.yml` 对应 `/chat`
- `src/tractus/config.py`
  - 配置读取：优先从环境变量/`.env` 读取 `DASHSCOPE_API_KEY`
  - 同时支持可选配置：`DASHSCOPE_BASE_URL`、`DASHSCOPE_MODEL`
- `src/tractus/llm.py`
  - 与模型端交互的薄封装：创建 OpenAI client + `chat_text()`
- `src/tractus/cli.py`
  - 项目 CLI（给 `poe` 调用）：
    - `poe serve 8000 --debug`
    - `poe chat 你好`
- `src/tractus/__init__.py`
  - 包导出（例如对外暴露 `create_app`）

## 环境准备

- 创建虚拟环境（示例）：
  - `python -m venv .venv`
  - `./.venv/Scripts/Activate.ps1`
- 安装依赖：
  - `pip install -e ".[dev]"`

## 配置密钥与参数

创建 `.env`（不要提交到 git），并设置：

- `DASHSCOPE_API_KEY=...`（必填）
- `DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`（可选）
- `DASHSCOPE_MODEL=qwen-long`（可选）

你可以先复制 `.env.example` 为 `.env` 再填写。

## 运行（Flask）

- 通过 poe：
  - `poe serve 8000 --debug`

健康检查：

- `GET http://127.0.0.1:8000/health`

Swagger UI：

- `GET http://127.0.0.1:8000/apidocs/`

对话接口：

- `POST http://127.0.0.1:8000/chat`
- JSON 请求体：`{ "message": "你好" }`

## 运行（一次性脚本）

- `python .\main.py`

## 任务脚本（poethepoet）

- 启动后端：`poe serve 8000 --debug`
- 单次对话：`poe chat 你好`
