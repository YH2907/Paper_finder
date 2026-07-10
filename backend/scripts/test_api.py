"""API 测试脚本"""
import httpx
import json

BASE_URL = "http://localhost:8000"


def test_health():
    """测试健康检查"""
    response = httpx.get(f"{BASE_URL}/api/v1/health")
    print(f"✅ 健康检查: {response.json()}")


def test_register():
    """测试用户注册"""
    response = httpx.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "name": "测试用户",
            "password": "Test123456",
        },
    )
    print(f"📝 注册: {response.status_code} - {response.json()}")
    return response


def test_login():
    """测试用户登录"""
    response = httpx.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "email": "demo@example.com",
            "password": "Demo123456",
        },
    )
    print(f"🔐 登录: {response.status_code} - {response.json()}")
    if response.status_code == 200:
        return response.json().get("data", {}).get("access_token")
    return None


def test_topics(token: str):
    """测试主题列表"""
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.get(f"{BASE_URL}/api/v1/topics/", headers=headers)
    print(f"📋 主题列表: {response.status_code} - {response.json()}")


def test_papers(token: str):
    """测试论文列表"""
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.get(f"{BASE_URL}/api/v1/papers/", headers=headers)
    print(f"📄 论文列表: {response.status_code} - {response.json()}")


def main():
    """运行所有测试"""
    print("🧪 开始 API 测试...\n")
    
    # 健康检查
    test_health()
    print()
    
    # 用户注册
    test_register()
    print()
    
    # 用户登录
    token = test_login()
    if token:
        print(f"   Token: {token[:20]}...\n")
        
        # 主题列表
        test_topics(token)
        print()
        
        # 论文列表
        test_papers(token)
        print()
    
    print("✨ 测试完成!")


if __name__ == "__main__":
    main()
