#!/usr/bin/env python3
"""
GitLab MR 自动代码评审机器人

功能：
1. 获取 MR 的代码变更
2. 调用 Claude API 进行代码评审
3. 将评审结果作为评论发布到 MR

使用方法：
    python review_bot.py [--config CONFIG_PATH] [--dry-run]
"""

import os
import sys
import json
import argparse
import subprocess
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import requests


@dataclass
class ReviewComment:
    """评审评论数据结构"""
    path: str
    side: str  # "left" or "right"
    from_line: int
    to_line: int
    note: str
    severity: str = "info"  # info, warning, error


class GitLabClient:
    """GitLab API 客户端"""

    def __init__(self, gitlab_url: str, token: str, project_id: str):
        self.gitlab_url = gitlab_url.rstrip('/')
        self.token = token
        self.project_id = project_id
        self.headers = {"PRIVATE-TOKEN": token}

    def get_mr_info(self, mr_iid: int) -> Dict[str, Any]:
        """获取 MR 基本信息"""
        url = f"{self.gitlab_url}/api/v4/projects/{self.project_id}/merge_requests/{mr_iid}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_mr_changes(self, mr_iid: int) -> Dict[str, Any]:
        """获取 MR 代码变更"""
        url = f"{self.gitlab_url}/api/v4/projects/{self.project_id}/merge_requests/{mr_iid}/changes"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_mr_diffs(self, mr_iid: int) -> List[Dict[str, Any]]:
        """获取 MR diff 列表"""
        changes = self.get_mr_changes(mr_iid)
        return changes.get("changes", [])

    def post_comment(self, mr_iid: int, body: str) -> Dict[str, Any]:
        """发布 MR 评论"""
        url = f"{self.gitlab_url}/api/v4/projects/{self.project_id}/merge_requests/{mr_iid}/notes"
        response = requests.post(
            url,
            headers=self.headers,
            json={"body": body}
        )
        response.raise_for_status()
        return response.json()

    def post_diff_comment(
        self,
        mr_iid: int,
        position: Dict[str, Any],
        body: str
    ) -> Dict[str, Any]:
        """发布带位置的 diff 评论"""
        url = f"{self.gitlab_url}/api/v4/projects/{self.project_id}/merge_requests/{mr_iid}/discussions"

        payload = {
            "body": body,
            "position": {
                "base_sha": position["base_sha"],
                "head_sha": position["head_sha"],
                "start_sha": position["start_sha"],
                "position_type": "text",
                "new_path": position.get("new_path"),
                "new_line": position.get("new_line"),
                "old_path": position.get("old_path"),
                "old_line": position.get("old_line"),
            }
        }

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()


class ClaudeReviewer:
    """Claude 代码评审器"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6-20250514"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.anthropic.com/v1/messages"

    def review_changes(
        self,
        mr_title: str,
        mr_description: str,
        changes: List[Dict[str, Any]],
        max_tokens: int = 8192
    ) -> List[ReviewComment]:
        """使用 Claude 评审代码变更"""

        # 构建评审提示
        prompt = self._build_review_prompt(mr_title, mr_description, changes)

        # 调用 Claude API
        response = requests.post(
            self.api_url,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        )
        response.raise_for_status()

        # 解析响应
        result = response.json()
        content = result["content"][0]["text"]

        # 解析评论
        return self._parse_comments(content)

    def _build_review_prompt(
        self,
        mr_title: str,
        mr_description: str,
        changes: List[Dict[str, Any]]
    ) -> str:
        """构建评审提示"""

        # 格式化代码变更
        changes_text = ""
        for i, change in enumerate(changes[:20], 1):  # 限制最多 20 个文件
            old_path = change.get("old_path", "")
            new_path = change.get("new_path", "")
            diff = change.get("diff", "")

            if not diff:
                continue

            changes_text += f"""
### 文件 {i}: {new_path or old_path}
```diff
{diff[:5000]}  # 限制每个文件的 diff 长度
```
"""

        return f"""你是一位资深代码评审专家。请对以下 Merge Request 进行代码评审。

## MR 信息
- 标题: {mr_title}
- 描述: {mr_description}

## 代码变更
{changes_text}

## 评审要求
请重点检查以下方面：
1. **安全漏洞**: SQL注入、XSS、敏感信息泄露等
2. **代码缺陷**: 空指针、边界条件、逻辑错误等
3. **性能问题**: 算法复杂度、内存泄漏、资源管理等
4. **可维护性**: 代码风格、命名规范、注释完整性等

## 输出格式
请按以下格式输出评审意见，每个意见用 `<notesplit />` 分隔：

<path>文件路径</path>
<side>right</side>
<from>起始行号</from>
<to>结束行号</to>
<severity>严重程度(info/warning/error)</severity>
<note>评审意见（中文）</note>
<notesplit />

注意：
- 只输出有问题的代码，不需要对正确代码进行评论
- 如果没有发现问题，输出 "LGTM，代码看起来没问题！"
- 行号尽量准确，基于 diff 中的行号
"""

    def _parse_comments(self, content: str) -> List[ReviewComment]:
        """解析 Claude 返回的评论"""
        comments = []

        if "LGTM" in content or "没问题" in content:
            return comments

        # 按分隔符拆分
        blocks = content.split("<notesplit />")

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            try:
                comment = self._parse_single_comment(block)
                if comment:
                    comments.append(comment)
            except Exception as e:
                print(f"解析评论失败: {e}")
                continue

        return comments

    def _parse_single_comment(self, block: str) -> Optional[ReviewComment]:
        """解析单条评论"""
        import re

        def extract_tag(tag: str, text: str) -> str:
            pattern = f"<{tag}>(.*?)</{tag}>"
            match = re.search(pattern, text, re.DOTALL)
            return match.group(1).strip() if match else ""

        path = extract_tag("path", block)
        note = extract_tag("note", block)

        if not path or not note:
            return None

        from_line = int(extract_tag("from", block) or "1")
        to_line = int(extract_tag("to", block) or str(from_line))
        side = extract_tag("side", block) or "right"
        severity = extract_tag("severity", block) or "info"

        return ReviewComment(
            path=path,
            side=side,
            from_line=from_line,
            to_line=to_line,
            note=note,
            severity=severity
        )


class ReviewBot:
    """代码评审机器人"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # 初始化 GitLab 客户端
        self.gitlab = GitLabClient(
            gitlab_url=config["gitlab"]["url"],
            token=config["gitlab"]["token"],
            project_id=config["gitlab"]["project_id"]
        )

        # 初始化 Claude 评审器
        self.reviewer = ClaudeReviewer(
            api_key=config["claude"]["api_key"],
            model=config["claude"].get("model", "claude-sonnet-4-6-20250514")
        )

    def run(self, mr_iid: int, dry_run: bool = False) -> List[ReviewComment]:
        """运行代码评审"""

        print(f"开始评审 MR !{mr_iid}...")

        # 1. 获取 MR 信息
        mr_info = self.gitlab.get_mr_info(mr_iid)
        mr_title = mr_info.get("title", "")
        mr_description = mr_info.get("description", "")

        print(f"MR 标题: {mr_title}")

        # 2. 获取代码变更
        changes = self.gitlab.get_mr_diffs(mr_iid)
        print(f"变更文件数: {len(changes)}")

        # 过滤不需要评审的文件
        changes = self._filter_changes(changes)
        print(f"需要评审的文件数: {len(changes)}")

        if not changes:
            print("没有需要评审的代码变更")
            return []

        # 3. 调用 Claude 进行评审
        print("正在进行代码评审...")
        comments = self.reviewer.review_changes(
            mr_title=mr_title,
            mr_description=mr_description,
            changes=changes
        )

        print(f"发现 {len(comments)} 条评审意见")

        # 4. 发布评论
        if not dry_run:
            self._post_comments(mr_iid, comments, mr_info)
        else:
            print("[DRY RUN] 跳过发布评论")
            for comment in comments:
                print(f"  - {comment.path}:{comment.from_line} [{comment.severity}] {comment.note[:50]}...")

        return comments

    def _filter_changes(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤不需要评审的文件"""
        exclude_patterns = self.config.get("review", {}).get("exclude_patterns", [
            "*.lock",
            "*.json",
            "*.md",
            "*.txt",
            "*.yml",
            "*.yaml",
        ])

        include_extensions = self.config.get("review", {}).get("include_extensions", [
            ".py", ".java", ".js", ".ts", ".go", ".rs", ".cpp", ".c", ".h", ".cs", ".rb", ".php"
        ])

        filtered = []
        for change in changes:
            new_path = change.get("new_path", "")
            old_path = change.get("old_path", "")

            # 检查是否是删除的文件
            if not new_path:
                continue

            # 检查扩展名
            ext = os.path.splitext(new_path)[1].lower()
            if ext not in include_extensions:
                continue

            # 检查排除模式
            skip = False
            for pattern in exclude_patterns:
                if pattern.startswith("*."):
                    if new_path.endswith(pattern[1:]):
                        skip = True
                        break
            if skip:
                continue

            filtered.append(change)

        return filtered

    def _post_comments(
        self,
        mr_iid: int,
        comments: List[ReviewComment],
        mr_info: Dict[str, Any]
    ):
        """发布评审评论"""

        if not comments:
            # 没有发现问题
            self.gitlab.post_comment(
                mr_iid,
                "## 🤖 自动代码评审\n\n"
                "✅ **LGTM** - 代码评审通过，未发现明显问题。\n\n"
                "---\n"
                "*由 Claude Code Review Bot 自动生成*"
            )
            return

        # 构建汇总评论
        severity_emoji = {
            "error": "🔴",
            "warning": "🟡",
            "info": "🔵"
        }

        body = "## 🤖 自动代码评审\n\n"
        body += f"发现 **{len(comments)}** 条评审意见：\n\n"

        # 按严重程度分组
        for severity in ["error", "warning", "info"]:
            severity_comments = [c for c in comments if c.severity == severity]
            if not severity_comments:
                continue

            emoji = severity_emoji.get(severity, "🔵")
            body += f"### {emoji} {severity.upper()} ({len(severity_comments)})\n\n"

            for comment in severity_comments:
                body += f"- **`{comment.path}:{comment.from_line}`**\n"
                body += f"  {comment.note}\n\n"

        body += "---\n"
        body += "*由 Claude Code Review Bot 自动生成*"

        # 发布汇总评论
        self.gitlab.post_comment(mr_iid, body)
        print(f"已发布评审评论到 MR !{mr_iid}")


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    import yaml

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # 从环境变量加载
    return {
        "gitlab": {
            "url": os.environ.get("GITLAB_URL", "https://gitlab.com"),
            "token": os.environ.get("GITLAB_TOKEN", ""),
            "project_id": os.environ.get("PROJECT_ID", ""),
        },
        "claude": {
            "api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6-20250514"),
        },
        "review": {
            "exclude_patterns": ["*.lock", "*.json", "*.md"],
            "include_extensions": [".py", ".java", ".js", ".ts", ".go", ".rs", ".cpp", ".c", ".h"]
        }
    }


def main():
    parser = argparse.ArgumentParser(description="GitLab MR 自动代码评审机器人")
    parser.add_argument("--config", "-c", default="config.yaml", help="配置文件路径")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，不发布评论")
    parser.add_argument("--mr-iid", type=int, help="MR IID（可选，默认从环境变量获取）")
    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 获取 MR IID
    mr_iid = args.mr_iid or int(os.environ.get("MR_IID") or os.environ.get("CI_MERGE_REQUEST_IID", 0))

    if not mr_iid:
        print("错误: 未指定 MR IID，请通过 --mr-iid 参数或 MR_IID 环境变量指定")
        sys.exit(1)

    # 验证配置
    if not config["gitlab"]["token"]:
        print("错误: 未配置 GITLAB_TOKEN")
        sys.exit(1)

    if not config["claude"]["api_key"]:
        print("错误: 未配置 ANTHROPIC_API_KEY")
        sys.exit(1)

    # 运行评审
    try:
        bot = ReviewBot(config)
        comments = bot.run(mr_iid, dry_run=args.dry_run)

        # 输出结果摘要
        print("\n" + "=" * 50)
        print("评审完成!")
        print(f"  - 评审意见数: {len(comments)}")
        print(f"  - 错误: {len([c for c in comments if c.severity == 'error'])}")
        print(f"  - 警告: {len([c for c in comments if c.severity == 'warning'])}")
        print(f"  - 提示: {len([c for c in comments if c.severity == 'info'])}")
        print("=" * 50)

    except Exception as e:
        print(f"评审失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
