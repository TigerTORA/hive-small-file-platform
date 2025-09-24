"""
YARN任务监控工具类
通过YARN REST API监控和管理Hive任务
支持HA配置的ResourceManager集群
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

import requests

logger = logging.getLogger(__name__)


class YarnApplicationState(Enum):
    """YARN应用状态枚举"""

    NEW = "NEW"
    NEW_SAVING = "NEW_SAVING"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
    KILLED = "KILLED"


class YarnApplicationFinalStatus(Enum):
    """YARN应用最终状态枚举"""

    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    KILLED = "KILLED"
    UNDEFINED = "UNDEFINED"


@dataclass
class YarnApplicationInfo:
    """YARN应用信息"""

    id: str
    name: str
    application_type: str
    user: str
    queue: str
    state: str
    final_status: str
    progress: float
    tracking_url: str
    original_tracking_url: str
    start_time: int
    finish_time: int
    elapsed_time: int
    memory_seconds: int
    vcore_seconds: int
    preempted_resource_mb: int
    preempted_resource_vcores: int


@dataclass
class YarnClusterInfo:
    """YARN集群信息"""

    cluster_id: int
    resource_manager_version: str
    state: str
    ha_state: str
    ha_zookeeper_connection_string: str
    hadoop_version: str
    hadoop_build_version: str
    hadoop_version_built_on: str
    started_on: int
    total_memory: int
    total_vcores: int
    total_nodes: int
    lost_nodes: int
    unhealthy_nodes: int
    decommissioned_nodes: int
    rebooted_nodes: int
    active_nodes: int


class YarnResourceManagerMonitor:
    """YARN ResourceManager监控器"""

    def __init__(self, resource_manager_urls: Union[str, List[str]], timeout: int = 30):
        """
        初始化YARN监控器

        Args:
            resource_manager_urls: ResourceManager URL或URL列表
            timeout: 请求超时时间（秒）
        """
        if isinstance(resource_manager_urls, str):
            self.resource_manager_urls = [resource_manager_urls]
        else:
            self.resource_manager_urls = resource_manager_urls

        self.timeout = timeout
        self.session = requests.Session()
        self.active_rm_url = None

        # 清理URL格式
        self.resource_manager_urls = [
            url.rstrip("/") for url in self.resource_manager_urls
        ]

        logger.info(f"Initialized YARN monitor with RMs: {self.resource_manager_urls}")

        # 查找活跃的ResourceManager
        self._find_active_resource_manager()

    def _find_active_resource_manager(self) -> bool:
        """查找活跃的ResourceManager"""
        for rm_url in self.resource_manager_urls:
            try:
                cluster_info_url = f"{rm_url}/ws/v1/cluster/info"
                logger.debug(f"Testing RM: {rm_url}")

                response = self.session.get(cluster_info_url, timeout=self.timeout)

                if response.status_code == 200:
                    data = response.json()
                    cluster_info = data.get("clusterInfo", {})
                    ha_state = cluster_info.get("haState", "UNKNOWN")

                    logger.info(f"RM {rm_url} state: {ha_state}")

                    if ha_state == "ACTIVE":
                        self.active_rm_url = rm_url
                        logger.info(f"Found active ResourceManager: {rm_url}")
                        return True

            except Exception as e:
                logger.warning(f"Failed to connect to RM {rm_url}: {str(e)}")
                continue

        # 如果没有找到ACTIVE状态的RM，使用第一个可用的
        if not self.active_rm_url and self.resource_manager_urls:
            for rm_url in self.resource_manager_urls:
                try:
                    cluster_info_url = f"{rm_url}/ws/v1/cluster/info"
                    response = self.session.get(cluster_info_url, timeout=self.timeout)

                    if response.status_code == 200:
                        self.active_rm_url = rm_url
                        logger.warning(f"Using RM as fallback: {rm_url}")
                        return True

                except Exception as e:
                    continue

        logger.error("No active ResourceManager found")
        return False

    def test_connection(self) -> Tuple[bool, str]:
        """
        测试YARN连接

        Returns:
            (是否连接成功, 错误信息或成功信息)
        """
        if not self.active_rm_url:
            if not self._find_active_resource_manager():
                return False, "无法找到活跃的ResourceManager"

        try:
            cluster_info = self.get_cluster_info()
            if cluster_info:
                return True, f"YARN连接成功，活跃RM: {self.active_rm_url}"
            else:
                return False, "无法获取集群信息"

        except Exception as e:
            error_msg = f"YARN连接测试失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_cluster_info(self) -> Optional[YarnClusterInfo]:
        """获取YARN集群信息"""
        if not self.active_rm_url:
            logger.error("No active ResourceManager available")
            return None

        try:
            url = f"{self.active_rm_url}/ws/v1/cluster/info"
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                cluster_info = data["clusterInfo"]

                return YarnClusterInfo(
                    cluster_id=cluster_info.get("id", 0),
                    resource_manager_version=cluster_info.get(
                        "resourceManagerVersion", ""
                    ),
                    state=cluster_info.get("state", ""),
                    ha_state=cluster_info.get("haState", ""),
                    ha_zookeeper_connection_string=cluster_info.get(
                        "haZookeeperConnectionString", ""
                    ),
                    hadoop_version=cluster_info.get("hadoopVersion", ""),
                    hadoop_build_version=cluster_info.get("hadoopBuildVersion", ""),
                    hadoop_version_built_on=cluster_info.get(
                        "hadoopVersionBuiltOn", ""
                    ),
                    started_on=cluster_info.get("startedOn", 0),
                    total_memory=cluster_info.get("totalMB", 0),
                    total_vcores=cluster_info.get("totalVirtualCores", 0),
                    total_nodes=cluster_info.get("totalNodes", 0),
                    lost_nodes=cluster_info.get("lostNodes", 0),
                    unhealthy_nodes=cluster_info.get("unhealthyNodes", 0),
                    decommissioned_nodes=cluster_info.get("decommissionedNodes", 0),
                    rebooted_nodes=cluster_info.get("rebootedNodes", 0),
                    active_nodes=cluster_info.get("activeNodes", 0),
                )
            else:
                logger.error(f"Failed to get cluster info: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting cluster info: {str(e)}")
            return None

    def get_applications(
        self,
        state: Optional[str] = None,
        user: Optional[str] = None,
        application_types: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[YarnApplicationInfo]:
        """
        获取YARN应用列表

        Args:
            state: 应用状态过滤
            user: 用户过滤
            application_types: 应用类型过滤（如["MAPREDUCE", "TEZ"]）
            limit: 返回结果限制

        Returns:
            应用信息列表
        """
        if not self.active_rm_url:
            logger.error("No active ResourceManager available")
            return []

        try:
            url = f"{self.active_rm_url}/ws/v1/cluster/apps"
            params = {}

            if state:
                params["state"] = state
            if user:
                params["user"] = user
            if application_types:
                params["applicationTypes"] = ",".join(application_types)
            if limit:
                params["limit"] = limit

            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                apps_data = data.get("apps", {})

                if not apps_data or "app" not in apps_data:
                    return []

                applications = []
                for app in apps_data["app"]:
                    applications.append(
                        YarnApplicationInfo(
                            id=app.get("id", ""),
                            name=app.get("name", ""),
                            application_type=app.get("applicationType", ""),
                            user=app.get("user", ""),
                            queue=app.get("queue", ""),
                            state=app.get("state", ""),
                            final_status=app.get("finalStatus", ""),
                            progress=app.get("progress", 0.0),
                            tracking_url=app.get("trackingUrl", ""),
                            original_tracking_url=app.get("originalTrackingUrl", ""),
                            start_time=app.get("startedTime", 0),
                            finish_time=app.get("finishedTime", 0),
                            elapsed_time=app.get("elapsedTime", 0),
                            memory_seconds=app.get("memorySeconds", 0),
                            vcore_seconds=app.get("vcoreSeconds", 0),
                            preempted_resource_mb=app.get("preemptedResourceMB", 0),
                            preempted_resource_vcores=app.get(
                                "preemptedResourceVCores", 0
                            ),
                        )
                    )

                return applications
            else:
                logger.error(f"Failed to get applications: HTTP {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error getting applications: {str(e)}")
            return []

    def get_application_by_id(
        self, application_id: str
    ) -> Optional[YarnApplicationInfo]:
        """
        根据应用ID获取应用信息

        Args:
            application_id: 应用ID

        Returns:
            应用信息，失败返回None
        """
        if not self.active_rm_url:
            logger.error("No active ResourceManager available")
            return None

        try:
            url = f"{self.active_rm_url}/ws/v1/cluster/apps/{application_id}"
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                app = data["app"]

                return YarnApplicationInfo(
                    id=app.get("id", ""),
                    name=app.get("name", ""),
                    application_type=app.get("applicationType", ""),
                    user=app.get("user", ""),
                    queue=app.get("queue", ""),
                    state=app.get("state", ""),
                    final_status=app.get("finalStatus", ""),
                    progress=app.get("progress", 0.0),
                    tracking_url=app.get("trackingUrl", ""),
                    original_tracking_url=app.get("originalTrackingUrl", ""),
                    start_time=app.get("startedTime", 0),
                    finish_time=app.get("finishedTime", 0),
                    elapsed_time=app.get("elapsedTime", 0),
                    memory_seconds=app.get("memorySeconds", 0),
                    vcore_seconds=app.get("vcoreSeconds", 0),
                    preempted_resource_mb=app.get("preemptedResourceMB", 0),
                    preempted_resource_vcores=app.get("preemptedResourceVCores", 0),
                )
            else:
                logger.warning(
                    f"Application {application_id} not found: HTTP {response.status_code}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting application {application_id}: {str(e)}")
            return None

    def find_hive_applications(
        self, user: str, limit: int = 50
    ) -> List[YarnApplicationInfo]:
        """
        查找用户的Hive相关应用

        Args:
            user: 用户名
            limit: 返回结果限制

        Returns:
            Hive应用信息列表
        """
        logger.info(f"Finding Hive applications for user: {user}")

        # 查找TEZ和MAPREDUCE类型的应用（Hive常用）
        applications = self.get_applications(
            user=user, application_types=["TEZ", "MAPREDUCE"], limit=limit
        )

        # 过滤包含hive关键词的应用
        hive_apps = []
        for app in applications:
            if (
                "hive" in app.name.lower()
                or "insert" in app.name.lower()
                or "select" in app.name.lower()
            ):
                hive_apps.append(app)

        logger.info(f"Found {len(hive_apps)} Hive applications")
        return hive_apps

    def monitor_application_progress(
        self, application_id: str, check_interval: int = 5, max_wait: int = 3600
    ) -> Dict:
        """
        监控应用执行进度

        Args:
            application_id: 应用ID
            check_interval: 检查间隔（秒）
            max_wait: 最大等待时间（秒）

        Returns:
            监控结果字典
        """
        logger.info(f"Starting to monitor application: {application_id}")

        start_time = time.time()
        progress_history = []

        while time.time() - start_time < max_wait:
            app_info = self.get_application_by_id(application_id)

            if not app_info:
                logger.warning(f"Application {application_id} not found")
                break

            current_time = datetime.now().isoformat()
            progress_info = {
                "timestamp": current_time,
                "progress": app_info.progress,
                "state": app_info.state,
                "final_status": app_info.final_status,
                "elapsed_time": app_info.elapsed_time,
            }
            progress_history.append(progress_info)

            logger.info(
                f"Application {application_id} progress: {app_info.progress}%, "
                f"state: {app_info.state}, final_status: {app_info.final_status}"
            )

            # 检查是否完成
            if app_info.state in [
                YarnApplicationState.FINISHED.value,
                YarnApplicationState.FAILED.value,
                YarnApplicationState.KILLED.value,
            ]:
                logger.info(
                    f"Application {application_id} completed with state: {app_info.state}"
                )
                break

            time.sleep(check_interval)

        final_app_info = self.get_application_by_id(application_id)

        return {
            "application_id": application_id,
            "monitoring_duration": time.time() - start_time,
            "progress_history": progress_history,
            "final_state": final_app_info.state if final_app_info else "UNKNOWN",
            "final_status": (
                final_app_info.final_status if final_app_info else "UNKNOWN"
            ),
            "success": (
                final_app_info.final_status
                == YarnApplicationFinalStatus.SUCCEEDED.value
                if final_app_info
                else False
            ),
        }

    def close(self):
        """关闭监控器连接"""
        if hasattr(self, "session"):
            self.session.close()
            logger.info("YARN monitor session closed")


# 测试函数
if __name__ == "__main__":
    # 测试YARN监控器
    rm_urls = [
        "http://192.168.0.106:8088",  # Active RM
        "http://192.168.0.107:8088",  # Standby RM
    ]

    monitor = YarnResourceManagerMonitor(rm_urls)

    print("Testing YARN connection...")
    success, message = monitor.test_connection()
    print(f"Connection test: {success}, Message: {message}")

    if success:
        # 测试获取集群信息
        cluster_info = monitor.get_cluster_info()
        if cluster_info:
            print(f"Cluster info: {cluster_info}")

        # 测试获取应用列表
        apps = monitor.get_applications(limit=5)
        print(f"Found {len(apps)} applications")
        for app in apps[:3]:
            print(
                f"App: {app.id}, Name: {app.name}, State: {app.state}, Progress: {app.progress}%"
            )

        # 测试查找Hive应用
        hive_apps = monitor.find_hive_applications("hive", limit=5)
        print(f"Found {len(hive_apps)} Hive applications")

    monitor.close()
