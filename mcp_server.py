import shlex
import subprocess
from typing import Dict, List, Optional, Union

from fastmcp import FastMCP

# 创建 MCP Server 实例
mcp = FastMCP("TerminalMCP")


@mcp.tool()
def run_terminal(command: str, timeout: int = 30) -> Dict[str, Union[str, int]]:
    """
    执行终端命令

    Args:
        command: 要执行的shell命令
        timeout: 命令超时时间(秒)，默认30秒

    Returns:
        包含执行结果的字典
    """
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


@mcp.tool()
def list_files(path: str = ".") -> Dict[str, Union[str, List[str]]]:
    """
    列出指定目录中的文件和目录

    Args:
        path: 要列出内容的目录路径，默认为当前目录

    Returns:
        包含文件和目录列表的字典
    """
    try:
        import platform
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


@mcp.tool()
def read_file(file_path: str, max_lines: Optional[int] = None) -> Dict[str, str]:
    """
    读取文件内容

    Args:
        file_path: 要读取的文件路径
        max_lines: 最大读取行数，默认读取全部

    Returns:
        包含文件内容的字典
    """
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

