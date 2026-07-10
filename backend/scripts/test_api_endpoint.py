"""快速验证推荐 API 端点

启动服务器后运行此脚本测试 API 响应。

使用方法：
    # 先启动服务器
    cd backend && python -m app.main
    
    # 然后运行此脚本
    python -m scripts.test_api_endpoint
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"


def test_health():
    """测试健康检查"""
    print("测试健康检查...")
    try:
        resp = requests.get("http://localhost:8000/health", timeout=5)
        print(f"  状态码: {resp.status_code}")
        print(f"  响应: {resp.json()}")
        return resp.status_code == 200
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


def test_recommendations(token: str):
    """测试推荐端点"""
    print("\n测试推荐端点...")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # 测试推荐
        resp = requests.get(
            f"{BASE_URL}/papers/recommended",
            params={"limit": 5, "online": True, "only_unseen": False},
            headers=headers,
            timeout=60,
        )
        print(f"  状态码: {resp.status_code}")
        data = resp.json()
        print(f"  成功: {data.get('success')}")

        papers = data.get("data", [])
        print(f"  推荐论文数量: {len(papers)}")

        for i, paper in enumerate(papers[:3], 1):
            print(f"\n  论文 {i}:")
            print(f"    标题: {paper.get('title', 'N/A')[:80]}")
            print(f"    来源: {paper.get('source', 'N/A')}")

        return resp.status_code == 200
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


def test_papers_list(token: str):
    """测试论文列表端点"""
    print("\n测试论文列表端点...")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.get(
            f"{BASE_URL}/papers/",
            params={"page": 1, "per_page": 5},
            headers=headers,
            timeout=30,
        )
        print(f"  状态码: {resp.status_code}")
        data = resp.json()
        print(f"  成功: {data.get('success')}")

        papers_data = data.get("data", {})
        print(f"  总论文数: {papers_data.get('total', 0)}")

        papers = papers_data.get("papers", [])
        print(f"  返回论文数: {len(papers)}")

        return resp.status_code == 200
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


def main():
    """运行 API 测试"""
    print("=" * 60)
    print("API 端点测试")
    print("=" * 60)

    # 测试健康检查
    if not test_health():
        print("\n❌ 服务器未运行，请先启动服务器")
        print("   cd backend && python -m app.main")
        return False

    # 获取 token（需要先登录或注册）
    print("\n注意: 需要有效的 JWT token 才能测试论文端点")
    print("请在浏览器中登录后，从开发者工具获取 token")
    print("或使用以下命令获取测试 token:")
    print('  curl -X POST http://localhost:8000/api/v1/auth/login \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"email": "test@example.com", "password": "password"}\'')

    # 如果提供了 token 参数
    if len(sys.argv) > 1:
        token = sys.argv[1]
        print(f"\n使用提供的 token 进行测试...")

        results = {}
        results["论文列表"] = test_papers_list(token)
        results["推荐论文"] = test_recommendations(token)

        # 汇总
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)

        all_passed = True
        for test_name, passed in results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"  {test_name}: {status}")
            if not passed:
                all_passed = False

        return all_passed
    else:
        print("\n跳过需要认证的测试（未提供 token）")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
