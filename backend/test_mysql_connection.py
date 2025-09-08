#!/usr/bin/env python3
"""
测试 MySQL Hive MetaStore 连接
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.monitor.mysql_hive_connector import MySQLHiveMetastoreConnector

def test_mysql_connection():
    """测试 MySQL 连接"""
    
    # 您的 MySQL 连接信息
    mysql_url = "mysql://root:!qaz2wsx3edC@192.168.0.105:3306/hive"
    
    print("🔗 测试 MySQL Hive MetaStore 连接...")
    print(f"连接地址: 192.168.0.105:3306")
    print(f"数据库: hive")
    print("-" * 50)
    
    try:
        connector = MySQLHiveMetastoreConnector(mysql_url)
        result = connector.test_connection()
        
        if result['status'] == 'success':
            print("✅ 连接成功！")
            print(f"📊 数据库数量: {result['total_databases']}")
            print(f"📋 表总数: {result['total_tables']}")
            print(f"🗂️  可用数据库: {', '.join(result['sample_databases'])}")
            return True
        else:
            print("❌ 连接失败！")
            print(f"错误信息: {result['message']}")
            return False
            
    except Exception as e:
        print("❌ 连接测试出错！")
        print(f"错误详情: {str(e)}")
        return False

def test_database_queries():
    """测试数据库查询功能"""
    mysql_url = "mysql://root:!qaz2wsx3edC@192.168.0.105:3306/hive"
    
    print("\n🔍 测试数据库查询功能...")
    print("-" * 50)
    
    try:
        with MySQLHiveMetastoreConnector(mysql_url) as connector:
            # 获取数据库列表
            databases = connector.get_databases()
            print(f"📁 找到 {len(databases)} 个数据库:")
            for db in databases[:10]:  # 只显示前10个
                print(f"  - {db}")
            
            # 如果有数据库，测试获取表信息
            if databases:
                test_db = databases[0]
                print(f"\n📋 测试数据库 '{test_db}' 中的表:")
                tables = connector.get_tables(test_db)
                print(f"  找到 {len(tables)} 个表")
                
                # 显示前5个表的信息
                for table in tables[:5]:
                    print(f"  - {table['table_name']} ({table['table_type']}) "
                          f"{'[分区表]' if table['is_partitioned'] else '[普通表]'}")
                    
                return True
            else:
                print("⚠️  没有找到可用的数据库")
                return False
                
    except Exception as e:
        print("❌ 查询测试失败！")
        print(f"错误详情: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 MySQL Hive MetaStore 连接测试")
    print("=" * 60)
    
    # 测试基本连接
    connection_ok = test_mysql_connection()
    
    if connection_ok:
        # 测试查询功能
        query_ok = test_database_queries()
        
        if query_ok:
            print("\n🎉 所有测试通过！可以开始配置集群了。")
        else:
            print("\n⚠️  连接正常但查询有问题，请检查权限。")
    else:
        print("\n💡 连接失败，请检查：")
        print("  1. MySQL 服务是否启动")
        print("  2. 网络连接是否正常") 
        print("  3. 用户名密码是否正确")
        print("  4. 数据库名称是否为 'hive'")