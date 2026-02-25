import os
import platform
import shlex
import socket
import subprocess
from typing import Dict, List, Optional, Union

from fastmcp import FastMCP


def get_system_info() -> dict:
    """获取系统信息"""
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "hostname": socket.gethostname(),
        "user": os.environ.get("USER") or os.environ.get("USERNAME", "unknown"),
    }

    # 获取 shell 信息
    if platform.system() == "Windows":
        info["shell"] = "cmd.exe / PowerShell"
    else:
        info["shell"] = os.environ.get("SHELL", "/bin/sh")

    return info


# 获取系统信息
SYSTEM_INFO = get_system_info()

# 动态生成描述
SERVER_DESCRIPTION = f"""TerminalMCP - Remote Terminal Access
System: {SYSTEM_INFO['os']} ({SYSTEM_INFO['machine']})
Host: {SYSTEM_INFO['hostname']}
User: {SYSTEM_INFO['user']}
Shell: {SYSTEM_INFO['shell']}"""

# 创建 MCP Server 实例
mcp = FastMCP("TerminalMCP", instructions=SERVER_DESCRIPTION)


# 动态生成工具描述
RUN_TERMINAL_DESC = f"""执行终端命令

【系统环境】
- 操作系统: {SYSTEM_INFO['os']} {SYSTEM_INFO['os_version'][:30]}...
- 主机名: {SYSTEM_INFO['hostname']}
- 用户: {SYSTEM_INFO['user']}
- Shell: {SYSTEM_INFO['shell']}

【注意事项】
- Windows 系统请使用: cmd /c <command> 或 powershell -Command "<command>"
- Linux/Mac 直接执行命令即可

Args:
    command: 要执行的shell命令
    timeout: 命令超时时间(秒)，默认30秒

Returns:
    包含执行结果的字典
"""


@mcp.tool(description=RUN_TERMINAL_DESC)
def run_terminal(command: str, timeout: int = 30) -> Dict[str, Union[str, int]]:
    try:
        args = shlex.split(command)
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        return {
            "status": "success",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": f"Command timed out after {timeout} seconds"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


LIST_FILES_DESC = f"""列出指定目录中的文件和目录

【系统环境】{SYSTEM_INFO['os']} @ {SYSTEM_INFO['hostname']}

Args:
    path: 要列出内容的目录路径，默认为当前目录

Returns:
    包含文件和目录列表的字典
"""


@mcp.tool(description=LIST_FILES_DESC)
def list_files(path: str = ".") -> Dict[str, Union[str, List[str]]]:
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["cmd", "/c", "dir", path],
                capture_output=True,
                text=True
            )
        else:
            result = subprocess.run(
                ["ls", "-la", path],
                capture_output=True,
                text=True
            )

        if result.returncode == 0:
            return {
                "status": "success",
                "output": result.stdout.splitlines()
            }
        else:
            return {
                "status": "error",
                "error": result.stderr
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


READ_FILE_DESC = f"""读取文件内容

【系统环境】{SYSTEM_INFO['os']} @ {SYSTEM_INFO['hostname']}

Args:
    file_path: 要读取的文件路径
    max_lines: 最大读取行数，默认读取全部

Returns:
    包含文件内容的字典
"""


@mcp.tool(description=READ_FILE_DESC)
def read_file(file_path: str, max_lines: Optional[int] = None) -> Dict[str, str]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if max_lines:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)
                content = ''.join(lines)
            else:
                content = f.read()

            return {
                "status": "success",
                "content": content
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def start_server(host: str = "0.0.0.0", port: int = 8001):
    """启动 MCP Server"""
    mcp.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    start_server()

