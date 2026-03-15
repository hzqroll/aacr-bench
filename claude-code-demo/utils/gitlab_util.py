"""
GitLab 操作工具模块
支持 GitLab MR 的 API 调用和 Git 操作
"""
import os
import subprocess
from pathlib import Path
from urllib.parse import quote

import requests

# 全局 Token，可通过 set_gitlab_token() 设置
_GITLAB_TOKEN = None


def set_gitlab_token(token: str):
    """
    设置 GitLab API Token

    :param token: GitLab Private Token 或 OAuth Token
    """
    global _GITLAB_TOKEN
    _GITLAB_TOKEN = token


def get_gitlab_token() -> str:
    """
    获取当前配置的 GitLab Token

    :return: Token 字符串，未配置则返回 None
    """
    global _GITLAB_TOKEN
    return _GITLAB_TOKEN


def get_mr_title_desc(gitlab_host: str, project_path: str, mr_id: str, token: str = None) -> tuple:
    """
    获取 GitLab MR 的标题和描述

    :param gitlab_host: GitLab 主机地址，如 "git.cai-inc.com"
    :param project_path: 项目路径，如 "rdc/paas/shareservice/base-library-core"
    :param mr_id: MR 编号
    :param token: 可选的 Token，不传则使用全局设置的 Token
    :return: (title, description)
    :raises ValueError: API 请求失败
    """
    # 使用传入的 token 或全局 token
    api_token = token or _GITLAB_TOKEN

    # URL 编码项目路径: rdc/paas/... → rdc%2Fpaas%2F...
    encoded_path = quote(project_path, safe='')
    url = f"https://{gitlab_host}/api/v4/projects/{encoded_path}/merge_requests/{mr_id}"

    # 构建请求头
    headers = {}
    if api_token:
        headers["PRIVATE-TOKEN"] = api_token

    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        raise ValueError(f"获取 MR 失败: {url}, 状态码: {response.status_code}, 响应: {response.text}")

    data = response.json()
    title = data.get("title", "")
    description = data.get("description", "") or ""

    return title, description


def get_gitlab_repo_url(gitlab_host: str, project_path: str, use_ssh: bool = False, token: str = None) -> str:
    """
    构建 GitLab 仓库的克隆 URL

    :param gitlab_host: GitLab 主机地址
    :param project_path: 项目路径
    :param use_ssh: 是否使用 SSH 协议
    :param token: 可选的 Token，用于 HTTPS 认证
    :return: Git 仓库 URL
    """
    if use_ssh:
        return f"git@{gitlab_host}:{project_path}.git"

    # 如果有 Token，嵌入到 URL 中进行认证
    if token or _GITLAB_TOKEN:
        api_token = token or _GITLAB_TOKEN
        return f"https://oauth2:{api_token}@{gitlab_host}/{project_path}.git"

    return f"https://{gitlab_host}/{project_path}.git"


def checkout_gitlab_mr(workspace: str, mr_id: str, branch: str):
    """
    Fetch 并 checkout GitLab MR

    GitLab fetch 格式: merge-requests/{id}/head:{branch}
    例如: merge-requests/2/head:mr_2

    :param workspace: 工作目录路径
    :param mr_id: MR 编号
    :param branch: 本地分支名称
    :raises RuntimeError: Git 操作失败
    """
    workspace_path = Path(workspace)
    if not workspace_path.exists():
        raise ValueError(f"工作目录不存在: {workspace}")

    git_dir = workspace_path / ".git"
    if not git_dir.exists():
        raise ValueError(f"不是 Git 仓库: {workspace}")

    original_dir = os.getcwd()

    try:
        os.chdir(workspace_path)

        # Fetch MR
        # GitLab 格式: merge-requests/2/head:mr_2
        fetch_ref = f"merge-requests/{mr_id}/head:{branch}"

        try:
            subprocess.run(
                ['git', 'fetch', 'origin', fetch_ref],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError:
            # 可能已经 fetch 过，尝试继续
            pass

        # Checkout 分支
        subprocess.run(
            ['git', 'checkout', branch],
            check=True,
            capture_output=True,
            text=True
        )

    except subprocess.CalledProcessError as e:
        error_msg = f"切换 GitLab MR 分支失败: {branch}\n"
        error_msg += f"错误: {e.stderr}\n"
        raise RuntimeError(error_msg) from e
    finally:
        os.chdir(original_dir)


def get_gitlab_project_info(gitlab_host: str, project_path: str) -> dict:
    """
    获取 GitLab 项目信息（可选功能，用于调试）

    :param gitlab_host: GitLab 主机地址
    :param project_path: 项目路径
    :return: 项目信息字典
    """
    encoded_path = quote(project_path, safe='')
    url = f"https://{gitlab_host}/api/v4/projects/{encoded_path}"

    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        raise ValueError(f"获取项目信息失败: {url}, 状态码: {response.status_code}")

    return response.json()
