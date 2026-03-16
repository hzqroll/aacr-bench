#!/bin/bash
# GitLab MR 代码评审机器人快速部署脚本

set -e

echo "=========================================="
echo "  GitLab MR 自动代码评审机器人部署脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查依赖
check_dependencies() {
    echo -e "${YELLOW}检查依赖...${NC}"

    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}错误: 未安装 Python 3${NC}"
        exit 1
    fi

    if ! command -v pip3 &> /dev/null; then
        echo -e "${RED}错误: 未安装 pip${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ 依赖检查通过${NC}"
}

# 创建配置文件
create_config() {
    echo -e "${YELLOW}创建配置文件...${NC}"

    if [ ! -f "configs/config.yaml" ]; then
        cp configs/config.yaml.example configs/config.yaml
        echo -e "${GREEN}✓ 已创建 configs/config.yaml${NC}"
        echo -e "${YELLOW}请编辑 configs/config.yaml 填入实际配置${NC}"
    else
        echo -e "${GREEN}✓ 配置文件已存在${NC}"
    fi
}

# 安装 Python 依赖
install_dependencies() {
    echo -e "${YELLOW}安装 Python 依赖...${NC}"

    pip3 install -r docker/requirements.txt

    echo -e "${GREEN}✓ 依赖安装完成${NC}"
}

# 验证配置
validate_config() {
    echo -e "${YELLOW}验证配置...${NC}"

    # 检查必要的环境变量
    local missing=()

    if [ -z "$GITLAB_TOKEN" ]; then
        missing+=("GITLAB_TOKEN")
    fi

    if [ -z "$ANTHROPIC_API_KEY" ]; then
        missing+=("ANTHROPIC_API_KEY")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${RED}错误: 缺少以下环境变量:${NC}"
        for var in "${missing[@]}"; do
            echo "  - $var"
        done
        echo ""
        echo "请设置环境变量:"
        echo "  export GITLAB_TOKEN='your-gitlab-token'"
        echo "  export ANTHROPIC_API_KEY='your-anthropic-api-key'"
        exit 1
    fi

    echo -e "${GREEN}✓ 配置验证通过${NC}"
}

# 测试连接
test_connection() {
    echo -e "${YELLOW}测试 GitLab 连接...${NC}"

    if [ -z "$GITLAB_URL" ]; then
        GITLAB_URL="https://gitlab.com"
    fi

    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
        "$GITLAB_URL/api/v4/user")

    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ GitLab 连接成功${NC}"
    else
        echo -e "${RED}✗ GitLab 连接失败 (HTTP $response)${NC}"
        echo "请检查 GITLAB_URL 和 GITLAB_TOKEN 是否正确"
        exit 1
    fi
}

# 构建镜像
build_image() {
    echo -e "${YELLOW}构建 Docker 镜像...${NC}"

    docker build -t gitlab-review-bot:latest -f docker/Dockerfile .

    echo -e "${GREEN}✓ Docker 镜像构建完成${NC}"
}

# 显示帮助
show_help() {
    echo ""
    echo "使用方法:"
    echo ""
    echo "1. 设置环境变量:"
    echo "   export GITLAB_URL='https://gitlab.your-company.com'"
    echo "   export GITLAB_TOKEN='your-gitlab-access-token'"
    echo "   export ANTHROPIC_API_KEY='your-anthropic-api-key'"
    echo ""
    echo "2. 运行评审（测试模式）:"
    echo "   python scripts/review_bot.py --mr-iid 123 --dry-run"
    echo ""
    echo "3. 运行评审（正式模式）:"
    echo "   python scripts/review_bot.py --mr-iid 123"
    echo ""
    echo "4. 部署到 GitLab CI/CD:"
    echo "   cp .gitlab-ci.yml /path/to/your/project/"
    echo "   cp -r scripts/ /path/to/your/project/"
    echo ""
}

# 主函数
main() {
    check_dependencies
    create_config
    install_dependencies

    echo ""
    echo -e "${GREEN}=========================================="
    echo "  部署完成！"
    echo "==========================================${NC}"

    show_help
}

# 解析参数
case "$1" in
    --build)
        build_image
        ;;
    --test)
        validate_config
        test_connection
        ;;
    --help)
        show_help
        ;;
    *)
        main
        ;;
esac
