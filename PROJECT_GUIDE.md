# AACR-Bench 项目介绍与使用手册

## 目录

- [项目概述](#项目概述)
- [核心特性](#核心特性)
- [项目结构](#项目结构)
- [环境准备](#环境准备)
- [快速开始](#快速开始)
- [详细使用指南](#详细使用指南)
- [配置说明](#配置说明)
- [评测指标](#评测指标)
- [常见问题](#常见问题)

---

## 项目概述

AACR-Bench 是**业界首个多语言、仓库级上下文感知的代码评审评测数据集**，由阿里巴巴团队开发并开源。该项目旨在评估大语言模型（LLM）在自动代码评审任务中的表现。

### 核心价值

| 维度 | 数据 |
|------|------|
| Pull Requests | 200 个 |
| 编程语言 | 10 种 |
| 源项目 | 50 个 |
| 评审意见 | 2,145 条 |

### 支持的编程语言

- **系统级语言**：C++, Rust, Go
- **企业级语言**：Java, C#, TypeScript
- **脚本语言**：Python, JavaScript, Ruby, PHP

---

## 核心特性

### 1. 多语言覆盖
覆盖 10 种主流编程语言，支持跨语言性能对比和泛化能力评估。

### 2. 仓库级上下文
- 保留完整项目结构
- 支持跨文件引用和模块间交互分析
- 包含 PR 元数据（描述、标题、评论等）

### 3. 高质量标注
- **80+** 位资深软件工程师参与标注
- 三轮标注交叉验证
- LLM 智能增强标注

### 4. 多维度评测
- **多语言评测**：识别模型在不同语言上的强弱项
- **定位精度评测**：行级别的问题定位能力
- **问题分类评测**：安全漏洞/代码缺陷/可维护性/性能问题
- **上下文理解评测**：Diff级/File级/Repo级

---

## 项目结构

```
aacr-bench/
├── README.md                    # 英文项目说明
├── README.zh-CN.md              # 中文项目说明
├── CODE_REVIEW.md               # 代码评审报告示例
├── requirements.txt             # Python 依赖
├── LICENSE                      # Apache 2.0 许可证
│
├── claude-code-demo/            # Claude Code 代码评审示例
│   ├── main.py                  # 主程序入口
│   ├── get_mr_diff.py           # GitLab MR diff 获取工具
│   ├── test_gitlab_review.py    # GitLab 评审测试脚本
│   ├── configs/
│   │   └── config.json          # 配置文件
│   ├── utils/
│   │   ├── claude_code_util.py  # Claude Code 工具函数
│   │   ├── git_util.py          # Git 操作工具
│   │   ├── gitlab_util.py       # GitLab API 工具
│   │   ├── dataset_util.py      # 数据集加载工具
│   │   ├── constants_util.py    # 常量定义
│   │   ├── model.py             # 数据模型
│   │   └── platform_util.py     # 平台检测工具
│   ├── .claude/agents/
│   │   └── code-reviewer.md     # 代码审查 Agent 配置
│   └── comments/                # 审查结果存储目录
│
├── evaluator_runner/            # 评测框架
│   ├── __init__.py              # 模块导出
│   ├── example_test.py          # 批量评测示例
│   ├── core/
│   │   ├── evaluator.py         # 核心评估逻辑
│   │   ├── match_location.py    # 位置匹配逻辑
│   │   ├── match_llm.py         # LLM 语义匹配
│   │   └── match_embedding.py   # Embedding 语义匹配
│   └── utils/
│       ├── config.py            # 配置类
│       └── .env                 # 环境变量
│
├── dataset/                     # 数据集目录
├── docs/                        # 文档目录
└── imgs/                        # 图片资源
```

---

## 环境准备

### 系统要求

- Python 3.8+
- Git 2.0+
- 足够的磁盘空间（用于克隆仓库）

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/alibaba/aacr-bench.git
cd aacr-bench

# 安装 Python 依赖
pip install -r requirements.txt
```

### 依赖包列表

```
claude-agent-sdk    # Claude Agent SDK
anyio               # 异步 IO
tqdm                # 进度条
openai              # OpenAI API（用于评测）
python-dotenv       # 环境变量管理
```

---

## 快速开始

### 第一步：配置 Claude CLI

编辑 `claude-code-demo/configs/config.json`：

```json
{
  "cli_path": "/path/to/claude",
  "data_path": "/path/to/positive_samples.json",
  "gitlab_token": "your_gitlab_token(optional)"
}
```

### 第二步：配置评测环境

在 `evaluator_runner/utils/` 目录下创建 `.env` 文件：

```env
LLM_MODEL_URL="your_llm_model_url"
LLM_MODEL="your_llm_model"
LLM_API_KEY="your_llm_api_key"

EMBEDDING_MODEL_URL="your_embedding_model_url"
EMBEDDING_MODEL="your_embedding_model"
EMBEDDING_API_KEY="your_embedding_api_key"
```

### 第三步：准备数据集

```python
# 首次运行时，在 main.py 中取消注释并执行
if __name__ == "__main__":
    load_data_as_task()  # 生成任务文件 tmp_data.json
```

### 第四步：运行代码评审

```bash
cd claude-code-demo
python main.py
```

### 第五步：运行评测

```bash
python evaluator_runner/example_test.py
```

---

## 详细使用指南

### 1. 代码评审流程

#### GitHub PR 评审

```python
from main import run_claude_code

# 对 GitHub PR 进行代码评审
run_claude_code(
    pr_url="https://github.com/owner/repo/pull/123",
    source="abc123...",  # 源 commit
    target="def456..."   # 目标 commit
)
```

#### GitLab MR 评审

```python
from main import run_claude_code

# 对 GitLab MR 进行代码评审
run_claude_code(
    pr_url="https://gitlab.com/owner/repo/-/merge_requests/456",
    source="abc123...",
    target="def456..."
)
```

### 2. 评测流程

#### 单个 PR 评测

```python
import asyncio
from evaluator_runner import (
    get_evaluator_ans_from_json,
    load_generated_comments_from_file,
    EvaluatorConfig
)

async def evaluate_single_pr():
    # 加载 AI 生成的评论
    comments = load_generated_comments_from_file("comments/repo_123.txt")

    # 加载参考评论
    reference_comments = [...]  # 从 positive_samples.json 加载

    # 运行评测
    result = await get_evaluator_ans_from_json(
        github_pr_url="https://github.com/owner/repo/pull/123",
        generated_comments=comments,
        good_comments=reference_comments
    )

    print(f"位置匹配率: {result['positive_line_match_rate']}")
    print(f"语义匹配率: {result['positive_match_rate']}")

asyncio.run(evaluate_single_pr())
```

#### 批量评测

编辑 `evaluator_runner/example_test.py` 配置区：

```python
# 输入/输出设置
INPUT_DIR = "./comments"              # 评论文件目录
OUTPUT_FILE = "./results.json"        # 输出文件
REFERENCE_DATA_FILE = "./positive_samples.json"  # 参考数据

# 评测设置
LINE_DISTANCE_THRESHOLD = 1           # 行号匹配阈值
ENABLE_SEMANTIC_MATCH = True          # 启用语义匹配
SEMANTIC_MATCHER_TYPE = "llm"         # 使用 LLM 匹配
```

运行批量评测：

```bash
python evaluator_runner/example_test.py
```

### 3. 自定义代码审查规则

编辑 `.claude/agents/code-reviewer.md` 文件来自定义审查行为：

```markdown
# 代码审查 Agent

## 审查重点
- 安全性：SQL注入、XSS、敏感信息泄露
- 性能：算法复杂度、内存泄漏、资源管理
- 可维护性：代码风格、命名规范、注释完整性

## 输出格式
<path>文件路径</path>
<side>right/left</side>
<from>起始行</from>
<to>结束行</to>
<note>评审意见</note>
<notesplit />
```

---

## 配置说明

### config.json 配置项

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cli_path` | string | 是 | Claude CLI 安装路径 |
| `data_path` | string | 是 | 数据集文件路径 |
| `gitlab_token` | string | 否 | GitLab 访问令牌 |

### EvaluatorConfig 配置项

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `line_distance_threshold` | int | 1 | 行号匹配距离阈值 |
| `semantic_matcher_type` | enum | LLM | 语义匹配器类型 |
| `enable_semantic_match` | bool | True | 是否启用语义匹配 |

### 配置快捷方法

```python
from evaluator_runner import EvaluatorConfig

# 使用 Embedding 匹配器
config = EvaluatorConfig.with_embedding(line_distance_threshold=2)

# 仅位置匹配
config = EvaluatorConfig.location_only(line_distance_threshold=1)

# 带筛选条件
config = EvaluatorConfig.with_filter(
    pr_categories=["Bug Fix"],
    project_languages=["Python"],
    comment_categories=["Code Defect"]
)
```

---

## 评测指标

### 核心指标

| 指标 | 说明 | 计算公式 |
|------|------|----------|
| **准确率** (Precision) | 有效评论占比 | `有效匹配数 / 生成总数` |
| **召回率** (Recall) | 发现问题的能力 | `有效匹配数 / 数据集中有效数` |
| **行级准确率** | 定位到代码行的能力 | `行号匹配数 / 生成总数` |
| **噪声率** | 无效评论的比例 | `未匹配数 / 生成总数` |

### 评测结果示例

```json
{
    "github_pr_url": "https://github.com/owner/repo/pull/123",
    "positive_expected_nums": 10,
    "total_generated_nums": 8,
    "positive_line_match_nums": 6,
    "positive_match_nums": 5,
    "positive_line_match_rate": 0.75,
    "positive_match_rate": 0.625
}
```

---

## 数据格式

### 输入数据集格式

```json
{
  "githubPrUrl": "https://github.com/owner/repo/pull/123",
  "source_commit": "abc123...",
  "target_commit": "def456...",
  "change_line_count": 100,
  "project_main_language": "Python",
  "comments": [
    {
      "note": "评论内容",
      "path": "src/main.py",
      "side": "right",
      "from_line": 10,
      "to_line": 15,
      "category": "Code Defect",
      "context": "Diff Level"
    }
  ]
}
```

### 评论输出格式

```
<path>src/main.py</path>
<side>right</side>
<from>10</from>
<to>15</to>
<note>这里存在潜在的空指针问题</note>
<notesplit />
```

---

## 常见问题

### Q1: 如何获取 Claude CLI？

访问 [Anthropic 官网](https://www.anthropic.com/) 注册并获取 API 访问权限，然后安装 Claude CLI。

### Q2: 评测时网络超时怎么办？

程序默认在完成每个任务后等待 30 秒以避免限制。可以在 `main.py` 中调整等待时间：

```python
time.sleep(30)  # 调整此值
```

### Q3: 如何恢复中断的任务？

程序会自动跳过标记为 `finish: true` 的任务，直接重新运行即可继续。

### Q4: 支持哪些 GitLab 版本？

支持 GitLab.com 和自托管的 GitLab 实例，只需配置正确的 `gitlab_token`。

### Q5: 如何添加新的编程语言支持？

数据集本身已支持 10 种语言。如需评测新语言，只需在数据集中添加对应语言的 PR 数据。

---

## 贡献指南

1. **Fork** 本仓库
2. **创建** 特性分支 (`git checkout -b feat/xxx`)
3. **提交** 更改 (`git commit -m 'feat: xxx'`)
4. **推送** 到分支 (`git push origin feat/xxx`)
5. **创建** Pull Request

---

## 许可证

本项目采用 Apache License 2.0 许可证。

---

## 联系方式

- **GitHub Issues**: https://github.com/alibaba/aacr-bench/issues
- **HuggingFace**: https://huggingface.co/datasets/Alibaba-Aone/aacr-bench
- **论文**: https://arxiv.org/abs/2601.19494

---

*最后更新: 2026-03-16*
