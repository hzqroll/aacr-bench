# GitLab MR 代码评审机器人 Docker 镜像
# 基于 Python 3.11

FROM python:3.11-slim

LABEL maintainer="DevOps Team"
LABEL description="GitLab MR Auto Code Review Bot"
LABEL version="1.0.0"

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY scripts/ ./scripts/
COPY configs/ ./configs/

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 入口点
ENTRYPOINT ["python", "scripts/review_bot.py"]
CMD ["--help"]
