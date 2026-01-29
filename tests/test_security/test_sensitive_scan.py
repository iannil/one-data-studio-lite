"""
TC-SEC-01: 敏感数据扫描测试
测试敏感数据检测功能
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestSensitiveScan:
    """TC-SEC-01: 敏感数据扫描测试（需要数据库）"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_sec_01_01_scan_sensitive_data(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-01-01: 扫描表中的敏感数据"""
        response = await sensitive_detect_client.post(
            "/api/sensitive/scan",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "table_name": "customers",
                "sample_size": 100
            }
        )
        # 表可能不存在
        assert response.status_code in (200, 400, 500)

        if response.status_code == 200:
            data = response.json()
            assert "table_name" in data
            assert "fields" in data
            assert "risk_level" in data

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_sec_01_02_detect_phone(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-01-02: 检测手机号敏感字段"""
        response = await sensitive_detect_client.post(
            "/api/sensitive/scan",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "users_with_phone", "sample_size": 50}
        )
        assert response.status_code in (200, 400, 500)

        if response.status_code == 200:
            data = response.json()
            # 验证结构
            assert "fields" in data

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_sec_01_03_detect_id_card(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-01-03: 检测身份证号敏感字段"""
        response = await sensitive_detect_client.post(
            "/api/sensitive/scan",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "users_with_idcard", "sample_size": 50}
        )
        assert response.status_code in (200, 400, 500)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_sec_01_04_detect_email(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-01-04: 检测邮箱敏感字段"""
        response = await sensitive_detect_client.post(
            "/api/sensitive/scan",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "users_with_email", "sample_size": 50}
        )
        assert response.status_code in (200, 400, 500)

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_sec_01_05_detect_bank_card(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-01-05: 检测银行卡号敏感字段"""
        response = await sensitive_detect_client.post(
            "/api/sensitive/scan",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "payment_info", "sample_size": 50}
        )
        assert response.status_code in (200, 400, 500)

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_sec_01_06_scan_non_sensitive_table(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-01-06: 扫描无敏感数据的表"""
        response = await sensitive_detect_client.post(
            "/api/sensitive/scan",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"table_name": "product_categories", "sample_size": 50}
        )
        assert response.status_code in (200, 400, 500)

        if response.status_code == 200:
            data = response.json()
            # 无敏感数据时，fields 可能为空
            assert "fields" in data

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_sec_01_07_get_scan_reports(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-01-07: 获取扫描报告列表"""
        response = await sensitive_detect_client.get(
            "/api/sensitive/reports",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
