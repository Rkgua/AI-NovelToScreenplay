# Novel2Script — AI 辅助小说转剧本工具

## 简介

将 3 章以上小说（EPUB / TXT / Markdown）自动转换为结构化 YAML 剧本。

### 主分支

### 开发分支PR

1. UserProcessBetter

#### 标题

在主分支基础上添加模仿编译器报错,旨在为在用户编辑校验后提供错误提示,方便用户编辑

#### 功能描述

#### 实现思路

2. AddTimeline

#### 标题

在主分支基础上添加时间轴功能,方便用户快速预览剧本结构,支持鼠标查看具体相关以及基本修改

#### 功能描述

#### 实现思路

3. 校验功能优化 AI答疑
## 快速开始

```bash
# 1. 安装
cd novel-to-script
uv venv
uv pip install -e .

# 2. 配置 .env
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY=sk-xxx

# 3. 使用
python -m src.cli convert 小说.txt -o output/剧本.yaml   # CLI
python -m src.cli launch                                     # Web UI
```

---

### 时间线功能介绍

基于beat的时间线 基于使用了beat卡片三个 A(action动作) D(dialogue对话) T(transition转场类型)

## 项目结构

```
novel-to-script/
├── pyproject.toml            # 项目配置与依赖声明
├── .env.example              # 环境变量模板
├── schema_doc.md             # YAML Schema 设计文档
├── README.md                 # 本文件
│
├── src/
│   ├── cli.py                # CLI 入口 (Typer + Rich)
│   ├── config.py             # 全局配置 (LLMConfig / AppConfig)
│   │
│   ├── schema/               # 剧本 Schema 定义
│   │   ├── screenplay.py     # Pydantic 数据模型
│   │   └── validator.py      # YAML 校验、加载、导出
│   │
│   ├── parser/               # 文本解析
│   │   ├── chapter.py        # Chapter 数据结构 & 章节切分
│   │   ├── txt.py            # TXT / Markdown 解析
│   │   ├── epub.py           # EPUB 电子书解析
│   │   └── __init__.py       # 统一入口 parse_file()
│   │
│   ├── llm/                  # LLM 统一接口层
│   │   ├── base.py           # 抽象基类 + 工厂函数 + 结构化 Schema 构建
│   │   ├── openai_adapter.py # OpenAI 兼容适配 (OpenAI / DeepSeek)
│   │   ├── claude_adapter.py # Anthropic Claude 适配
│   │   └── ollama_adapter.py # Ollama 本地模型适配
│   │
│   ├── pipeline/             # AI 转换流水线
│   │   ├── pipeline.py       # 流水线编排器
│   │   ├── character.py      # 阶段1: 角色识别
│   │   ├── summary.py        # 阶段2: 章节摘要
│   │   ├── chapter_processor.py # 阶段3+4: 分场 + 节拍提取（合并调用）
│   │   ├── scene.py          # 阶段3: 分场（旧，流水线不再使用）
│   │   ├── dialogue.py       # 阶段4: 节拍提取（旧，流水线不再使用）
│   │   └── assembler.py      # 阶段5: 组装为 Screenplay 对象
│   │
│   └── web/                  # Web UI
│       └── app.py            # Gradio 交互界面
│
└── tests/                    # 测试
```

---

## 模块详解

### 1. `src/cli.py` — CLI 入口

| 函数 / 组件                                               | 作用                                                          |
| --------------------------------------------------------- | ------------------------------------------------------------- |
| `convert(source, output, model, title, author, chapters)` | 命令行转换：`python -m src.cli convert novel.txt -o out.yaml` |
| `validate(screenplay)`                                    | 校验已有 YAML 是否符合 Schema                                 |
| `launch(share, port)`                                     | 启动 Gradio Web UI                                            |

**依赖第三方库：** `typer` (CLI 框架), `rich` (彩色终端输出)

---

### 2. `src/config.py` — 配置管理

| 类          | 作用                                                                          |
| ----------- | ----------------------------------------------------------------------------- |
| `LLMConfig` | 模型提供商 (deepseek/openai/claude/ollama)、模型名、API Key、API Base、温度等 |
| `AppConfig` | 全局配置，含 `LLMConfig` + `PipelineConfig` + 输出目录                        |

环境变量读取：`python-dotenv` 自动加载 `.env` 文件。

---

### 3. `src/schema/` — 剧本 Schema

#### `screenplay.py` — Pydantic 数据模型

| 类                | 说明                                                                         |
| ----------------- | ---------------------------------------------------------------------------- |
| `Meta`            | 剧本元信息：标题、来源、作者、类型、版本                                     |
| `Character`       | 角色档案：ID、姓名、性别、年龄、性格特征、关系网                             |
| `SceneHeading`    | 场次标题 (slug line)：INT/EXT、地点、时间                                    |
| `Beat` (联合类型) | `ActionBeat` (动作/舞台指示)、`DialogueBeat` (对白)、`TransitionBeat` (转场) |
| `Scene`           | 场次：heading + summary + beats 序列                                         |
| `Act`             | 幕：包含多个 Scene                                                           |
| `Structure`       | 剧本结构：acts 列表                                                          |
| `Screenplay`      | 顶层模型：meta + characters + structure                                      |

**依赖第三方库：** `pydantic` (数据校验与序列化)

#### `validator.py` — YAML 校验

| 函数                        | 作用                                     |
| --------------------------- | ---------------------------------------- |
| `load_screenplay(path)`     | 从 YAML 加载并校验为 Screenplay 对象     |
| `validate_screenplay(path)` | 结构 + 语义校验，返回 `ValidationResult` |
| `save_screenplay(sp, path)` | 导出 Screenplay 为 YAML 文件             |

**依赖第三方库：** `pyyaml` (YAML 解析与生成)

---

### 4. `src/parser/` — 文本解析

#### `chapter.py` — 章节切分引擎

| 函数 / 类                | 作用                                         |
| ------------------------ | -------------------------------------------- |
| `Chapter` (dataclass)    | 章节数据：index、title、paragraphs、raw_text |
| `detect_and_split(text)` | 自动检测章节标记并切分                       |

支持的章节标记：

- 中文：`第一章`、`第十二章`、`第15章`、`楔子`、`尾声`、`番外篇`
- 英文：`Chapter 1`、`Chapter 2`
- 无标记时回退为单章 `全文`

**纯 Python 标准库实现，无第三方依赖。**

#### `txt.py` — TXT/MD 解析

| 函数              | 作用                                                                                       |
| ----------------- | ------------------------------------------------------------------------------------------ |
| `parse_txt(path)` | 多编码回退读取 (UTF-8 → GBK → GB18030 → UTF-16 → latin-1)，跳过 Markdown YAML front matter |

#### `epub.py` — EPUB 解析

| 函数               | 作用                                                                 |
| ------------------ | -------------------------------------------------------------------- |
| `parse_epub(path)` | 使用 ebooklib 提取正文，BeautifulSoup 清洗 HTML，从 TOC 提取章节标题 |

**依赖第三方库：** `ebooklib` (EPUB 解析), `beautifulsoup4` + `lxml` (HTML 清洗)

---

### 5. `src/llm/` — LLM 接口层

#### `base.py` — 抽象基类与工厂

| 组件                                  | 作用                                                                                         |
| ------------------------------------- | -------------------------------------------------------------------------------------------- |
| `BaseLLMAdapter` (ABC)                | 抽象接口：`complete()` 纯文本调用、`complete_structured()` 结构化输出、`count_tokens()` 计费 |
| `create_adapter(config)`              | 工厂函数：根据 `LLMConfig.provider` 创建对应适配器实例                                       |
| `build_structured_schema(properties)` | 快捷构建 JSON Schema                                                                         |
| `LLMError`                            | 自定义异常                                                                                   |

内置 3 次指数退避重试 (`complete_with_retry` / `complete_structured_with_retry`)。

#### `openai_adapter.py` — OpenAI / DeepSeek 适配

- OpenAI: 使用 `response_format: json_schema` (strict mode) 强制结构化输出
- DeepSeek: 使用 `response_format: json_object` + prompt 注入 Schema（DeepSeek 不支持严格 JSON Schema 模式）
- Token 计数：`tiktoken`

**依赖第三方库：** `openai` (OpenAI Python SDK), `tiktoken` (Token 计数)

#### `claude_adapter.py` — Claude 适配

- 通过 Anthropic Messages API 调用
- 结构化输出：将 JSON Schema 转为 Claude Tool Use 定义
- Token 计数：`tiktoken` (cl100k_base 编码)

**依赖第三方库：** `anthropic` (Anthropic Python SDK), `tiktoken`

#### `ollama_adapter.py` — Ollama 适配

- 通过 Ollama Generate API 调用本地模型
- 结构化输出：prompt 注入 JSON Schema + 输出后 JSON 提取 + 3 次解析重试
- Token 计数：`len(text) // 2` 粗略估算

**依赖第三方库：** `ollama` (Ollama Python SDK)

---

### 6. `src/pipeline/` — 转换流水线

#### `pipeline.py` — 编排器

| 函数                                                          | 作用                                      |
| ------------------------------------------------------------- | ----------------------------------------- |
| `run_pipeline(chapters, config, meta, progress)`              | 串行执行 5 个阶段，返回 `Screenplay` 对象 |
| `run_and_save(chapters, config, output_path, meta, progress)` | = `run_pipeline` + 保存为 YAML            |

进度回调签名：`(phase: str, current: int, total: int) -> None`

转换流程：

```
parse_file → extract_characters → 每章 summarize → process_chapter → assemble → YAML
```

#### `character.py` — 阶段1：角色识别

采样前 3 章文本，调 LLM 提取全局角色档案（ID、姓名、性别、年龄、性格、关系网）。角色 ID 格式：`序号+性别字母`（如 `1M` = 第一个出场的男性，`2F` = 第二个出场的女性）。

#### `summary.py` — 阶段2：章节摘要

逐章生成 2-3 句摘要，注入角色档案 + 前章摘要作为滑动窗口上下文。

#### `chapter_processor.py` — 阶段3+4：分场+节拍（合并调用）

一次 LLM 调用完成两个任务，避免分步调用导致的跨场重复问题：

1. 按地点/时间变化切分场次
2. 为每场提取按时间排列的节拍序列（action / dialogue / transition）

#### `assembler.py` — 阶段5：组装

将中间结果（角色 dict、章节数据 dict）转换为 Pydantic `Screenplay` 对象。自动分配三幕结构，处理非法 beat 类型的静默跳过。

> **注：** `scene.py` 和 `dialogue.py` 是早期分步版本的实现，流水线已不再使用，替换为 `chapter_processor.py` 合并方案。

---

### 7. `src/web/app.py` — Gradio Web UI

| 功能         | 说明                                 |
| ------------ | ------------------------------------ |
| 文件上传     | 支持 EPUB / TXT / MD                 |
| 模型选择     | DeepSeek / OpenAI / Claude / Ollama  |
| YAML 编辑器  | 转换后可直接修改                     |
| 错误标注视图 | 校验不通过时显示带红色箭头的行号定位 |
| 校验         | 手动触发行级错误定位                 |
| 保存并导出   | 修改后保存并下载                     |

**依赖第三方库：** `gradio` (Web UI 框架)

---

## 第三方库清单

| 库                 | 用途                 | 使用的模块 / 函数                                                      |
| ------------------ | -------------------- | ---------------------------------------------------------------------- |
| **pydantic**       | 数据模型校验与序列化 | `BaseModel`, `Field`, `StringConstraints` — 全部 Schema 类             |
| **pyyaml**         | YAML 读写            | `yaml.safe_load`, `yaml.dump` — validator                              |
| **typer**          | CLI 框架             | `typer.Typer`, `typer.Argument`, `typer.Option` — cli                  |
| **rich**           | 彩色终端输出         | `rich.console.Console` — cli                                           |
| **gradio**         | Web UI               | `gr.Blocks`, `gr.File`, `gr.Code`, `gr.HTML`, `gr.Button` — web        |
| **ebooklib**       | EPUB 解析            | `epub.read_epub`, `ITEM_DOCUMENT` — parser/epub                        |
| **beautifulsoup4** | HTML 清洗            | `BeautifulSoup` — parser/epub                                          |
| **lxml**           | HTML/XML 解析引擎    | BeautifulSoup 底层 — parser/epub                                       |
| **openai**         | OpenAI API 调用      | `OpenAI` client — llm/openai_adapter                                   |
| **anthropic**      | Claude API 调用      | `Anthropic` client — llm/claude_adapter                                |
| **ollama**         | 本地模型调用         | `Client` — llm/ollama_adapter                                          |
| **tiktoken**       | Token 计数           | `tiktoken.encoding_for_model` — llm/openai_adapter, llm/claude_adapter |
| **python-dotenv**  | 环境变量加载         | `load_dotenv` — config                                                 |

开发工具（可选）：

| 库         | 用途             |
| ---------- | ---------------- |
| **pytest** | 测试框架         |
| **ruff**   | 代码检查与格式化 |
| **mypy**   | 静态类型检查     |

---

## Schema 设计

详细 YAML Schema 说明见 [schema_doc.md](schema_doc.md)。核心设计：

- **角色 ID** — `序号+性别`，如 `1M`、`2F`，各自独立编号，关系和对白均以此引用
- **Beat 为单一有序列表** — 保留动作/对白/转场的时间顺序
- **三幕结构** — 章节按比例自动分配
- **每层有 notes** — 给 AI 和人工编辑留空间

---

## 环境变量

| 变量                | 说明             | 默认值                   |
| ------------------- | ---------------- | ------------------------ |
| `N2S_LLM_PROVIDER`  | 默认 LLM 提供商  | `deepseek`               |
| `DEEPSEEK_API_KEY`  | DeepSeek API Key | —                        |
| `DEEPSEEK_MODEL`    | DeepSeek 模型名  | `deepseek-chat`          |
| `OPENAI_API_KEY`    | OpenAI API Key   | —                        |
| `ANTHROPIC_API_KEY` | Claude API Key   | —                        |
| `OLLAMA_HOST`       | Ollama 服务地址  | `http://localhost:11434` |
| `N2S_OUTPUT_DIR`    | 输出目录         | `output`                 |

---

## 使用示例

```bash
# CLI 转换       文本名称 -o 输出文件名 -t 标题
python -m src.cli convert test_novel.txt -o output/觉醒.yaml --title "觉醒"

# 指定章节范围
python -m src.cli convert 小说.txt -o output.yaml -c 1-5

# 使用 OpenAI
python -m src.cli convert 小说.txt -o output.yaml -m openai

# 使用 Claude
python -m src.cli convert 小说.txt -o output.yaml -m claude

# 使用 deepseek
python -m src.cli convert 小说.txt -o output.yaml -m deepseek

# 使用 Ollama(本地运行大模型)
python -m src.cli convert 小说.txt -o output.yaml -m ollama

# 校验已有 YAML
python -m src.cli validate output/觉醒.yaml

# 启动 Web UI
python -m src.cli launch

# 指定端口启动Wed UI
python -m src.cli launch --port 8080
```
