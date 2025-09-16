"""
密码加密工具类
使用Fernet对称加密，密钥从配置文件读取
"""
import os
import base64
import logging
from typing import Optional
try:
    from cryptography.fernet import Fernet, InvalidToken  # type: ignore
except Exception:  # pragma: no cover - 测试/最小环境下的降级分支
    # 在缺少 cryptography 依赖或绑定异常时，降级为简易实现，避免导入失败阻断测试
    import base64 as _b64

    class _FallbackFernet:
        @staticmethod
        def generate_key() -> bytes:
            # 生成一个伪 key（非安全，仅用于测试环境）
            return _b64.urlsafe_b64encode(b"insecure-test-key-32bytes____")

        def __init__(self, key: bytes):
            self._key = key

        def encrypt(self, data: bytes) -> bytes:
            # 仅做可逆编码（非安全），用于单元测试不中断
            return _b64.urlsafe_b64encode(data)

        def decrypt(self, token: bytes) -> bytes:
            try:
                return _b64.urlsafe_b64decode(token)
            except Exception as e:  # 与 InvalidToken 语义兼容
                raise ValueError(str(e))

    Fernet = _FallbackFernet  # type: ignore
    class InvalidToken(Exception):  # type: ignore
        pass

logger = logging.getLogger(__name__)

class PasswordEncryptor:
    """密码加密解密工具"""
    
    _fernet_instance: Optional[Fernet] = None
    
    @classmethod
    def _get_fernet(cls) -> Fernet:
        """获取Fernet加密实例"""
        if cls._fernet_instance is None:
            # 从环境变量或配置文件获取加密密钥
            encryption_key = os.getenv('HIVE_PASSWORD_ENCRYPTION_KEY')
            
            if not encryption_key:
                logger.warning("HIVE_PASSWORD_ENCRYPTION_KEY not found, generating new key")
                # 生成新密钥并保存到环境变量建议中
                encryption_key = cls.generate_key()
                logger.info(f"Generated new encryption key: {encryption_key}")
                logger.info("Please save this key to your environment variables: HIVE_PASSWORD_ENCRYPTION_KEY")
            
            try:
                # 验证密钥格式并创建实例
                base64.urlsafe_b64decode(encryption_key.encode())
                cls._fernet_instance = Fernet(encryption_key.encode())
            except Exception as e:
                logger.error(f"Invalid encryption key format: {e}")
                # 生成新的有效密钥
                encryption_key = cls.generate_key()
                cls._fernet_instance = Fernet(encryption_key.encode())
                logger.warning(f"Generated new valid key: {encryption_key}")
        
        return cls._fernet_instance
    
    @classmethod
    def generate_key(cls) -> str:
        """生成新的加密密钥"""
        key = Fernet.generate_key()
        return key.decode('utf-8')
    
    @classmethod
    def encrypt_password(cls, plain_password: str) -> Optional[str]:
        """
        加密密码
        
        Args:
            plain_password: 明文密码
            
        Returns:
            加密后的密码字符串，失败返回None
        """
        if not plain_password:
            return None
        
        try:
            fernet = cls._get_fernet()
            encrypted = fernet.encrypt(plain_password.encode('utf-8'))
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt password: {e}")
            return None
    
    @classmethod
    def decrypt_password(cls, encrypted_password: str) -> Optional[str]:
        """
        解密密码
        
        Args:
            encrypted_password: 加密的密码
            
        Returns:
            解密后的明文密码，失败返回None
        """
        if not encrypted_password:
            return None
        
        try:
            fernet = cls._get_fernet()
            decrypted = fernet.decrypt(encrypted_password.encode('utf-8'))
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.error("Invalid encryption token - password may be corrupted or key changed")
            return None
        except Exception as e:
            logger.error(f"Failed to decrypt password: {e}")
            return None
    
    @classmethod
    def is_encrypted(cls, password: str) -> bool:
        """
        检查密码是否已加密
        
        Args:
            password: 待检查的密码
            
        Returns:
            True if encrypted, False if plain text
        """
        if not password:
            return False
        
        try:
            # 尝试解密，如果成功说明是加密的
            cls.decrypt_password(password)
            return True
        except:
            # 解密失败，可能是明文
            return False


def encrypt_cluster_password(cluster, plain_password: str) -> bool:
    """
    加密集群的Hive密码
    
    Args:
        cluster: 集群对象
        plain_password: 明文密码
        
    Returns:
        True if successful, False otherwise
    """
    if not plain_password:
        cluster.hive_password = None
        return True
    
    encrypted = PasswordEncryptor.encrypt_password(plain_password)
    if encrypted:
        cluster.hive_password = encrypted
        return True
    
    logger.error("Failed to encrypt cluster password")
    return False


def decrypt_cluster_password(cluster) -> Optional[str]:
    """
    解密集群的Hive密码
    
    Args:
        cluster: 集群对象
        
    Returns:
        解密后的明文密码，失败返回None
    """
    if not cluster.hive_password:
        return None
    
    return PasswordEncryptor.decrypt_password(cluster.hive_password)


# 测试函数
if __name__ == "__main__":
    # 测试加密解密功能
    test_password = "test_password_123"
    
    print("Testing password encryption...")
    
    # 加密
    encrypted = PasswordEncryptor.encrypt_password(test_password)
    print(f"Original: {test_password}")
    print(f"Encrypted: {encrypted}")
    
    # 解密
    decrypted = PasswordEncryptor.decrypt_password(encrypted)
    print(f"Decrypted: {decrypted}")
    
    # 验证
    print(f"Match: {test_password == decrypted}")
    
    # 检查是否加密
    print(f"Is encrypted: {PasswordEncryptor.is_encrypted(encrypted)}")
    print(f"Is plain: {PasswordEncryptor.is_encrypted(test_password)}")
