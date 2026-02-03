"""服务控制工具

提供服务的启动、停止、重启等操作。
"""

import asyncio
import logging
import os
import subprocess
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    url: str
    stop_endpoint: str = "/shutdown"
    health_endpoint: str = "/health"


# 内部微服务列表
INTERNAL_SERVICES = [
    ServiceInfo(name="portal", url="http://localhost:8010", stop_endpoint="/shutdown"),
    ServiceInfo(name="nl2sql", url="http://localhost:8011"),
    ServiceInfo(name="ai_cleaning", url="http://localhost:8012"),
    ServiceInfo(name="metadata_sync", url="http://localhost:8013"),
    ServiceInfo(name="data_api", url="http://localhost:8014"),
    ServiceInfo(name="sensitive_detect", url="http://localhost:8015"),
    ServiceInfo(name="audit_log", url="http://localhost:8016"),
]


async def stop_service_via_http(service: ServiceInfo, timeout: int = 5) -> tuple[bool, str]:
    """通过 HTTP API 停止服务

    Args:
        service: 服务信息
        timeout: 请求超时时间（秒）

    Returns:
        (是否成功, 消息)
    """
    try:
        stop_url = f"{service.url}{service.stop_endpoint}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(stop_url)
            if response.status_code in (200, 202):
                return True, f"{service.name} 已停止"
            else:
                return False, f"{service.name} 停止失败: HTTP {response.status_code}"
    except TimeoutError:
        return False, f"{service.name} 停止超时"
    except Exception as e:
        return False, f"{service.name} 停止异常: {e}"


async def check_service_health(service: ServiceInfo, timeout: int = 3) -> bool:
    """检查服务健康状态

    Args:
        service: 服务信息
        timeout: 请求超时时间（秒）

    Returns:
        是否健康
    """
    try:
        health_url = f"{service.url}{service.health_endpoint}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(health_url)
            return response.status_code == 200
    except Exception:
        return False


async def stop_internal_services(
    skip_self: bool = True,
    timeout: int = 5,
) -> dict[str, tuple[bool, str]]:
    """停止所有内部服务

    Args:
        skip_self: 是否跳过当前服务（portal）
        timeout: 每个服务的超时时间（秒）

    Returns:
        {服务名: (是否成功, 消息)}
    """
    results = {}

    tasks = []
    service_names = []

    for service in INTERNAL_SERVICES:
        if skip_self and service.name == "portal":
            continue

        tasks.append(stop_service_via_http(service, timeout))
        service_names.append(service.name)

    if tasks:
        stop_results = await asyncio.gather(*tasks, return_exceptions=True)

        for name, result in zip(service_names, stop_results):
            if isinstance(result, Exception):
                results[name] = (False, f"异常: {result}")
            else:
                results[name] = result

    return results


async def stop_docker_services(
    label_filter: str = "com.one-data-studio.service",
    timeout: int = 10,
) -> tuple[bool, str]:
    """通过 Docker API 停止服务

    Args:
        label_filter: Docker 标签过滤器
        timeout: 超时时间（秒）

    Returns:
        (是否成功, 消息)
    """
    try:
        # 检查 Docker 是否可用
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False, "Docker 不可用"

        # 获取带有指定标签的容器
        result = subprocess.run(
            ["docker", "ps", "--filter", f"label={label_filter}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return False, "获取 Docker 容器列表失败"

        containers = [c.strip() for c in result.stdout.split("\n") if c.strip()]

        if not containers:
            return True, "没有需要停止的容器"

        # 停止所有容器
        stop_result = subprocess.run(
            ["docker", "stop"] + containers + ["--timeout", str(timeout)],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )

        if stop_result.returncode == 0:
            return True, f"已停止 {len(containers)} 个容器: {', '.join(containers)}"
        else:
            return False, f"停止容器失败: {stop_result.stderr}"

    except FileNotFoundError:
        return False, "Docker 命令不可用"
    except subprocess.TimeoutExpired:
        return False, "Docker 命令执行超时"
    except Exception as e:
        return False, f"Docker 停止异常: {e}"


async def stop_k8s_services(
    namespace: str = "default",
    label_selector: str = "app=one-data-studio",
    timeout: int = 30,
) -> tuple[bool, str]:
    """通过 Kubernetes API 停止服务

    Args:
        namespace: Kubernetes 命名空间
        label_selector: 标签选择器
        timeout: 超时时间（秒）

    Returns:
        (是否成功, 消息)
    """
    try:
        # 检查 kubectl 是否可用
        result = subprocess.run(
            ["kubectl", "version", "--client", "--short"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False, "kubectl 不可用"

        # 通过将副本数设置为 0 来停止服务
        result = subprocess.run(
            [
                "kubectl", "scale",
                "deployment",
                "--selector", label_selector,
                "--replicas=0",
                "-n", namespace,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return True, f"Kubernetes 副本数已设置为 0 (namespace: {namespace})"
        else:
            return False, f"kubectl 命令失败: {result.stderr}"

    except FileNotFoundError:
        return False, "kubectl 命令不可用"
    except subprocess.TimeoutExpired:
        return False, "kubectl 命令执行超时"
    except Exception as e:
        return False, f"Kubernetes 停止异常: {e}"


async def emergency_stop_all(
    reason: str,
    triggered_by: str,
) -> dict:
    """紧急停止所有服务

    尝试多种方式停止服务：
    1. HTTP API 停止内部微服务
    2. Docker 停止容器
    3. Kubernetes 停止部署

    Args:
        reason: 停止原因
        triggered_by: 触发者

    Returns:
        停止结果
    """
    results = {
        "reason": reason,
        "triggered_by": triggered_by,
        "methods": {},
    }

    # 方法 1: HTTP API 停止内部服务
    logger.warning(f"紧急停止触发: {reason} (操作者: {triggered_by})")
    http_results = await stop_internal_services(skip_self=True)
    results["methods"]["http_api"] = http_results

    # 方法 2: Docker 停止
    docker_success, docker_msg = await stop_docker_services()
    results["methods"]["docker"] = {"success": docker_success, "message": docker_msg}

    # 方法 3: Kubernetes 停止
    k8s_success, k8s_msg = await stop_k8s_services()
    results["methods"]["kubernetes"] = {"success": k8s_success, "message": k8s_msg}

    return results


async def get_service_status(timeout: int = 3) -> dict:
    """获取所有服务状态

    Args:
        timeout: 请求超时时间（秒）

    Returns:
        {服务名: 是否健康}
    """
    status = {}

    tasks = []
    service_names = []

    for service in INTERNAL_SERVICES:
        tasks.append(check_service_health(service, timeout))
        service_names.append(service.name)

    if tasks:
        health_results = await asyncio.gather(*tasks, return_exceptions=True)

        for name, result in zip(service_names, health_results):
            if isinstance(result, Exception):
                status[name] = False
            else:
                status[name] = result

    return status


def get_container_info() -> dict:
    """获取容器信息（如果运行在容器中）

    Returns:
        容器信息
    """
    info = {
        "in_container": False,
        "container_id": None,
        "docker_compose": False,
    }

    # 检查是否在容器中
    if os.path.exists("/.dockerenv"):
        info["in_container"] = True

    # 检查容器 ID
    try:
        with open("/proc/self/cgroup") as f:
            content = f.read()
            if "docker" in content or "kubepods" in content:
                info["in_container"] = True
    except Exception:
        pass

    # 检查 Docker Compose
    if os.path.exists("/.dockerconfig") or os.environ.get("DOCKER_COMPOSE"):
        info["docker_compose"] = True

    return info
