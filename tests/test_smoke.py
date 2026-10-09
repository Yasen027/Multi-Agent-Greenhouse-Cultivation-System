"""基础冒烟测试：验证应用可启动并响应健康检查。"""

from fastapi.testclient import TestClient

from backend.app.main import app


def test_health():
    """健康检查接口应返回 200 与 ok 状态。"""
    r = TestClient(app).get('/api/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'
