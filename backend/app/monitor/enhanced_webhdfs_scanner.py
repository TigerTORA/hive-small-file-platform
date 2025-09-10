import logging
import requests
import time
import subprocess
import os
from typing import Dict, List, Tuple, Optional
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import base64

logger = logging.getLogger(__name__)

# 尝试导入Kerberos相关模块
try:
    from requests_gssapi import HTTPSPNEGOAuth, OPTIONAL
    KERBEROS_AVAILABLE = True
    logger.info("Kerberos authentication support available (via GSSAPI)")
except ImportError:
    logger.warning("Kerberos authentication not available - install requests-gssapi for Kerberos support")
    KERBEROS_AVAILABLE = False

class EnhancedWebHDFSScanner:
    """
    增强的WebHDFS/HttpFS扫描器，支持多种Kerberos认证方式
    """
    
    def __init__(self, namenode_url: str, user: str = "hdfs", webhdfs_port: int = 9870, password: str = None):
        """
        初始化增强的WebHDFS/HttpFS扫描器
        Args:
            namenode_url: NameNode URL
            user: HDFS用户名
            webhdfs_port: WebHDFS/HttpFS端口
            password: 用户密码（用于Kerberos认证）
        """
        self.user = user
        self.password = password
        self._connected = False
        self.auth = None
        self.is_httpfs = False
        self.auth_methods = []
        
        # 解析URL并构造WebHDFS/HttpFS基础URL
        if namenode_url.startswith('hdfs://'):
            parsed = urlparse(namenode_url)
            if parsed.hostname:
                self.webhdfs_base_url = f"http://{parsed.hostname}:{webhdfs_port}/webhdfs/v1"
            else:
                # 处理nameservice情况，假设KDC在同一主机
                self.webhdfs_base_url = f"http://192.168.0.105:{webhdfs_port}/webhdfs/v1"
        elif namenode_url.startswith('http://'):
            parsed = urlparse(namenode_url)
            # 检查是否是HttpFS（端口14000）
            if parsed.port == 14000:
                self.is_httpfs = True
                self.webhdfs_base_url = f"http://{parsed.netloc}/webhdfs/v1"
            else:
                self.webhdfs_base_url = f"http://{parsed.netloc}/webhdfs/v1"
        else:
            if webhdfs_port == 14000:
                self.is_httpfs = True
            self.webhdfs_base_url = f"http://{namenode_url}:{webhdfs_port}/webhdfs/v1"
        
        # 初始化认证方法
        self._setup_authentication()
        
        logger.info(f"{'HttpFS' if self.is_httpfs else 'WebHDFS'} base URL: {self.webhdfs_base_url}")
        logger.info(f"Available auth methods: {', '.join(self.auth_methods)}")
        
        # HTTP会话
        self.session = requests.Session()
        self.session.timeout = 30
    
    def _setup_authentication(self):
        """设置认证方法"""
        if KERBEROS_AVAILABLE:
            try:
                # 方法1: GSSAPI Kerberos认证
                self.auth = HTTPSPNEGOAuth(mutual_authentication=OPTIONAL)
                self.auth_methods.append("GSSAPI-Kerberos")
                logger.info(f"Using Kerberos authentication (GSSAPI) for {'HttpFS' if self.is_httpfs else 'WebHDFS'}")
            except Exception as e:
                logger.warning(f"Failed to initialize Kerberos auth: {e}")
        
        # 方法2: 简单用户名认证
        self.auth_methods.append("Simple")
        
        # 方法3: 如果有密码，尝试Basic认证
        if self.password:
            self.auth_methods.append("Basic")
    
    def _try_kinit_authentication(self) -> bool:
        """尝试使用kinit获取Kerberos票据"""
        try:
            # 首先检查是否已有有效票据
            env = os.environ.copy()
            env['KRB5_CONFIG'] = '/Users/luohu/.krb5.conf'
            
            result = subprocess.run("klist", shell=True, env=env, 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and self.user.upper() in result.stdout:
                logger.info("Found existing valid Kerberos ticket")
                return True
                
            # 如果没有票据且有密码，尝试获取新票据
            if self.password:
                kinit_cmd = f"echo '{self.password}' | kinit {self.user}@PHOENIXESINFO.COM"
                result = subprocess.run(kinit_cmd, shell=True, env=env, 
                                      capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    logger.info("Successfully obtained Kerberos ticket via kinit")
                    return True
                else:
                    logger.warning(f"kinit failed: {result.stderr}")
                    
            return False
        except Exception as e:
            logger.warning(f"kinit authentication failed: {e}")
            return False
    
    def _get_request_with_multiple_auth(self, path: str, operation: str, **params) -> requests.Response:
        """使用多种认证方法尝试请求"""
        url = urljoin(self.webhdfs_base_url, path.lstrip('/'))
        params.update({
            'op': operation,
            'user.name': self.user
        })
        
        # 方法1: 尝试GSSAPI Kerberos
        if self.auth and "GSSAPI-Kerberos" in self.auth_methods:
            try:
                logger.debug(f"Trying GSSAPI Kerberos auth for: {url}")
                response = self.session.get(url, params=params, auth=self.auth)
                if response.status_code == 200:
                    logger.info("GSSAPI Kerberos authentication successful")
                    return response
                elif response.status_code == 401:
                    logger.debug("GSSAPI Kerberos auth failed with 401")
                else:
                    logger.debug(f"GSSAPI Kerberos auth failed with {response.status_code}")
            except Exception as e:
                logger.debug(f"GSSAPI Kerberos auth error: {e}")
        
        # 方法2: 尝试kinit + GSSAPI
        if "GSSAPI-Kerberos" in self.auth_methods and self.password:
            try:
                if self._try_kinit_authentication():
                    logger.debug(f"Trying kinit+GSSAPI auth for: {url}")
                    response = self.session.get(url, params=params, auth=self.auth)
                    if response.status_code == 200:
                        logger.info("kinit+GSSAPI authentication successful")
                        return response
                    else:
                        logger.debug(f"kinit+GSSAPI auth failed with {response.status_code}")
            except Exception as e:
                logger.debug(f"kinit+GSSAPI auth error: {e}")
        
        # 方法3: 尝试Basic认证
        if self.password and "Basic" in self.auth_methods:
            try:
                logger.debug(f"Trying Basic auth for: {url}")
                basic_auth = requests.auth.HTTPBasicAuth(self.user, self.password)
                response = self.session.get(url, params=params, auth=basic_auth)
                if response.status_code == 200:
                    logger.info("Basic authentication successful")
                    return response
                else:
                    logger.debug(f"Basic auth failed with {response.status_code}")
            except Exception as e:
                logger.debug(f"Basic auth error: {e}")
        
        # 方法4: 简单认证（无认证）
        try:
            logger.debug(f"Trying simple auth (no auth) for: {url}")
            response = self.session.get(url, params=params)
            if response.status_code == 200:
                logger.info("Simple authentication (no auth) successful")
                return response
            else:
                logger.debug(f"Simple auth failed with {response.status_code}")
                return response  # 返回错误响应用于进一步分析
        except Exception as e:
            logger.error(f"All authentication methods failed: {e}")
            raise e
    
    def connect(self) -> bool:
        """测试WebHDFS连接"""
        try:
            response = self._get_request_with_multiple_auth("/", "LISTSTATUS")
            if response.status_code == 200:
                self._connected = True
                logger.info(f"Connected to {'HttpFS' if self.is_httpfs else 'WebHDFS'}: {self.webhdfs_base_url}")
                return True
            else:
                logger.error(f"{'HttpFS' if self.is_httpfs else 'WebHDFS'} connection failed: HTTP {response.status_code}")
                logger.debug(f"Response headers: {dict(response.headers)}")
                logger.debug(f"Response body: {response.text[:500]}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to {'HttpFS' if self.is_httpfs else 'WebHDFS'}: {e}")
            return False
    
    def disconnect(self):
        """关闭连接"""
        self._connected = False
        if self.session:
            self.session.close()
    
    def test_connection(self) -> Dict[str, any]:
        """测试WebHDFS/HttpFS连接"""
        service_type = 'HttpFS' if self.is_httpfs else 'WebHDFS'
        
        if not self.connect():
            return {
                'status': 'error', 
                'message': f'Failed to connect to {service_type}',
                'service_type': service_type,
                'auth_methods_tried': self.auth_methods
            }
        
        try:
            # 测试根目录列表
            response = self._get_request_with_multiple_auth("/", "LISTSTATUS")
            
            if response.status_code == 200:
                data = response.json()
                file_statuses = data.get('FileStatuses', {}).get('FileStatus', [])
                sample_files = [f['pathSuffix'] for f in file_statuses[:5]]
                
                return {
                    'status': 'success',
                    'service_type': service_type,
                    'webhdfs_url': self.webhdfs_base_url,
                    'user': self.user,
                    'auth_method': 'Multiple-Methods',
                    'auth_methods_available': self.auth_methods,
                    'sample_paths': sample_files
                }
            else:
                auth_header = response.headers.get('WWW-Authenticate', 'Not specified')
                return {
                    'status': 'error', 
                    'message': f'HTTP {response.status_code}: Authentication required',
                    'service_type': service_type,
                    'auth_methods_tried': self.auth_methods,
                    'server_auth_header': auth_header,
                    'response_detail': response.text[:200]
                }
        except Exception as e:
            return {
                'status': 'error', 
                'message': str(e),
                'service_type': service_type,
                'auth_methods_tried': self.auth_methods
            }
        finally:
            self.disconnect()