"""
集中管理应用版本号

提供统一的版本来源，供设置界面展示与启动时更新检查使用。
"""

# 当前应用版本号（仅数字与点，外观显示时可加前缀`v`）
__version__ = "1.0.0"

def normalize_version(v: str) -> str:
    """规范化版本字符串，去掉前缀v/V并保留数字与点"""
    v = (v or "").strip()
    if v.lower().startswith("v"):
        v = v[1:]
    # 只保留数字与点
    import re
    m = re.findall(r"[0-9]+(?:\.[0-9]+)*", v)
    return m[0] if m else "0"

def compare_versions(a: str, b: str) -> int:
    """比较两个版本，返回-1(a<b)、0(a==b)、1(a>b)"""
    def parse(x: str):
        x = normalize_version(x)
        return [int(p) for p in x.split('.') if p.isdigit()]
    pa, pb = parse(a), parse(b)
    # 对齐长度
    max_len = max(len(pa), len(pb))
    pa += [0] * (max_len - len(pa))
    pb += [0] * (max_len - len(pb))
    if pa < pb:
        return -1
    if pa > pb:
        return 1
    return 0

