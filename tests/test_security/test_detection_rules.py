"""
TC-SEC-03: 检测规则管理测试
测试敏感数据检测规则的查看和添加
"""

import pytest
from httpx import AsyncClient


class TestDetectionRules:
    """TC-SEC-03: 检测规则管理测试"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_sec_03_01_list_rules(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-03-01: 查看检测规则列表"""
        response = await sensitive_detect_client.get(
            "/api/sensitive/rules",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_sec_03_02_view_rule_detail(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-03-02: 查看规则详情"""
        response = await sensitive_detect_client.get(
            "/api/sensitive/rules",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()

        if len(data) > 0:
            rule = data[0]
            # 验证规则结构
            assert "id" in rule or "name" in rule

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_sec_03_03_add_custom_rule(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-03-03: 添加自定义检测规则"""
        response = await sensitive_detect_client.post(
            "/api/sensitive/rules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "员工工号检测",
                "pattern": "^EMP\\d{6}$",
                "sensitivity_level": "medium",
                "description": "检测员工工号格式 EMP+6位数字"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "员工工号检测"

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_sec_03_04_add_regex_rule(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-03-04: 添加规则 - 正则表达式检测"""
        response = await sensitive_detect_client.post(
            "/api/sensitive/rules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "车牌号检测",
                "pattern": "^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5}$",
                "sensitivity_level": "medium",
                "description": "检测中国车牌号"
            }
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_sec_03_05_add_critical_rule(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-03-05: 添加高敏感度规则"""
        response = await sensitive_detect_client.post(
            "/api/sensitive/rules",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "密码字段检测",
                "pattern": "password|passwd|pwd|secret|credential",
                "sensitivity_level": "critical",
                "description": "检测可能存储密码的字段名"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sensitivity_level"] == "critical"
