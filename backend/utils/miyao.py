"""生成 Fernet 对称密钥的工具脚本。

用法：
    python utils/miyao.py

将输出粘贴到 .env 的 ENCRYPTION_KEY= 后即可。
本脚本只负责生成随机密钥，不在代码中保存任何明文密钥。
"""
import base64
import os


def generate_key() -> str:
    """生成一个 32 字节、urlsafe base64 编码的 Fernet 密钥。"""
    return base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')


if __name__ == '__main__':
    key = generate_key()
    print('ENCRYPTION_KEY=' + key)
    print('（请将上面一行写入 .env 文件，不要在源码中硬编码）')
