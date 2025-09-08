#!/usr/bin/env python3
"""
测试MySQL Hive MetaStore连接并发现数据库信息
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_mysql_metastore():
    """测试MySQL MetaStore连接"""
    # 使用提供的连接信息
    mysql_url = "mysql://root:!qaz2wsx3edC@192.168.0.105:3306/hive"
    
    logger.info(f"Testing connection to: {mysql_url}")
    
    try:
        connector = MySQLHiveMetastoreConnector(mysql_url)
        
        # 测试基本连接
        connection_result = connector.test_connection()
        logger.info(f"Connection test result: {connection_result}")
        
        if connection_result['status'] == 'success':
            logger.info(f"✅ 成功连接到 Hive MetaStore!")
            logger.info(f"总数据库数: {connection_result['total_databases']}")
            logger.info(f"总表数: {connection_result['total_tables']}")
            logger.info(f"样例数据库: {connection_result['sample_databases']}")
            
            # 获取完整的数据库列表
            with connector:
                databases = connector.get_databases()
                logger.info(f"所有数据库 ({len(databases)}个):")
                for db in databases:
                    logger.info(f"  - {db}")
                
                # 选择一个数据库查看表信息
                if databases:
                    test_db = databases[0]  # 使用第一个数据库
                    logger.info(f"\n检查数据库 '{test_db}' 中的表:")
                    tables = connector.get_tables(test_db)
                    logger.info(f"找到 {len(tables)} 个表:")
                    
                    for i, table in enumerate(tables[:10]):  # 只显示前10个表
                        logger.info(f"  {i+1}. {table['table_name']} ({table['table_type']})")
                        logger.info(f"     路径: {table['table_path']}")
                        logger.info(f"     分区表: {'是' if table['is_partitioned'] else '否'}")
                        if table['is_partitioned']:
                            logger.info(f"     分区数: {table['partition_count']}")
                        logger.info("")
                    
                    if len(tables) > 10:
                        logger.info(f"  ... 还有 {len(tables) - 10} 个表")
                    
                    # 测试分区表
                    partitioned_tables = [t for t in tables if t['is_partitioned']]
                    if partitioned_tables:
                        test_table = partitioned_tables[0]
                        logger.info(f"\n测试分区表 '{test_table['table_name']}' 的分区信息:")
                        partitions = connector.get_table_partitions(test_db, test_table['table_name'])
                        logger.info(f"找到 {len(partitions)} 个分区:")
                        for i, partition in enumerate(partitions[:5]):  # 只显示前5个分区
                            logger.info(f"  {i+1}. {partition['partition_name']}")
                            logger.info(f"     路径: {partition['partition_path']}")
                        if len(partitions) > 5:
                            logger.info(f"  ... 还有 {len(partitions) - 5} 个分区")
            
        else:
            logger.error(f"❌ 连接失败: {connection_result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试过程出错: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_mysql_metastore()
    if success:
        print("\n🎉 测试完成! MetaStore连接正常，可以开始真实数据扫描。")
    else:
        print("\n💥 测试失败! 请检查连接信息或网络配置。")
        sys.exit(1)