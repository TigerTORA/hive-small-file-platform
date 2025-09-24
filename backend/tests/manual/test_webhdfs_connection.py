#!/usr/bin/env python3
"""
测试WebHDFS连接并发现HDFS信息
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

import logging

from app.monitor.webhdfs_scanner import WebHDFSScanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_webhdfs_connection():
    """测试WebHDFS连接"""

    # 尝试不同的WebHDFS端点
    test_configs = [
        {"url": "hdfs://nameservice1", "port": 9870, "desc": "标准WebHDFS端口"},
        {"url": "192.168.0.105", "port": 9870, "desc": "直接IP WebHDFS"},
        {"url": "192.168.0.105", "port": 50070, "desc": "旧版WebHDFS端口"},
    ]

    for config in test_configs:
        logger.info(f"\n测试 {config['desc']}: {config['url']}:{config['port']}")

        try:
            scanner = WebHDFSScanner(
                config["url"], user="hdfs", webhdfs_port=config["port"]
            )
            result = scanner.test_connection()

            logger.info(f"测试结果: {result}")

            if result["status"] == "success":
                logger.info(f"✅ WebHDFS 连接成功!")
                logger.info(f"WebHDFS URL: {result['webhdfs_url']}")
                logger.info(f"用户: {result['user']}")
                logger.info(f"根目录示例: {result.get('sample_paths', [])}")

                # 测试实际的表路径扫描
                test_paths = [
                    "/warehouse/tablespace/managed/hive/category",
                    "/user/hive/warehouse/hudi_cow",
                ]

                if scanner.connect():
                    for test_path in test_paths:
                        logger.info(f"\n测试扫描路径: {test_path}")
                        try:
                            stats = scanner.scan_directory(test_path)
                            if not stats.get("error"):
                                logger.info(f"  总文件数: {stats['total_files']}")
                                logger.info(f"  小文件数: {stats['small_files']}")
                                logger.info(
                                    f"  总大小: {stats['total_size'] / (1024**3):.2f} GB"
                                )
                                logger.info(
                                    f"  平均文件大小: {stats['avg_file_size'] / (1024**2):.2f} MB"
                                )
                                logger.info(
                                    f"  扫描时间: {stats['scan_duration']:.2f} 秒"
                                )
                            else:
                                logger.warning(f"  扫描错误: {stats['error']}")
                        except Exception as e:
                            logger.error(f"  扫描失败: {e}")

                    scanner.disconnect()
                    return True  # 找到可用的配置就返回

            else:
                logger.warning(f"❌ 连接失败: {result.get('message', 'Unknown error')}")

        except Exception as e:
            logger.error(f"❌ 测试过程出错: {e}")

    return False


if __name__ == "__main__":
    success = test_webhdfs_connection()
    if success:
        print("\n🎉 WebHDFS连接测试成功! 可以进行真实数据扫描。")
    else:
        print("\n💥 所有WebHDFS配置都无法连接，可能需要检查网络或端口配置。")
        sys.exit(1)
