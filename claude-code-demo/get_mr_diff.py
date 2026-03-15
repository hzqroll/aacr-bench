#!/usr/bin/env python3
"""
获取 GitLab MR 的 diff 信息并输出到文件
（用于外部运行 Claude Code 代码评审）
"""
import json
import os
from urllib.parse import quote
import requests

# 配置
GITLAB_URL = "https://git.cai-inc.com/rdc/paas/shareservice/expert-server/-/merge_requests/139"
TOKEN = "drNKaSCybwitqzZs2GiR"
SOURCE_COMMIT = "c507aea7f967359e1682e23f8f6144f25270b51b"
TARGET_COMMIT = "e44958bfa26f835add77a3f7bdfa092bd15895d4"

def parse_gitlab_url(url):
    """解析 GitLab MR URL"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.netloc
    parts = url.split("/-/merge_requests/")
    project_path = parts[0].replace(f"https://{host}/", "").replace(f"http://{host}/", "")
    mr_id = parts[1].split("/")[0].split("?")[0]
    return host, project_path, mr_id

def get_mr_info(host, project_path, mr_id, token):
    """获取 MR 信息"""
    encoded_path = quote(project_path, safe='')
    url = f"https://{host}/api/v4/projects/{encoded_path}/merge_requests/{mr_id}"
    headers = {"PRIVATE-TOKEN": token}
    response = requests.get(url, headers=headers, timeout=30)
    return response.json()

def get_mr_diff(host, project_path, mr_id, token):
    """获取 MR diff"""
    encoded_path = quote(project_path, safe='')
    url = f"https://{host}/api/v4/projects/{encoded_path}/merge_requests/{mr_id}/diffs"
    headers = {"PRIVATE-TOKEN": token}
    response = requests.get(url, headers=headers, timeout=60)
    return response.json()

def get_mr_changes(host, project_path, mr_id, token):
    """获取 MR 变更详情"""
    encoded_path = quote(project_path, safe='')
    url = f"https://{host}/api/v4/projects/{encoded_path}/merge_requests/{mr_id}/changes"
    headers = {"PRIVATE-TOKEN": token}
    response = requests.get(url, headers=headers, timeout=60)
    return response.json()

def main():
    print("=" * 60)
    print("GitLab MR 信息获取")
    print("=" * 60)

    # 解析 URL
    parts = GITLAB_URL.split("/-/merge_requests/")
    from urllib.parse import urlparse
    parsed = urlparse(GITLAB_URL)
    host = parsed.netloc
    project_path = parts[0].replace(f"https://{host}/", "")
    mr_id = parts[1].split("/")[0].split("?")[0]

    print(f"\n📦 主机: {host}")
    print(f"📁 项目: {project_path}")
    print(f"🔀 MR ID: {mr_id}")

    # 获取 MR 信息
    print("\n📋 获取 MR 信息...")
    mr_info = get_mr_info(host, project_path, mr_id, TOKEN)
    print(f"   标题: {mr_info.get('title')}")
    print(f"   状态: {mr_info.get('state')}")
    print(f"   作者: {mr_info.get('author', {}).get('username')}")

    # 获取变更
    print("\n📝 获取变更详情...")
    changes_info = get_mr_changes(host, project_path, mr_id, TOKEN)
    changes = changes_info.get('changes', [])

    # 构建输出
    output_lines = []
    output_lines.append("=" * 80)
    output_lines.append("GitLab MR 代码评审请求")
    output_lines.append("=" * 80)
    output_lines.append(f"\n## MR 信息\n")
    output_lines.append(f"- **URL**: {GITLAB_URL}")
    output_lines.append(f"- **标题**: {mr_info.get('title')}")
    output_lines.append(f"- **描述**: {mr_info.get('description') or '(无)'}")
    output_lines.append(f"- **源分支**: {mr_info.get('source_branch')}")
    output_lines.append(f"- **目标分支**: {mr_info.get('target_branch')}")
    output_lines.append(f"- **Source Commit**: {SOURCE_COMMIT}")
    output_lines.append(f"- **Target Commit**: {TARGET_COMMIT}")
    output_lines.append(f"\n## 变更文件 ({len(changes)} 个)\n")

    for i, change in enumerate(changes, 1):
        old_path = change.get('old_path', '')
        new_path = change.get('new_path', '')
        is_new = change.get('new_file', False)
        is_deleted = change.get('deleted_file', False)
        is_renamed = change.get('renamed_file', False)

        if is_new:
            status = "🟢 新增"
        elif is_deleted:
            status = "🔴 删除"
        elif is_renamed:
            status = "📝 重命名"
        else:
            status = "✏️ 修改"

        output_lines.append(f"{i}. {status} `{new_path}`")

        # 添加 diff
        diff = change.get('diff', '')
        if diff:
            output_lines.append(f"\n```diff\n{diff}\n```\n")

    # 保存到文件
    output_file = "mr_review_request.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"\n✅ 输出已保存到: {output_file}")
    print(f"   文件大小: {os.path.getsize(output_file)} 字节")

    # 同时保存 JSON 格式
    json_file = "mr_changes.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump({
            "mr_info": mr_info,
            "changes": changes,
            "source_commit": SOURCE_COMMIT,
            "target_commit": TARGET_COMMIT
        }, f, indent=2, ensure_ascii=False)

    print(f"✅ JSON 数据已保存到: {json_file}")

    print("\n" + "=" * 60)
    print("🎉 完成！")
    print("=" * 60)
    print(f"\n你现在可以运行以下命令进行代码评审：")
    print(f"  cd /Users/roll/code/github/aacr-bench/repos/expert-server")
    print(f"  claude \"请对 {SOURCE_COMMIT}...{TARGET_COMMIT} 的变更进行代码评审\"")

if __name__ == "__main__":
    main()
