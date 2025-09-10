#!/usr/bin/env python3
"""
直接测试HttpFS + Kerberos连接
"""
import os
import requests
from requests_gssapi import HTTPSPNEGOAuth, OPTIONAL
import subprocess

def test_kerberos_ticket():
    """检查Kerberos票据"""
    try:
        env = os.environ.copy()
        env['KRB5_CONFIG'] = '/Users/luohu/.krb5.conf'
        
        result = subprocess.run("klist", shell=True, env=env, 
                              capture_output=True, text=True, timeout=5)
        
        print(f"klist exit code: {result.returncode}")
        print(f"klist output: {result.stdout}")
        if result.stderr:
            print(f"klist error: {result.stderr}")
            
        return result.returncode == 0 and "hdfs@PHOENIXESINFO.COM" in result.stdout
    except Exception as e:
        print(f"Error checking Kerberos ticket: {e}")
        return False

def test_httpfs_connection():
    """测试HttpFS连接"""
    # 使用主机名，因为我们有该主机名的HTTP服务票据
    url = "http://cdpmaster1.phoenixesinfo.com:14000/webhdfs/v1/?op=LISTSTATUS&user.name=hdfs"
    
    try:
        # 设置环境变量
        os.environ['KRB5_CONFIG'] = '/Users/luohu/.krb5.conf'
        
        # 创建GSSAPI认证
        auth = HTTPSPNEGOAuth(mutual_authentication=OPTIONAL)
        
        print(f"Testing URL: {url}")
        print(f"Using GSSAPI auth: {auth}")
        
        # 发送请求，使用IP地址但设置正确的Host头
        headers = {'Host': 'cdpmaster1.phoenixesinfo.com:14000'}
        # 实际请求使用IP地址
        actual_url = url.replace('cdpmaster1.phoenixesinfo.com', '192.168.0.105')
        
        print(f"Actual URL: {actual_url}")
        print(f"Host header: {headers['Host']}")
        
        response = requests.get(actual_url, auth=auth, headers=headers, timeout=30)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body (first 500 chars): {response.text[:500]}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error testing HttpFS connection: {e}")
        return False

def main():
    print("=== HttpFS + Kerberos 直接测试 ===")
    
    print("\n1. 检查Kerberos票据...")
    if test_kerberos_ticket():
        print("✅ Kerberos票据有效")
    else:
        print("❌ Kerberos票据无效或不存在")
        return
    
    print("\n2. 测试HttpFS连接...")
    if test_httpfs_connection():
        print("✅ HttpFS连接成功！")
    else:
        print("❌ HttpFS连接失败")

if __name__ == "__main__":
    main()