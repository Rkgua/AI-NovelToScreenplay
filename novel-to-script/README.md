# Novel2Script — AI 辅助小说转剧本工具

## 简介

将 3 章以上小说（EPUB / TXT / Markdown）自动转换为结构化 YAML 剧本(注:角色识别只采样前 3 章来提取角色档案（避免 token 浪费）),即用提示词驱 LLM 把小说文本结构化，再按 Schema 规范输出为 YAML 剧本，前端提供可编辑、可校验、可自定义的交互界面

### 主分支
基于AI LLM 模型转换，基于用户输入的文本生成结构化 YAML 剧本,使用gradioWedUI进行可视化(后被HTML代替),支持CLI + 页面两种操作模式

### 开发分支PR

#### 1. UserProcessBetter 用户编辑优化

在主分支基础上添加模仿编译器报错板块,旨在为在用户编辑校验后提供错误提示,方便用户编辑

#### 功能描述

(前端换用了html页面)添加报错模块,用户编辑后点击校验,会有基本报错提示展示在在输出部分的右上侧偏下方
#### 实现思路

#### 2. AddTimeline 时间线

在主分支基础上添加时间轴功能,方便用户快速预览剧本结构,支持鼠标查看具体相关以及基本修改

#### 功能描述

会在YAML预览板块的左侧生成基于beat的时间线卡片,包含幕,场次,也在头部添加了元信息,人物全介绍,方便用户快速确认YAML生成的大纲,
1. 提供了基本的修改功能如人物对话等
2. 鼠标浮动相关人物卡片上会展示相关人物心理描写(如果llm提取出来存在的话)
3. Summary总结描述即灰色子块可以点击展示当前场景的heading(location_type,location,time)属性
4. 支持点击后提示用户当前summary的行号会在预览板块右下角有提示,方便用户确认summary位置以及方便用户进行修改

#### 实现思路

#### 3. SchemaSetting

在主分支基础上添加YAML Schema设置功能,可选展示YAML的重要的属性(用户觉得必要检查的部分),方便用户快速查看YAMLshuxux结构属性,快速完成初稿的检查
#### 功能描述
在右上角添加了一个设置按钮,点击展示YAMLSchema结构属性,可以了解YAML结构的属性,也可以自定义属性(要求属性名为英文)+描述属性的文字
补充:相当于给看不懂代码的用户提供了一个简单的YAML属性展示方式
#### 实现思路



#### 4.批量操作

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

## 项目结构




























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
