import json
import os
import time

import anyio
from tqdm import tqdm
from claude_agent_sdk import query, ResultMessage
from utils.claude_code_util import get_claude_code_options, add_code_review_agent, load_config
from utils.git_util import git_clone, checkout, git_fetch, get_pr_title_desc
from utils.gitlab_util import get_mr_title_desc, get_gitlab_repo_url, checkout_gitlab_mr, set_gitlab_token
from utils.dataset_util import get_gitrepo_pr_id, get_gitlab_mr_info, load_dataset
from utils.platform_util import detect_platform
from utils.constants_util import BASE_PROMPT


task_data_path = "tmp_data.json"


def init_gitlab_token():
    """
    从配置文件初始化 GitLab Token
    """
    config = load_config()
    token = config.get("gitlab_token")
    if token:
        set_gitlab_token(token)
        print(f"GitLab Token 已配置")
    else:
        print("警告: 未配置 GitLab Token，GitLab MR API 可能无法访问")


def copy_comments(workspace: str, cp_id: str):
    """
    Copy the comments.txt from workspace
    """
    comments_path = os.path.join(workspace, "comments.txt")
    if os.path.exists(comments_path):
        with open(comments_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        print("No comments.txt found, agent doesn't post comments.")
        return
    # write comments into comments_{cp_id}.txt under main.py directory
    comments_dir = "comments"
    os.makedirs(comments_dir, exist_ok=True)
    with open(os.path.join(comments_dir, "comments_%s.txt" % cp_id), "w", encoding="utf-8") as f:
        f.write(text)


def create_agent(workspace: str):
    """
    Create the code review agent
    """
    agent_path = ".claude/agents/code-reviewer.md"
    with open(agent_path, "r", encoding="utf-8") as f:
        agent_md = f.read()
    add_code_review_agent(workspace, agent_md)


def run_claude_code(pr_url: str, source: str, target: str):
    """
    Run Claude Code - 支持 GitHub 和 GitLab
    :param pr_url: PR/MR 的 URL
    :param source: source commit
    :param target: target commit
    """
    platform = detect_platform(pr_url)
    print(f"检测到平台: {platform}")

    if platform == "github":
        return _run_github_review(pr_url, source, target)
    elif platform == "gitlab":
        return _run_gitlab_review(pr_url, source, target)
    else:
        raise ValueError(f"不支持的平台: {platform}")


def _run_github_review(pr_url: str, source: str, target: str):
    """
    GitHub PR 代码评审
    """
    git_repo, pr_id = get_gitrepo_pr_id(pr_url)
    repo = git_repo.split("/")[-1].replace(".git", "")
    full_repo = git_repo.split("/")[-2] + "/" + repo
    pull_pr = "pull/" + pr_id
    branch = "pr_" + pr_id

    # clone the repo
    workspace = git_clone(git_repo)
    checkout(workspace, pull_pr, branch)  # set the workspace to the target branch
    # fetch hidden commit
    git_fetch(workspace, "origin", source)
    git_fetch(workspace, "origin", target)
    create_agent(workspace)

    options = get_claude_code_options(workspace=workspace, allowed_tools=["Read", "Write", "Bash"])
    title, desc = get_pr_title_desc(repo=full_repo, pr_id=pr_id)

    async def call():
        async for message in query(
                prompt=BASE_PROMPT % (title, desc, source, target), options=options
        ):
            if type(message) is ResultMessage:
                print(message.result)

    anyio.run(call)
    copy_comments(workspace, repo + "_" + pr_id)


def _run_gitlab_review(mr_url: str, source: str, target: str):
    """
    GitLab MR 代码评审
    """
    repo_url, gitlab_host, project_path, mr_id = get_gitlab_mr_info(mr_url)
    repo = project_path.split("/")[-1]
    branch = "mr_" + mr_id

    # clone the repo
    workspace = git_clone(repo_url)
    checkout_gitlab_mr(workspace, mr_id, branch)  # set the workspace to the MR branch
    # fetch hidden commit
    git_fetch(workspace, "origin", source)
    git_fetch(workspace, "origin", target)
    create_agent(workspace)

    options = get_claude_code_options(workspace=workspace, allowed_tools=["Read", "Write", "Bash"])
    title, desc = get_mr_title_desc(gitlab_host=gitlab_host, project_path=project_path, mr_id=mr_id)

    async def call():
        async for message in query(
                prompt=BASE_PROMPT % (title, desc, source, target), options=options
        ):
            if type(message) is ResultMessage:
                print(message.result)

    anyio.run(call)
    # 使用项目路径中的斜杠替换为下划线，避免文件名问题
    copy_comments(workspace, project_path.replace("/", "_") + "_mr" + mr_id)


def main():
    # 初始化 GitLab Token
    init_gitlab_token()

    data_path = task_data_path
    dataset = load_dataset(data_path)
    print("load dataset done, size:", len(dataset))
    for item in tqdm(dataset):
        if item.finish:
            # skip finished task
            continue

        # 使用 get_pr_url() 方法获取 URL（支持 GitHub 和 GitLab）
        pr_url = item.get_pr_url()
        run_claude_code(pr_url, item.source_commit, item.target_commit)
        print(f"finish {pr_url}")
        item.finish = True
        # save process
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump([item.model_dump() for item in dataset], f, indent=4)
        # sleep 30s to avoid network down
        time.sleep(30)


def load_data_as_task():
    # copy raw data and add a new key::finish
    config = load_config()
    data_path = config.get("data_path")
    dataset = load_dataset(data_path)
    for item in dataset:
        item.finish = False
    # write back
    with open(task_data_path, "w", encoding="utf-8") as f:
        json.dump([item.model_dump() for item in dataset], f, indent=4)


if __name__ == "__main__":
    # load_data_as_task()  # Copy initial data as task, only when you first run the script you need to run this
    main()
