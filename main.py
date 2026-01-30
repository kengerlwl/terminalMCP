#!/usr/bin/env python3
"""
TerminalMCP - 终端 MCP Server + FRP 代理

使用方法:
    ./terminal-mcp --server 服务器IP --token 你的token --remote-port 9001
"""

import argparse
import signal
import sys
import time
import uuid

from frp_manager import FRPManager


def parse_args():
    parser = argparse.ArgumentParser(
        description="TerminalMCP - 终端 MCP Server + FRP 代理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    terminal-mcp --server 1.2.3.4 --token mytoken --remote-port 9001
    terminal-mcp -s 1.2.3.4 -t mytoken -r 9001 -n my-terminal
        """
    )

    parser.add_argument(
        "-s", "--server",
        required=True,
        help="FRP 服务端地址"
    )
    parser.add_argument(
        "-t", "--token",
        required=True,
        help="FRP 认证 token"
    )
    parser.add_argument(
        "-r", "--remote-port",
        type=int,
        required=True,
        help="服务端暴露的端口"
    )
    parser.add_argument(
        "-l", "--local-port",
        type=int,
        default=8001,
        help="本地 MCP Server 端口 (默认: 8001)"
    )
    parser.add_argument(
        "-n", "--name",
        default=None,
        help="FRP 隧道名称 (默认: terminal-mcp-随机)"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # 生成隧道名称
    tunnel_name = args.name or f"terminal-mcp-{uuid.uuid4().hex[:8]}"

    print("=" * 50)
    print("TerminalMCP 启动中...")
    print("=" * 50)
    print(f"FRP Server: {args.server}")
    print(f"Remote Port: {args.remote_port}")
    print(f"Local Port: {args.local_port}")
    print(f"Tunnel Name: {tunnel_name}")
    print("=" * 50)

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
        print(f"[Main] 远程访问地址: http://{args.server}:{args.remote_port}/mcp")
        print("=" * 50)

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
