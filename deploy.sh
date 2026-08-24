#!/bin/bash
# =============================================
# 配网调度业务量智能预测系统 - 一键部署脚本
# =============================================
# 使用方法：
#   chmod +x deploy.sh
#   ./deploy.sh [选项]
#
# 选项：
#   build     - 仅构建镜像
#   start     - 启动服务
#   stop      - 停止服务
#   restart   - 重启服务
#   logs      - 查看日志
#   test      - 测试模式启动
#   full      - 完整部署（构建 + 启动）
# =============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose 未安装"
        exit 1
    fi
    
    # 检查 Oracle Instant Client
    if [ ! -f "instantclient-basic-linux.x64-23.26.3.0.0.zip" ] && [ ! -f "instantclient-basiclite-linux.x64-19.21.0.0.0dbru.zip" ]; then
        print_warning "Oracle Instant Client 文件未找到"
        print_warning "请下载并放到项目根目录："
        print_warning "  https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html"
    else
        print_success "Oracle Instant Client 文件已就绪"
    fi
    
    # 检查 .env 文件
    if [ ! -f ".env" ]; then
        print_warning ".env 文件不存在，从 .env.example 复制..."
        cp .env.example .env
        print_warning "请编辑 .env 文件配置你的环境"
    else
        print_success ".env 文件已存在"
    fi
    
    # 检查模型配置
    if [ -f "config/agent_llm_config.json" ]; then
        MODEL=$(grep -o '"model": *"[^"]*"' config/agent_llm_config.json | head -1 | cut -d'"' -f4)
        print_info "当前模型配置：$MODEL"
    fi
}

# 构建镜像
build_image() {
    print_info "构建 Docker 镜像..."
    
    if docker compose version &> /dev/null; then
        docker compose build dispatch-app
    else
        docker-compose build dispatch-app
    fi
    
    print_success "镜像构建完成"
}

# 启动服务
start_service() {
    print_info "启动服务..."
    
    if docker compose version &> /dev/null; then
        docker compose up -d dispatch-app
    else
        docker-compose up -d dispatch-app
    fi
    
    print_success "服务已启动"
    print_info "访问地址：http://localhost:5000"
}

# 启动测试模式
start_test() {
    print_info "启动测试模式（假数据）..."
    
    if docker compose version &> /dev/null; then
        docker compose up -d dispatch-app-test
    else
        docker-compose up -d dispatch-app-test
    fi
    
    print_success "测试服务已启动"
    print_info "访问地址：http://localhost:5001"
}

# 停止服务
stop_service() {
    print_info "停止服务..."
    
    if docker compose version &> /dev/null; then
        docker compose down
    else
        docker-compose down
    fi
    
    print_success "服务已停止"
}

# 重启服务
restart_service() {
    print_info "重启服务..."
    
    if docker compose version &> /dev/null; then
        docker compose restart dispatch-app
    else
        docker-compose restart dispatch-app
    fi
    
    print_success "服务已重启"
}

# 查看日志
view_logs() {
    print_info "查看日志（Ctrl+C 退出）..."
    
    if docker compose version &> /dev/null; then
        docker compose logs -f dispatch-app
    else
        docker-compose logs -f dispatch-app
    fi
}

# 健康检查
health_check() {
    print_info "等待服务启动..."
    sleep 5
    
    # 检查容器状态
    if docker ps | grep -q "dispatch-app"; then
        print_success "容器运行正常"
    else
        print_error "容器未运行"
        exit 1
    fi
    
    # 检查端口
    if curl -s http://localhost:5000 > /dev/null; then
        print_success "服务响应正常"
    else
        print_warning "服务可能还在启动中，请稍后访问"
    fi
    
    # 显示访问地址
    echo ""
    print_success "========================================="
    print_success "部署完成！"
    print_success "========================================="
    print_info "访问地址：http://localhost:5000"
    print_info "查看日志：docker compose logs -f dispatch-app"
    print_info "停止服务：docker compose down"
    echo ""
}

# 显示帮助
show_help() {
    echo "配网调度业务量智能预测系统 - 部署工具"
    echo ""
    echo "使用方法：$0 [选项]"
    echo ""
    echo "选项："
    echo "  build     - 仅构建镜像"
    echo "  start     - 启动服务（生产模式）"
    echo "  stop      - 停止服务"
    echo "  restart   - 重启服务"
    echo "  logs      - 查看日志"
    echo "  test      - 测试模式启动（假数据）"
    echo "  full      - 完整部署（构建 + 启动 + 健康检查）"
    echo "  help      - 显示此帮助"
    echo ""
    echo "示例："
    echo "  $0 full      # 完整部署"
    echo "  $0 test      # 测试模式"
    echo "  $0 logs      # 查看日志"
}

# 主函数
main() {
    case "${1:-full}" in
        build)
            check_dependencies
            build_image
            ;;
        start)
            check_dependencies
            start_service
            health_check
            ;;
        stop)
            stop_service
            ;;
        restart)
            check_dependencies
            restart_service
            health_check
            ;;
        logs)
            view_logs
            ;;
        test)
            check_dependencies
            start_test
            health_check
            ;;
        full)
            check_dependencies
            build_image
            start_service
            health_check
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知选项：$1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
