"""
认证相关接口
"""
import hashlib
import hmac
import json
import time
import base64
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from atguigu.infrastructure.http_client import get_http_client
from atguigu.conf.config import settings
from atguigu.api.logger import logger

router = APIRouter(prefix="/api/auth", tags=["认证"])

# JWT 密钥（生产环境应使用环境变量）
JWT_SECRET = "finance-customer-service-secret-key-2024"


class LoginRequest(BaseModel):
    customer_no: str
    password: str


class LoginResponse(BaseModel):
    token: str
    customer_no: str
    customer_name: str


def generate_token(customer_no: str) -> str:
    """生成简单的 JWT token"""
    # Header
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')

    # Payload
    payload = {
        "sub": customer_no,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400,  # 24小时过期
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')

    # Signature
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_token(token: str) -> Optional[str]:
    """验证 token 并返回 customer_no"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        # 验证签名
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip('=')

        if signature_b64 != expected_sig_b64:
            return None

        # 解析 payload
        payload_json = base64.urlsafe_b64decode(payload_b64 + '==').decode()
        payload = json.loads(payload_json)

        # 检查过期时间
        if payload.get('exp', 0) < time.time():
            return None

        return payload.get('sub')
    except Exception:
        return None


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    登录接口（简化版：客户号即密码）
    验证客户号是否存在于 finance-data 服务
    """
    customer_no = request.customer_no.strip()
    password = request.password.strip()

    if not customer_no:
        raise HTTPException(status_code=400, detail="客户号不能为空")

    # 简化版验证：密码必须等于客户号
    if password != customer_no:
        raise HTTPException(status_code=401, detail="密码错误")

    try:
        # 调用 finance-data 服务验证客户号是否存在
        client = get_http_client()
        url = f"{settings.finance_api_base_url}/api/v1/customers/{customer_no}"
        headers = {
            "X-Channel-Code": "ONLINE_BANK",
            "Authorization": f"Bearer {customer_no}",
        }

        response = await client.get(url, headers=headers)
        data = response.json()

        if data.get("code") != 0:
            raise HTTPException(status_code=401, detail="客户号不存在")

        customer_data = data.get("data", {})
        customer_name = customer_data.get("customer_name", customer_no)

        # 生成 token
        token = generate_token(customer_no)

        logger.info(f"用户登录成功: {customer_no} ({customer_name})")

        return LoginResponse(
            token=token,
            customer_no=customer_no,
            customer_name=customer_name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录异常: {e}")
        raise HTTPException(status_code=500, detail="登录服务异常，请稍后重试")


@router.get("/verify")
async def verify(token: str):
    """验证 token 是否有效"""
    customer_no = verify_token(token)
    if not customer_no:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")
    return {"valid": True, "customer_no": customer_no}
