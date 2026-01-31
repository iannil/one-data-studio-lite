"""ShardingSphere 代理路由 - 数据脱敏规则管理

使用 DistSQL 动态管理脱敏规则，无需重启服务。

API 规范:
    GET  /api/proxy/shardingsphere/v1/mask-rules              # 获取所有脱敏规则
    GET  /api/proxy/shardingsphere/v1/mask-rules/{table}     # 获取表的脱敏规则
    POST /api/proxy/shardingsphere/v1/mask-rules              # 创建脱敏规则
    PUT  /api/proxy/shardingsphere/v1/mask-rules              # 更新脱敏规则
    DELETE /api/proxy/shardingsphere/v1/mask-rules/{table}    # 删除表的脱敏规则
    POST /api/proxy/shardingsphere/v1/mask-rules/batch       # 批量创建规则
    GET  /api/proxy/shardingsphere/v1/algorithms              # 获取可用算法
    GET  /api/proxy/shardingsphere/v1/presets                 # 获取预设方案
    POST /api/proxy/shardingsphere/v1/sync                    # 同步规则到 Proxy

认证: 需要 Bearer Token（通过 get_current_user 依赖）
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.api_response import (
    ApiResponse,
    ErrorCode,
    error,
    success,
)
from services.common.auth import TokenPayload, get_current_user
from services.common.database import get_db
from services.common.shardingsphere_client import ShardingSphereClient, MaskAlgorithms
from services.common.repositories.mask_repository import MaskRuleRepository
from services.common.orm_models import MaskRuleORM

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/proxy/shardingsphere", tags=["ShardingSphere"])

# ShardingSphere Proxy 连接配置
# 从环境变量读取，用于容器内连接
PROXY_HOST = os.environ.get("SHARDINGSPHERE_HOST", "ods-shardingsphere")
PROXY_PORT = int(os.environ.get("SHARDINGSPHERE_PORT", "3307"))
PROXY_USER = os.environ.get("SHARDINGSPHERE_USER", "root")
PROXY_PASSWORD = os.environ.get("SHARDINGSPHERE_PASSWORD", "changeme")
PROXY_DATABASE = os.environ.get("SHARDINGSPHERE_DATABASE", "one_data_studio")


class MaskRuleItem(BaseModel):
    """单个脱敏规则"""
    table_name: str
    column_name: str
    algorithm_type: str
    algorithm_props: Optional[dict] = None
    enabled: bool = True


class MaskRuleRequest(BaseModel):
    """创建/更新脱敏规则请求"""
    table_name: str
    column_name: str
    algorithm_type: str
    algorithm_props: Optional[dict] = None


class BatchMaskRequest(BaseModel):
    """批量脱敏规则请求"""
    rules: list[MaskRuleRequest]


def _get_client() -> ShardingSphereClient:
    """获取 ShardingSphere 客户端"""
    return ShardingSphereClient(
        host=PROXY_HOST,
        port=PROXY_PORT,
        user=PROXY_USER,
        password=PROXY_PASSWORD,
        database=PROXY_DATABASE,
    )


# ============================================================
# v1 版本 API（推荐使用，统一响应格式）
# ============================================================

@router.get(
    "/v1/mask-rules",
    response_model=ApiResponse,
    summary="获取所有脱敏规则",
    description="从 ShardingSphere Proxy 读取所有脱敏规则"
)
async def list_mask_rules_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """列出所有脱敏规则"""
    try:
        async with _get_client() as client:
            rules = await client.list_mask_rules()
            return success(data={"rules": rules, "total": len(rules)})
    except Exception as e:
        logger.error(f"获取脱敏规则失败: {e}")
        return error(
            message=f"获取脱敏规则失败: {str(e)}",
            code=ErrorCode.SHARDINGSPHERE_ERROR
        )


@router.get(
    "/v1/mask-rules/{table_name}",
    response_model=ApiResponse,
    summary="获取表的脱敏规则",
    description="获取指定表的脱敏规则"
)
async def get_table_rules_v1(
    table_name: str,
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """获取指定表的脱敏规则"""
    try:
        async with _get_client() as client:
            rules = await client.get_table_rules(table_name)
            return success(data={"rules": rules, "total": len(rules)})
    except Exception as e:
        logger.error(f"获取表脱敏规则失败: {e}")
        return error(
            message=f"获取表脱敏规则失败: {str(e)}",
            code=ErrorCode.SHARDINGSPHERE_ERROR
        )


@router.post(
    "/v1/mask-rules",
    response_model=ApiResponse,
    summary="创建脱敏规则",
    description="创建脱敏规则，同时写入本地数据库和 ShardingSphere Proxy"
)
async def create_mask_rule_v1(
    req: MaskRuleRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """创建脱敏规则"""
    try:
        # 1. 写入 ShardingSphere Proxy
        async with _get_client() as client:
            ok = await client.add_mask_rule(
                req.table_name,
                req.column_name,
                req.algorithm_type,
                req.algorithm_props,
            )
            if not ok:
                return error(
                    message="创建规则失败，可能规则已存在",
                    code=ErrorCode.VALIDATION_FAILED
                )

        # 2. 保存到本地数据库
        repo = MaskRuleRepository(db)
        await repo.upsert_by_table_column(
            req.table_name,
            req.column_name,
            req.algorithm_type,
            req.algorithm_props,
        )
        # 标记已同步
        rule = await repo.get_by_table_column(req.table_name, req.column_name)
        if rule:
            await repo.mark_synced(rule.id)

        return success(
            data={"table": req.table_name, "column": req.column_name},
            message=f"脱敏规则已创建: {req.table_name}.{req.column_name}"
        )
    except Exception as e:
        logger.error(f"创建脱敏规则失败: {e}")
        return error(
            message=f"创建规则失败: {str(e)}",
            code=ErrorCode.INTERNAL_ERROR
        )


@router.put(
    "/v1/mask-rules",
    response_model=ApiResponse,
    summary="更新脱敏规则",
    description="更新脱敏规则，使用 upsert 模式"
)
async def update_mask_rule_v1(
    req: MaskRuleRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """更新脱敏规则"""
    try:
        async with _get_client() as client:
            ok = await client.upsert_mask_rule(
                req.table_name,
                req.column_name,
                req.algorithm_type,
                req.algorithm_props,
            )
            if not ok:
                return error(
                    message="更新规则失败",
                    code=ErrorCode.SHARDINGSPHERE_ERROR
                )

        # 更新本地数据库
        repo = MaskRuleRepository(db)
        await repo.upsert_by_table_column(
            req.table_name,
            req.column_name,
            req.algorithm_type,
            req.algorithm_props,
        )
        rule = await repo.get_by_table_column(req.table_name, req.column_name)
        if rule:
            await repo.mark_synced(rule.id)

        return success(
            data={"table": req.table_name, "column": req.column_name},
            message=f"脱敏规则已更新: {req.table_name}.{req.column_name}"
        )
    except Exception as e:
        logger.error(f"更新脱敏规则失败: {e}")
        return error(
            message=f"更新规则失败: {str(e)}",
            code=ErrorCode.INTERNAL_ERROR
        )


@router.delete(
    "/v1/mask-rules/{table_name}",
    response_model=ApiResponse,
    summary="删除表的脱敏规则",
    description="删除指定表的所有脱敏规则"
)
async def delete_table_rules_v1(
    table_name: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """删除表的所有脱敏规则"""
    try:
        async with _get_client() as client:
            ok = await client.drop_mask_rule(table_name)
            if not ok:
                return error(
                    message="规则不存在或删除失败",
                    code=ErrorCode.NOT_FOUND
                )

        # 删除本地记录
        repo = MaskRuleRepository(db)
        rules = await repo.get_by_table(table_name)
        for rule in rules:
            await repo.delete(rule.id)

        return success(
            data={"table": table_name},
            message=f"已删除表 {table_name} 的所有脱敏规则"
        )
    except Exception as e:
        logger.error(f"删除脱敏规则失败: {e}")
        return error(
            message=f"删除规则失败: {str(e)}",
            code=ErrorCode.INTERNAL_ERROR
        )


@router.post(
    "/v1/mask-rules/batch",
    response_model=ApiResponse,
    summary="批量创建脱敏规则",
    description="批量创建多个脱敏规则"
)
async def batch_create_rules_v1(
    req: BatchMaskRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """批量创建脱敏规则"""
    success_count = 0
    errors = []

    async with _get_client() as client:
        repo = MaskRuleRepository(db)

        for rule in req.rules:
            try:
                ok = await client.upsert_mask_rule(
                    rule.table_name,
                    rule.column_name,
                    rule.algorithm_type,
                    rule.algorithm_props,
                )
                if ok:
                    await repo.upsert_by_table_column(
                        rule.table_name,
                        rule.column_name,
                        rule.algorithm_type,
                        rule.algorithm_props,
                    )
                    db_rule = await repo.get_by_table_column(
                        rule.table_name, rule.column_name
                    )
                    if db_rule:
                        await repo.mark_synced(db_rule.id)
                    success_count += 1
                else:
                    errors.append(f"{rule.table_name}.{rule.column_name}: 创建失败")
            except Exception as e:
                errors.append(f"{rule.table_name}.{rule.column_name}: {str(e)}")

    return success(
        data={
            "success_count": success_count,
            "total_count": len(req.rules),
            "errors": errors if errors else None,
        },
        message=f"成功创建 {success_count}/{len(req.rules)} 个规则"
    )


@router.get(
    "/v1/algorithms",
    response_model=ApiResponse,
    summary="获取可用算法",
    description="列出所有可用的脱敏算法"
)
async def list_algorithms_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """列出可用的脱敏算法"""
    try:
        async with _get_client() as client:
            algorithms = await client.list_mask_algorithms()
            return success(data={"algorithms": algorithms})
    except Exception as e:
        logger.error(f"获取算法列表失败: {e}")
        # 返回预定义的算法
        return success(data={
            "algorithms": [
                {"name": "KEEP_FIRST_N_LAST_M", "description": "保留前N后M位"},
                {"name": "MASK_FIRST_N_LAST_M", "description": "遮盖前N后M位"},
                {"name": "MD5", "description": "MD5哈希"},
                {"name": "MASK_BEFORE_SPECIAL_CHARS", "description": "特殊字符前遮盖"},
            ]
        })


@router.get(
    "/v1/presets",
    response_model=ApiResponse,
    summary="获取预设方案",
    description="列出预设的脱敏方案"
)
async def list_presets_v1(
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """列出预设的脱敏方案"""
    return success(data={
        "presets": [
            {
                "name": "phone",
                "description": "手机号脱敏 (保留前3后4)",
                "algorithm_type": MaskAlgorithms.KEEP_FIRST_N_LAST_M,
                "algorithm_props": {"first-n": "3", "last-m": "4", "replace-char": "*"},
            },
            {
                "name": "id_card",
                "description": "身份证号脱敏 (保留前6后4)",
                "algorithm_type": MaskAlgorithms.KEEP_FIRST_N_LAST_M,
                "algorithm_props": {"first-n": "6", "last-m": "4", "replace-char": "*"},
            },
            {
                "name": "bank_card",
                "description": "银行卡号脱敏 (保留后4位)",
                "algorithm_type": MaskAlgorithms.KEEP_FIRST_N_LAST_M,
                "algorithm_props": {"first-n": "0", "last-m": "4", "replace-char": "*"},
            },
            {
                "name": "email",
                "description": "邮箱脱敏 (@前遮盖)",
                "algorithm_type": MaskAlgorithms.MASK_BEFORE_SPECIAL_CHARS,
                "algorithm_props": {"special-chars": "@", "replace-char": "*"},
            },
        ]
    })


@router.post(
    "/v1/sync",
    response_model=ApiResponse,
    summary="同步规则到 Proxy",
    description="将本地未同步的规则同步到 ShardingSphere Proxy"
)
async def sync_rules_to_proxy_v1(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
) -> ApiResponse:
    """将本地未同步的规则同步到 Proxy"""
    repo = MaskRuleRepository(db)
    unsynced = await repo.get_unsynced_rules()

    if not unsynced:
        return success(
            data={"synced_count": 0},
            message="没有需要同步的规则"
        )

    success_count = 0
    async with _get_client() as client:
        for rule in unsynced:
            try:
                ok = await client.upsert_mask_rule(
                    rule.table_name,
                    rule.column_name,
                    rule.algorithm_type,
                    rule.algorithm_props,
                )
                if ok:
                    await repo.mark_synced(rule.id)
                    success_count += 1
            except Exception as e:
                logger.error(f"同步规则失败: {rule.table_name}.{rule.column_name}: {e}")

    return success(
        data={
            "synced_count": success_count,
            "total_count": len(unsynced),
        },
        message=f"已同步 {success_count}/{len(unsynced)} 个规则"
    )


# ============================================================
# 旧版 API（向后兼容，逐步废弃）
# ============================================================

@router.get("/mask-rules")
async def list_mask_rules_legacy(user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取所有脱敏规则"""
    result = await list_mask_rules_v1(user=user)
    if result.code == ErrorCode.SUCCESS:
        return {"rules": result.data.get("rules", []), "total": result.data.get("total", 0)}
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/mask-rules/{table_name}")
async def get_table_rules_legacy(table_name: str, user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取表的脱敏规则"""
    result = await get_table_rules_v1(table_name=table_name, user=user)
    if result.code == ErrorCode.SUCCESS:
        return {"rules": result.data.get("rules", []), "total": result.data.get("total", 0)}
    raise HTTPException(status_code=500, detail=result.message)


@router.post("/mask-rules")
async def create_mask_rule_legacy(
    req: MaskRuleRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """兼容旧版 API: 创建脱敏规则"""
    result = await create_mask_rule_v1(req=req, db=db, user=user)
    if result.code == ErrorCode.SUCCESS:
        return {
            "success": True,
            "message": result.message,
        }
    raise HTTPException(status_code=400, detail=result.message)


@router.put("/mask-rules")
async def update_mask_rule_legacy(
    req: MaskRuleRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """兼容旧版 API: 更新脱敏规则"""
    result = await update_mask_rule_v1(req=req, db=db, user=user)
    if result.code == ErrorCode.SUCCESS:
        return {
            "success": True,
            "message": result.message,
        }
    raise HTTPException(status_code=400, detail=result.message)


@router.delete("/mask-rules/{table_name}")
async def delete_table_rules_legacy(
    table_name: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """兼容旧版 API: 删除表的脱敏规则"""
    result = await delete_table_rules_v1(table_name=table_name, db=db, user=user)
    if result.code == ErrorCode.SUCCESS:
        return {"success": True, "message": result.message}
    raise HTTPException(status_code=404, detail=result.message)


@router.post("/mask-rules/batch")
async def batch_create_rules_legacy(
    req: BatchMaskRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """兼容旧版 API: 批量创建脱敏规则"""
    result = await batch_create_rules_v1(req=req, db=db, user=user)
    if result.code == ErrorCode.SUCCESS:
        return {
            "success": result.data.get("success_count") == len(req.rules),
            "message": result.message,
            "errors": result.data.get("errors"),
        }
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/algorithms")
async def list_algorithms_legacy(user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取可用算法"""
    result = await list_algorithms_v1(user=user)
    if result.code == ErrorCode.SUCCESS:
        return result.data
    raise HTTPException(status_code=500, detail=result.message)


@router.get("/presets")
async def list_presets_legacy(user: TokenPayload = Depends(get_current_user)):
    """兼容旧版 API: 获取预设方案"""
    result = await list_presets_v1(user=user)
    if result.code == ErrorCode.SUCCESS:
        return result.data
    raise HTTPException(status_code=500, detail=result.message)


@router.post("/sync")
async def sync_rules_to_proxy_legacy(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """兼容旧版 API: 同步规则到 Proxy"""
    result = await sync_rules_to_proxy_v1(db=db, user=user)
    if result.code == ErrorCode.SUCCESS:
        return {
            "success": True,
            "message": result.message,
            "synced_count": result.data.get("synced_count"),
        }
    raise HTTPException(status_code=500, detail=result.message)
