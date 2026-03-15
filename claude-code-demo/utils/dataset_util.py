from .model import PRDataItem
from .platform_util import detect_platform, parse_gitlab_url
import json


def get_gitrepo_pr_id(pr_url: str) -> tuple[str, str]:
    """
    Get the git repo and pr_id from the GitHub PR url
    :param pr_url: e.g. "https://github.com/gofr-dev/gofr/pull/1681"
    :return: (repo_url, pr_id)
    """
    pull_index = pr_url.find("pull")
    if pull_index <= 0:
        raise ValueError("Invalid GitHub PR url")
    repo_url = pr_url[:pull_index - 1] + ".git"
    pr_id = pr_url[pull_index + 5:]
    return repo_url, pr_id


def get_gitlab_mr_info(mr_url: str) -> tuple[str, str, str, str]:
    """
    Get the GitLab repo url, host, project path and mr_id from the GitLab MR url

    :param mr_url: e.g. "https://git.cai-inc.com/rdc/paas/base-lib/-/merge_requests/2"
    :return: (repo_url, gitlab_host, project_path, mr_id)
    """
    gitlab_host, project_path, mr_id = parse_gitlab_url(mr_url)
    repo_url = f"https://{gitlab_host}/{project_path}.git"
    return repo_url, gitlab_host, project_path, mr_id


def load_dataset(path: str) -> list[PRDataItem]:
    """
    Load the dataset from the given path
    :param path: the path to the dataset
    """
    with open(path, "r", encoding="utf-8") as f:
        return [PRDataItem(**item) for item in json.load(f)]
