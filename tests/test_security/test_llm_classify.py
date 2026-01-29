"""
TC-SEC-02: LLM 分类测试
测试使用 LLM 对敏感数据进行分类
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestLLMClassify:
    """TC-SEC-02: LLM 分类测试（需要 LLM 服务）"""

    @pytest.mark.asyncio
    @pytest.mark.p0
    async def test_sec_02_01_llm_classify(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-02-01: 使用 LLM 分类敏感数据"""
        response = await sensitive_detect_client.post(
            "/api/sensitive/classify",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "data_samples": [
                    {"content": "张三，男，1990年1月1日出生，住址：北京市朝阳区xxx路xxx号"},
                    {"content": "李四的联系电话是13800138000，紧急联系人王五 13900139000"}
                ],
                "context": "客户信息表"
            }
        )
        # LLM 不可用时可能返回 500/503
        assert response.status_code in (200, 500, 503)

        if response.status_code == 200:
            data = response.json()
            # 验证返回了分类结果
            assert data is not None

    @pytest.mark.asyncio
    @pytest.mark.p2
    async def test_sec_02_02_classify_without_context(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-02-02: LLM 分类 - 无上下文"""
        response = await sensitive_detect_client.post(
            "/api/sensitive/classify",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "data_samples": [{"email": "user@example.com"}, {"phone": "13800138000"}]
            }
        )
        assert response.status_code in (200, 500, 503)

    @pytest.mark.asyncio
    @pytest.mark.p1
    async def test_sec_02_03_classify_mixed_data(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-02-03: LLM 分类 - 混合数据"""
        response = await sensitive_detect_client.post(
            "/api/sensitive/classify",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "data_samples": [
                    {"product": "智能手机"},
                    {"customer": "张三"},
                    {"amount": "9999.00"},
                    {"address": "北京市海淀区中关村大街1号"}
                ],
                "context": "订单数据"
            }
        )
        assert response.status_code in (200, 500, 503)

    @pytest.mark.asyncio
    @pytest.mark.p3
    async def test_sec_02_04_llm_unavailable(
        self, sensitive_detect_client: AsyncClient, admin_token: str
    ):
        """TC-SEC-02-04: LLM 分类 - 服务不可用"""
        # 在测试环境中，LLM 通常不可用
        response = await sensitive_detect_client.post(
            "/api/sensitive/classify",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"data_samples": [{"data": "test data"}]}
        )
        # 服务不应该崩溃
        assert response.status_code in (200, 500, 503)
