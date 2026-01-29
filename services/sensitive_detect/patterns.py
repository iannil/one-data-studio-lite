"""敏感数据检测 - 正则模式库 (中国大陆常见敏感数据)"""

import re

# ========== 敏感数据正则表达式 ==========

PATTERNS = {
    "phone": {
        "name": "手机号码",
        "pattern": re.compile(r"1[3-9]\d{9}"),
        "level": "high",
        "description": "中国大陆手机号码",
    },
    "id_card": {
        "name": "身份证号码",
        "pattern": re.compile(
            r"[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]"
        ),
        "level": "critical",
        "description": "18位居民身份证号码",
    },
    "email": {
        "name": "邮箱地址",
        "pattern": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        "level": "medium",
        "description": "电子邮箱地址",
    },
    "bank_card": {
        "name": "银行卡号",
        "pattern": re.compile(r"(?:62|4|5)\d{14,18}"),
        "level": "critical",
        "description": "银联/Visa/MasterCard 银行卡号",
    },
    "ip_address": {
        "name": "IP地址",
        "pattern": re.compile(
            r"(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)"
        ),
        "level": "low",
        "description": "IPv4 地址",
    },
    "passport": {
        "name": "护照号码",
        "pattern": re.compile(r"[A-Z]\d{8}|[a-zA-Z]{2}\d{7}"),
        "level": "high",
        "description": "中国护照号码",
    },
    "license_plate": {
        "name": "车牌号",
        "pattern": re.compile(
            r"[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}"
        ),
        "level": "medium",
        "description": "中国大陆车牌号",
    },
    "chinese_name": {
        "name": "中文姓名",
        # 简化判断：2-4个汉字可能是姓名（需要结合字段名判断）
        "pattern": re.compile(r"^[\u4e00-\u9fa5]{2,4}$"),
        "level": "medium",
        "description": "中文姓名（需结合字段名判断）",
    },
    "address": {
        "name": "地址",
        "pattern": re.compile(
            r"[\u4e00-\u9fa5]{2,}(?:省|市|区|县|镇|乡|村|路|街|巷|号|栋|单元|室)"
        ),
        "level": "medium",
        "description": "中国大陆地址信息",
    },
}

# 字段名关键词（辅助判断）
SENSITIVE_FIELD_KEYWORDS = {
    "critical": ["id_card", "idcard", "身份证", "sfzh", "certno", "bank_card", "bankcard", "银行卡"],
    "high": ["phone", "mobile", "手机", "tel", "电话", "password", "密码", "passwd", "secret"],
    "medium": ["email", "邮箱", "address", "地址", "name", "姓名", "real_name", "真实姓名"],
    "low": ["ip", "ip_address", "user_agent"],
}


def detect_by_pattern(value: str) -> list[dict]:
    """使用正则表达式检测敏感数据"""
    matches = []
    for key, info in PATTERNS.items():
        if info["pattern"].search(str(value)):
            matches.append({
                "type": key,
                "name": info["name"],
                "level": info["level"],
                "description": info["description"],
            })
    return matches


def detect_by_field_name(field_name: str) -> str | None:
    """根据字段名判断敏感级别"""
    field_lower = field_name.lower()
    for level, keywords in SENSITIVE_FIELD_KEYWORDS.items():
        for kw in keywords:
            if kw in field_lower:
                return level
    return None
