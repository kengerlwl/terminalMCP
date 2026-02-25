#!/usr/bin/env python3
"""
TerminalMCP - 终端 MCP Server + FRP 代理

将本地终端能力通过 MCP 协议暴露，并通过 FRP 代理到远程服务器
"""

import argparse
import signal
import sys
import time
import uuid

from frp_manager import FRPManager

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║                     TerminalMCP v1.0                         ║
║          Terminal MCP Server + FRP Proxy Tool                ║
╚══════════════════════════════════════════════════════════════╝
"""

USAGE_GUIDE = """
================== 使用指南 ==================

【功能说明】
  本工具将你的终端能力通过 MCP 协议暴露出去，
  并通过 FRP 隧道代理到远程服务器，使 AI 助手
  可以远程执行你本地的终端命令。

【提供的 MCP Tools】
  - run_terminal    : 执行终端命令
  - list_files      : 列出目录文件
  - read_file       : 读取文件内容

【配置 AI 助手】
  在 Claude Desktop 或其他 MCP 客户端配置:

  {
    "mcpServers": {
      "remote-terminal": {
        "url": "http://<服务器IP>:<端口>/mcp"
      }
    }
  }

【安全提示】
  ⚠️  此工具会暴露你的终端执行能力，请确保:
  1. 只在受信任的网络环境中使用
  2. 使用强密码作为 FRP token
  3. 不要在生产环境中使用

==============================================
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="TerminalMCP - 终端 MCP Server + FRP 代理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
【基本用法】
  terminal-mcp --server <服务器IP> --token <TOKEN> --remote-port <端口>

【示例】
  # 最简用法
  terminal-mcp -s 1.2.3.4 -t mytoken -r 9001

  # 指定本地端口和隧道名称
  terminal-mcp -s 1.2.3.4 -t mytoken -r 9001 -l 8080 -n my-pc

【启动后】
  MCP 服务将在以下地址可用:
  http://<服务器IP>:<remote-port>/mcp

【更多信息】
  GitHub: https://github.com/kengerlwl/terminalMCP
        """
    )

    parser.add_argument(
        "-s", "--server",
        required=True,
        metavar="IP",
        help="FRP 服务端地址 (例: 1.2.3.4)"
    )
    parser.add_argument(
        "-t", "--token",
        required=True,
        metavar="TOKEN",
        help="FRP 认证 token"
    )
    parser.add_argument(
        "-r", "--remote-port",
        type=int,
        required=True,
        metavar="PORT",
        help="服务端暴露的端口 (例: 9001)"
    )
    parser.add_argument(
        "-l", "--local-port",
        type=int,
        default=8001,
        metavar="PORT",
        help="本地 MCP Server 端口 (默认: 8001)"
    )
    parser.add_argument(
        "-n", "--name",
        default=None,
        metavar="NAME",
        help="FRP 隧道名称 (默认: 自动生成)"
    )
    parser.add_argument(
        "--guide",
        action="store_true",
        help="显示详细使用指南"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # 显示使用指南
    if args.guide:
        print(BANNER)
        print(USAGE_GUIDE)
        return

    # 生成隧道名称
    tunnel_name = args.name or f"terminal-mcp-{uuid.uuid4().hex[:8]}"

    print(BANNER)
    print("【连接信息】")
    print(f"  FRP Server  : {args.server}")
    print(f"  Remote Port : {args.remote_port}")
    print(f"  Local Port  : {args.local_port}")
    print(f"  Tunnel Name : {tunnel_name}")
    print()
    print("【MCP 访问地址】")
    print(f"  http://{args.server}:{args.remote_port}/mcp")
    print()
    print("  提示: 使用 --guide 查看详细使用指南")
    print("=" * 62)

    # 创建 FRP 管理器
    frp_manager = FRPManager(
        server_addr=args.server,
        token=args.token,
        remote_port=args.remote_port,
        local_port=args.local_port,
        tunnel_name=tunnel_name
    )

    # 信号处理
    def signal_handler(sig, frame):
        print("\n[Main] 收到退出信号，正在清理...")
        frp_manager.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 1. 下载/准备 frpc
        print("\n[Main] 准备 FRP 客户端...")
        frp_manager.download_frpc()

        # 2. 生成配置
        print("\n[Main] 生成 FRP 配置...")
        frp_manager.generate_config()

        # 3. 启动 frpc (后台线程)
        print("\n[Main] 启动 FRP 客户端...")
        frp_process = frp_manager.start()

        # 等待 frpc 建立连接
        time.sleep(2)

        # 检查 frpc 是否正常运行
        if frp_process.poll() is not None:
            # frpc 已退出，打印错误
            stdout, stderr = frp_process.communicate()
            print(f"[FRP] 启动失败!")
            print(f"[FRP] stdout: {stdout}")
            print(f"[FRP] stderr: {stderr}")
            sys.exit(1)

        # 4. 启动 MCP Server (阻塞)
        print("\n[Main] 启动 MCP Server...")
        print("[Main] ✅ 服务已就绪!")
        print(f"[Main] 远程访问地址: http://{args.server}:{args.remote_port}/mcp")
        print("[Main] 按 Ctrl+C 停止服务")
        print("=" * 62)

        # 导入并启动 MCP Server
        from mcp_server import start_server
        start_server(host="0.0.0.0", port=args.local_port)

    except KeyboardInterrupt:
        print("\n[Main] 用户中断")
    except Exception as e:
        print(f"\n[Main] 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        frp_manager.cleanup()


if __name__ == "__main__":
    main()
