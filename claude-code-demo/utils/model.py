from pydantic import BaseModel
from typing import Optional


class Comment(BaseModel):
    is_ai_comment: bool
    note: str
    path: str
    side: str
    source_model: str
    from_line: int
    to_line: int
    category: str
    context: str


class PRDataItem(BaseModel):
    change_line_count: int
    category: str
    project_main_language: str
    source_commit: str
    target_commit: str
    githubPrUrl: Optional[str] = None  # GitHub PR URL（保持兼容）
    gitlabMrUrl: Optional[str] = None  # GitLab MR URL（新增）
    comments: list[Comment]
    finish: Optional[bool] = False

    def get_pr_url(self) -> str:
        """
        获取有效的 PR/MR URL

        :return: GitHub PR URL 或 GitLab MR URL
        :raises ValueError: 两个字段都为空
        """
        if self.githubPrUrl:
            return self.githubPrUrl
        if self.gitlabMrUrl:
            return self.gitlabMrUrl
        raise ValueError("数据项缺少 githubPrUrl 或 gitlabMrUrl")
