# GitLab MR 自动代码评审集成方案

## 架构概述

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   GitLab MR     │────▶│  GitLab CI/CD   │────▶│   Claude Code   │
│   (触发器)       │     │   (执行器)       │     │   (评审引擎)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   MR 评论       │◀────│  GitLab API     │◀────│  评审结果       │
│   (结果展示)     │     │   (回写评论)     │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 文件结构

```
gitlab-integration/
├── README.md                    # 本文档
├── .gitlab-ci.yml               # GitLab CI 配置（放到项目根目录）
├── scripts/
│   ├── run_review.py            # 主评审脚本
│   ├── post_comment.py          # 发布评论脚本
│   └── review_bot.py            # 完整的机器人脚本
├── configs/
│   └── config.yaml              # 配置文件模板
└── docker/
    ├── Dockerfile               # Docker 镜像
    └── entrypoint.sh            # 容器入口脚本
```

## 快速开始

### 1. 准备工作

#### 1.1 创建 GitLab Access Token

1. 登录 GitLab → Settings → Access Tokens
2. 创建一个新 Token，勾选 `api` 权限
3. 保存 Token（只显示一次）

#### 1.2 配置 GitLab CI/CD Variables

在 GitLab 项目中配置以下 Variables（Settings → CI/CD → Variables）：

| Variable | 说明 | 是否保护 |
|----------|------|----------|
| `GITLAB_TOKEN` | GitLab Access Token | 是 |
| `ANTHROPIC_API_KEY` | Claude API Key | 是 |
| `REVIEW_CONFIG` | 配置文件内容（可选） | 否 |

### 2. 部署方式

#### 方式一：直接使用 GitLab CI（推荐）

将 `.gitlab-ci.yml` 放到项目根目录即可。

#### 方式二：使用 Docker Runner

```bash
# 构建镜像
cd docker
docker build -t code-review-bot .

# 推送到私有仓库
docker tag code-review-bot your-registry.com/code-review-bot
docker push your-registry.com/code-review-bot
```

#### 方式三：使用 Webhook + 独立服务

适合需要更精细控制的场景，见下方详细说明。

## 详细配置

### .gitlab-ci.yml 配置

```yaml
# .gitlab-ci.yml
stages:
  - code-review

code-review:
  stage: code-review
  image: python:3.10-slim
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  before_script:
    - apt-get update && apt-get install -y git
    - pip install --quiet anthropic requests pyyaml
  script:
    - python scripts/review_bot.py
      --project-id "$CI_PROJECT_ID"
      --mr-iid "$CI_MERGE_REQUEST_IID"
      --gitlab-url "$CI_SERVER_URL"
      --gitlab-token "$GITLAB_TOKEN"
      --anthropic-key "$ANTHROPIC_API_KEY"
      --source-branch "$CI_MERGE_REQUEST_SOURCE_BRANCH_SHA"
      --target-branch "$CI_MERGE_REQUEST_TARGET_BRANCH_SHA"
  artifacts:
    reports:
      metrics: review-metrics.txt
    expire_in: 1 week
  allow_failure: true
  timeout: 30m
```

### 配置文件模板 (config.yaml)

```yaml
# config.yaml
gitlab:
  url: "https://gitlab.your-company.com"
  # token 从环境变量读取

review:
  # 评审规则
  focus_areas:
    - security        # 安全问题
    - performance     # 性能问题
    - bugs           # 潜在 bug
    - maintainability # 可维护性

  # 排除的文件模式
  exclude_patterns:
    - "*.lock"
    - "package-lock.json"
    - "dist/**"
    - "node_modules/**"

  # 严重级别阈值（低于此级别不评论）
  severity_threshold: "medium"

  # 最大评论数量
  max_comments: 20

  # 超时设置（分钟）
  timeout: 25

output:
  # 评论格式
  format: "markdown"  # markdown 或 html

  # 是否在评论中包含代码片段
  include_code_snippet: true

  # 评论摘要
  include_summary: true
```

## API 说明

### GitLab API 端点

本项目使用以下 GitLab API：

| 端点 | 用途 |
|------|------|
| `GET /projects/:id/merge_requests/:iid/changes` | 获取 MR 变更 |
| `GET /projects/:id/merge_requests/:iid/commits` | 获取 MR 提交 |
| `POST /projects/:id/merge_requests/:iid/discussions` | 创建讨论（评论） |
| `POST /projects/:id/merge_requests/:iid/notes` | 创建普通评论 |

## 自定义配置

### 修改评审规则

编辑 `review_bot.py` 中的 prompt 模板：

```python
REVIEW_PROMPT = """
请对以下代码变更进行评审，重点关注：

1. **安全问题**：SQL注入、XSS、敏感信息泄露等
2. **代码缺陷**：逻辑错误、空指针、边界条件
3. **性能问题**：算法复杂度、资源泄漏
4. **可维护性**：命名规范、代码结构、注释

请按以下格式输出：
<path>文件路径</path>
<line>行号</line>
<severity>严重程度(critical/high/medium/low)</severity>
<message>问题描述</message>
<suggestion>改进建议</suggestion>
---
"""
```

### 配置触发条件

修改 `.gitlab-ci.yml` 中的 `rules` 部分：

```yaml
rules:
  # 仅对特定分支触发
  - if: $CI_MERGE_REQUEST_TARGET_BRANCH_NAME == "main"
  - if: $CI_MERGE_REQUEST_TARGET_BRANCH_NAME == "master"

  # 排除 WIP MR
  - if: $CI_MERGE_REQUEST_TITLE =~ /^(Draft|WIP):/
    when: never

  # 仅当代码文件变更时触发
  - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    changes:
      - "**/*.{py,java,js,ts,go,rs, cpp,c,h}"
```

## 常见问题

### Q: 如何限制只评审特定文件？

A: 在配置文件中设置 `include_patterns`：

```yaml
review:
  include_patterns:
    - "src/**/*.py"
    - "api/**/*.java"
```

### Q: 如何跳过某些 MR？

A: 在 MR 描述中添加标记：

```
[skip-review] 或 [review-skip]
```

并在脚本中添加检测逻辑。

### Q: 如何处理大型 MR？

A: 设置文件数量和行数限制：

```yaml
review:
  max_files: 50      # 最多评审 50 个文件
  max_lines: 2000    # 最多评审 2000 行
```

### Q: 如何通知特定人员？

A: 在评论中 @ 相关人员：

```python
# 获取 MR 作者和评审者
participants = get_mr_participants(project_id, mr_iid)
mention_text = " ".join([f"@{p['username']}" for p in participants])
```

## 安全建议

1. **Token 安全**：使用 GitLab CI/CD Variables，勾选 Protected 和 Masked
2. **API Key 轮换**：定期轮换 Anthropic API Key
3. **访问控制**：限制 Token 的权限范围
4. **日志脱敏**：确保日志中不包含敏感信息

## 成本估算

- Claude Opus: ~$15/百万 token
- 平均每个 MR 评审: ~5000-20000 tokens
- 预估每个 MR 成本: $0.1 - $0.3

## 联系支持

如有问题，请联系 DevOps 团队或提交 Issue。
