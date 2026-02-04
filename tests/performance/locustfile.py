"""性能压测脚本

使用 Locust 进行 API 性能测试。

运行方式:
  1. GUI 模式: locust -f tests/performance/locustfile.py
  2. 命令行模式: locust -f tests/performance/locustfile.py --headless -u 100 -r 10 -t 60s
"""

import random

from locust import HttpUser, between, events, task
from locust.runners import MasterRunner


class PortalUser(HttpUser):
    """Portal 服务用户模拟

    模拟真实用户访问 Portal 服务的场景。
    """

    # 等待时间：1-3 秒
    wait_time = between(1, 3)
    host = "http://localhost:8010"

    def on_start(self):
        """用户启动时登录"""
        self.login()

    def login(self):
        """用户登录获取 Token"""
        response = self.client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(5)
    def health_check(self):
        """健康检查（高频操作）"""
        self.client.get("/health")

    @task(3)
    def list_subsystems(self):
        """列出子系统"""
        if self.token:
            self.client.get("/api/subsystems", headers=self.headers)

    @task(2)
    def get_user_info(self):
        """获取用户信息"""
        if self.token:
            self.client.get("/auth/userinfo", headers=self.headers)

    @task(1)
    def validate_token(self):
        """验证 Token"""
        if self.token:
            self.client.get("/auth/validate", headers=self.headers)

    @task(1)
    def health_check_all(self):
        """聚合健康检查"""
        self.client.get("/health/all")


class NL2SQLUser(HttpUser):
    """NL2SQL 服务用户模拟

    模拟自然语言查询场景。
    """

    wait_time = between(2, 5)
    host = "http://localhost:8011"

    # 测试查询列表
    queries = [
        "显示所有用户",
        "查询今天的订单",
        "统计销售额",
        "列出最近的数据表",
        "显示数据质量报告",
    ]

    @task
    def health_check(self):
        """健康检查"""
        self.client.get("/health")

    @task(3)
    def query(self):
        """自然语言查询"""
        query = random.choice(self.queries)
        self.client.post("/query", json={
            "question": query,
            "database": "one_data_studio"
        })


class DataAPIUser(HttpUser):
    """数据 API 网关用户模拟

    模拟数据资产访问场景。
    """

    wait_time = between(1, 3)
    host = "http://localhost:8014"

    @task(2)
    def health_check(self):
        """健康检查"""
        self.client.get("/health")

    @task(5)
    def list_assets(self):
        """列出数据资产"""
        self.client.get("/api/assets")

    @task(3)
    def get_asset_detail(self):
        """获取资产详情"""
        # 假设资产 ID 为 1-100
        asset_id = random.randint(1, 100)
        self.client.get(f"/api/assets/{asset_id}")

    @task(1)
    def query_data(self):
        """查询数据"""
        self.client.post("/api/query", json={
            "asset_id": random.randint(1, 100),
            "limit": 10
        })


@events.request.add_hook
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """请求钩子 - 记录慢请求"""
    if exception:
        print(f"请求失败: {name} - {exception}")
    elif response_time > 1000:
        print(f"慢请求警告: {name} - 响应时间 {response_time}ms")


@events.test_stop.add_hook
def on_test_stop(environment, **kwargs):
    """测试结束钩子 - 输出统计"""
    if isinstance(environment.runner, MasterRunner):
        return

    stats = environment.stats
    print("\n" + "=" * 60)
    print("性能测试报告")
    print("=" * 60)
    print(f"总请求数: {stats.total.num_requests}")
    print(f"失败请求数: {stats.total.num_failures}")
    print(f"平均响应时间: {stats.total.avg_response_time:.2f}ms")
    print(f"中位数响应时间: {stats.total.median_response_time:.2f}ms")
    print(f"95% 响应时间: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99% 响应时间: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"每秒请求数 (RPS): {stats.total.total_rps:.2f}")
    print("=" * 60)
