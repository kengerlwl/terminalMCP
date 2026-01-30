import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

# FRP 版本，与你服务端保持一致
FRP_VERSION = "0.65.0"

# 下载地址映射
FRP_DOWNLOAD_URLS = {
    ("Linux", "x86_64"): f"https://github.com/fatedier/frp/releases/download/v{FRP_VERSION}/frp_{FRP_VERSION}_linux_amd64.tar.gz",
    ("Linux", "aarch64"): f"https://github.com/fatedier/frp/releases/download/v{FRP_VERSION}/frp_{FRP_VERSION}_linux_arm64.tar.gz",
    ("Darwin", "x86_64"): f"https://github.com/fatedier/frp/releases/download/v{FRP_VERSION}/frp_{FRP_VERSION}_darwin_amd64.tar.gz",
    ("Darwin", "arm64"): f"https://github.com/fatedier/frp/releases/download/v{FRP_VERSION}/frp_{FRP_VERSION}_darwin_arm64.tar.gz",
    ("Windows", "AMD64"): f"https://github.com/fatedier/frp/releases/download/v{FRP_VERSION}/frp_{FRP_VERSION}_windows_amd64.zip",
}


class FRPManager:
    def __init__(self, server_addr: str, token: str, remote_port: int,
                 local_port: int = 8001, tunnel_name: str = "terminal-mcp"):
        self.server_addr = server_addr
        self.token = token
        self.remote_port = remote_port
        self.local_port = local_port
        self.tunnel_name = tunnel_name

        # 工作目录
        self.work_dir = Path(tempfile.gettempdir()) / "terminal-mcp"
        self.work_dir.mkdir(parents=True, exist_ok=True)

        self.frpc_path: Optional[Path] = None
        self.config_path: Optional[Path] = None
        self.process: Optional[subprocess.Popen] = None

    def _get_platform_info(self) -> tuple:
        """获取当前平台信息"""
        system = platform.system()
        machine = platform.machine()
        return (system, machine)

    def _get_download_url(self) -> str:
        """获取对应平台的下载地址"""
        platform_info = self._get_platform_info()
        url = FRP_DOWNLOAD_URLS.get(platform_info)
        if not url:
            raise RuntimeError(f"不支持的平台: {platform_info}")
        return url

    def _get_frpc_name(self) -> str:
        """获取 frpc 可执行文件名"""
        if platform.system() == "Windows":
            return "frpc.exe"
        return "frpc"

    def download_frpc(self) -> Path:
        """下载并解压 frpc"""
        frpc_name = self._get_frpc_name()
        frpc_path = self.work_dir / frpc_name

        # 如果已存在且可执行，直接返回
        if frpc_path.exists():
            print(f"[FRP] 使用已存在的 frpc: {frpc_path}")
            self.frpc_path = frpc_path
            return frpc_path

        url = self._get_download_url()
        print(f"[FRP] 下载 frpc 从: {url}")

        # 下载文件
        archive_name = url.split("/")[-1]
        archive_path = self.work_dir / archive_name

        try:
            urllib.request.urlretrieve(url, archive_path)
            print(f"[FRP] 下载完成: {archive_path}")
        except Exception as e:
            raise RuntimeError(f"下载失败: {e}")

        # 解压
        extract_dir = self.work_dir / "frp_extract"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir()

        try:
            if archive_name.endswith(".tar.gz"):
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(extract_dir)
            elif archive_name.endswith(".zip"):
                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)

            # 找到 frpc
            for root, dirs, files in os.walk(extract_dir):
                if frpc_name in files:
                    src = Path(root) / frpc_name
                    shutil.copy2(src, frpc_path)
                    break

            if not frpc_path.exists():
                raise RuntimeError("解压后未找到 frpc")

            # 设置可执行权限 (Linux/Mac)
            if platform.system() != "Windows":
                os.chmod(frpc_path, 0o755)

            print(f"[FRP] frpc 准备完成: {frpc_path}")

        finally:
            # 清理临时文件
            if archive_path.exists():
                archive_path.unlink()
            if extract_dir.exists():
                shutil.rmtree(extract_dir)

        self.frpc_path = frpc_path
        return frpc_path

    def generate_config(self) -> Path:
        """生成 frpc.toml 配置文件 (v0.52.0+ 使用 TOML 格式)"""
        config_content = f"""serverAddr = "{self.server_addr}"
serverPort = 7000
auth.method = "token"
auth.token = "{self.token}"
transport.tls.enable = true

[[proxies]]
name = "{self.tunnel_name}"
type = "tcp"
localIP = "127.0.0.1"
localPort = {self.local_port}
remotePort = {self.remote_port}
"""

        config_path = self.work_dir / "frpc.toml"
        config_path.write_text(config_content)
        print(f"[FRP] 配置文件生成: {config_path}")

        self.config_path = config_path
        return config_path

    def start(self) -> subprocess.Popen:
        """启动 frpc"""
        if not self.frpc_path:
            self.download_frpc()
        if not self.config_path:
            self.generate_config()

        cmd = [str(self.frpc_path), "-c", str(self.config_path)]
        print(f"[FRP] 启动命令: {' '.join(cmd)}")

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"[FRP] frpc 已启动, PID: {self.process.pid}")
        print(f"[FRP] 远程访问地址: http://{self.server_addr}:{self.remote_port}")

        return self.process

    def stop(self):
        """停止 frpc"""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            print("[FRP] frpc 已停止")

    def cleanup(self):
        """清理临时文件"""
        self.stop()
        if self.config_path and self.config_path.exists():
            self.config_path.unlink()


if __name__ == "__main__":
    # 测试下载
    manager = FRPManager(
        server_addr="127.0.0.1",
        token="test",
        remote_port=9001
    )
    manager.download_frpc()

