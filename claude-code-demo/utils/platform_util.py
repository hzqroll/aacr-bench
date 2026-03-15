"""
平台识别工具模块
支持自动识别 GitHub 和 GitLab URL
"""
from urllib.parse import urlparse


def detect_platform(url: str) -> str:
    """
    根据 URL 判断是 GitHub 还是 GitLab

    :param url: PR/MR 的 URL
    :return: "github" 或 "gitlab"
    :raises ValueError: 无法识别的 URL
    """
    parsed = urlparse(url)

    # GitHub: 域名是 github.com
    if "github.com" in parsed.netloc:
        return "github"

    # GitLab: 路径包含 /-/merge_requests/
    if "/-/merge_requests/" in url:
        return "gitlab"

    raise ValueError(f"无法识别的平台 URL: {url}")


def is_github_url(url: str) -> bool:
    """
    判断是否为 GitHub URL
    """
    try:
        return detect_platform(url) == "github"
    except ValueError:
        return False


def is_gitlab_url(url: str) -> bool:
    """
    判断是否为 GitLab URL
    """
    try:
        return detect_platform(url) == "gitlab"
    except ValueError:
        return False


def parse_gitlab_url(url: str) -> tuple:
    """
    解析 GitLab MR URL

    输入示例: https://git.cai-inc.com/rdc/paas/shareservice/base-library-core/-/merge_requests/2

    :param url: GitLab MR URL
    :return: (gitlab_host, project_path, mr_id)
             例如: ("git.cai-inc.com", "rdc/paas/shareservice/base-library-core", "2")
    :raises ValueError: URL 格式无效
    """
    parsed = urlparse(url)
    gitlab_host = parsed.netloc

    # 检查是否包含 /-/merge_requests/
    if "/-/merge_requests/" not in url:
        raise ValueError(f"无效的 GitLab MR URL 格式: {url}")

    # 提取项目路径和 MR 编号
    parts = url.split("/-/merge_requests/")
    if len(parts) != 2:
        raise ValueError(f"无效的 GitLab MR URL 格式: {url}")

    # 项目路径: 移除协议和域名部分
    project_path = parts[0].replace(f"https://{gitlab_host}/", "")
    project_path = project_path.replace(f"http://{gitlab_host}/", "")

    # MR 编号: 移除末尾的斜杠和查询参数
    mr_id = parts[1].split("/")[0].split("?")[0]

    if not project_path or not mr_id:
        raise ValueError(f"无法从 URL 解析项目路径或 MR 编号: {url}")

    return gitlab_host, project_path, mr_id
