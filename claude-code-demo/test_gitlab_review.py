#!/usr/bin/env python3
"""
测试 GitLab MR 代码评审
"""
import json
import os
import time

import anyio
from tqdm import tqdm
from claude_agent_sdk import query, ResultMessage

from utils.claude_code_util import get_claude_code_options, add_code_review_agent, load_config
from utils.git_util import git_clone, git_fetch
from utils.gitlab_util import get_mr_title_desc, get_gitlab_repo_url, checkout_gitlab_mr, set_gitlab_token
from utils.dataset_util import get_gitlab_mr_info, load_dataset
from utils.constants_util import BASE_PROMPT


def copy_comments(workspace: str, cp_id: str):
    """复制评审结果"""
    comments_path = os.path.join(workspace, "comments.txt")
    if os.path.exists(comments_path):
        with open(comments_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        print("未找到 comments.txt，Agent 未生成评论")
        return None

    comments_dir = "comments"
    os.makedirs(comments_dir, exist_ok=True)
    output_file = os.path.join(comments_dir, f"comments_{cp_id}.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)
    return output_file


def create_agent(workspace: str):
    """创建代码评审 Agent"""
    agent_path = ".claude/agents/code-reviewer.md"
    with open(agent_path, "r", encoding="utf-8") as f:
        agent_md = f.read()
    add_code_review_agent(workspace, agent_md)


def run_gitlab_review(mr_url: str, source: str, target: str):
    """运行 GitLab MR 代码评审"""
    print(f"\n{'='*60}")
    print(f"开始处理 GitLab MR: {mr_url}")
    print(f"{'='*60}\n")

    # 解析 MR URL
    _, gitlab_host, project_path, mr_id = get_gitlab_mr_info(mr_url)
    repo = project_path.split("/")[-1]
    branch = "mr_" + mr_id

    print(f"📦 项目: {project_path}")
    print(f"🔀 MR ID: {mr_id}")
    print(f"🌿 分支: {branch}")

    # Clone 仓库 (使用带 Token 的 URL)
    print(f"\n⬇️  克隆仓库...")
    repo_url = get_gitlab_repo_url(gitlab_host, project_path, use_ssh=False, token=None)  # 使用全局 Token
    workspace = git_clone(repo_url)
    print(f"   工作目录: {workspace}")

    # Checkout MR 分支
    print(f"\n🔄 切换到 MR 分支...")
    checkout_gitlab_mr(workspace, mr_id, branch)

    # Fetch commits
    print(f"\n📥 获取提交信息...")
    git_fetch(workspace, "origin", source)
    git_fetch(workspace, "origin", target)

    # 创建 Agent
    create_agent(workspace)

    # 获取 MR 信息
    print(f"\n📋 获取 MR 信息...")
    title, desc = get_mr_title_desc(gitlab_host=gitlab_host, project_path=project_path, mr_id=mr_id)
    print(f"   标题: {title}")
    print(f"   描述: {desc[:100]}..." if desc and len(desc) > 100 else f"   描述: {desc or '(无)'}")

    # 运行 Claude Code
    print(f"\n🤖 运行 Claude Code 进行代码评审...")
    options = get_claude_code_options(workspace=workspace, allowed_tools=["Read", "Write", "Bash"])

    async def call():
        async for message in query(
            prompt=BASE_PROMPT % (title, desc, source, target), options=options
        ):
            if type(message) is ResultMessage:
                print(f"   结果: {message.result[:200]}..." if len(str(message.result)) > 200 else f"   结果: {message.result}")

    anyio.run(call)

    # 复制评论
    print(f"\n📝 保存评审结果...")
    cp_id = project_path.replace("/", "_") + "_mr" + mr_id
    output_file = copy_comments(workspace, cp_id)

    if output_file:
        print(f"   ✅ 评审结果已保存: {output_file}")
        return output_file
    else:
        print(f"   ⚠️  未生成评审结果")
        return None


def main():
    # 初始化 GitLab Token
    config = load_config()
    token = config.get("gitlab_token")
    if token:
        set_gitlab_token(token)
        print(f"🔑 GitLab Token 已配置")

    # 加载测试数据
    data_path = "test_data.json"
    dataset = load_dataset(data_path)
    print(f"📊 加载数据集: {len(dataset)} 条")

    for item in tqdm(dataset):
        if item.finish:
            continue

        # 获取 MR URL
        mr_url = item.get_pr_url()
        output_file = run_gitlab_review(mr_url, item.source_commit, item.target_commit)

        # 标记完成
        item.finish = True
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump([item.model_dump() for item in dataset], f, indent=4, ensure_ascii=False)

        print(f"\n✅ 完成: {mr_url}")
        if output_file:
            print(f"   输出文件: {output_file}")

    print(f"\n{'='*60}")
    print("🎉 所有任务完成！")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
