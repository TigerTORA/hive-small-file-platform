#!/usr/bin/env python3
"""
设置演示集群配置
在主数据库中添加真实的集群配置
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.cluster import Cluster
from app.config.database import Base
from app.config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_demo_cluster():
    """设置演示集群"""
    # 使用主数据库
    engine = create_engine(settings.DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()
    
    try:
        # 检查是否已存在相同名称的集群
        existing_cluster = db_session.query(Cluster).filter(
            Cluster.name == "CDP真实集群"
        ).first()
        
        if existing_cluster:
            logger.info(f"集群已存在: {existing_cluster.name} (ID: {existing_cluster.id})")
            logger.info("更新集群配置...")
            
            # 更新配置
            existing_cluster.hive_metastore_url = "mysql://root:!qaz2wsx3edC@192.168.0.105:3306/hive"
            existing_cluster.hdfs_namenode_url = "hdfs://nameservice1"
            existing_cluster.hdfs_user = "hdfs"
            existing_cluster.small_file_threshold = 128*1024*1024
            existing_cluster.description = "连接到192.168.0.105的真实CDP集群，支持混合HDFS扫描"
            
            db_session.commit()
            logger.info(f"✅ 集群配置已更新: {existing_cluster.name}")
            return existing_cluster
        
        else:
            # 创建新集群
            cluster = Cluster(
                name="CDP真实集群",
                description="连接到192.168.0.105的真实CDP集群，支持混合HDFS扫描",
                hive_host="192.168.0.105",
                hive_port=10000,
                hive_database="default",
                hive_metastore_url="mysql://root:!qaz2wsx3edC@192.168.0.105:3306/hive",
                hdfs_namenode_url="hdfs://nameservice1",
                hdfs_user="hdfs",
                small_file_threshold=128*1024*1024,  # 128MB
                status="active",
                scan_enabled=True
            )
            
            db_session.add(cluster)
            db_session.commit()
            db_session.refresh(cluster)
            logger.info(f"✅ 创建新集群: {cluster.name} (ID: {cluster.id})")
            return cluster
        
    except Exception as e:
        logger.error(f"设置演示集群失败: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()

def test_demo_apis():
    """测试演示API"""
    import requests
    import json
    
    base_url = "http://localhost:8000"
    
    try:
        # 测试健康检查
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            logger.info("✅ API服务正常运行")
        else:
            logger.warning("⚠️ API服务可能未启动")
            return
        
        # 测试集群列表
        response = requests.get(f"{base_url}/api/v1/clusters/")
        if response.status_code == 200:
            clusters = response.json()
            logger.info(f"📋 发现 {len(clusters)} 个集群:")
            for cluster in clusters:
                logger.info(f"  - {cluster['name']} (ID: {cluster['id']})")
            
            if clusters:
                cluster_id = clusters[0]['id']
                
                # 测试真实连接
                logger.info(f"\n🔌 测试集群 {cluster_id} 的真实连接...")
                response = requests.get(f"{base_url}/api/v1/tables/test-connection-real/{cluster_id}")
                if response.status_code == 200:
                    result = response.json()
                    logger.info("连接测试结果:")
                    logger.info(f"  MetaStore: {result['connections']['metastore']['status']}")
                    logger.info(f"  HDFS: {result['connections']['hdfs']['status']} ({result['connections']['hdfs'].get('mode', 'unknown')})")
                
                # 测试数据库列表
                logger.info(f"\n📚 获取集群 {cluster_id} 的数据库列表...")
                response = requests.get(f"{base_url}/api/v1/tables/databases/{cluster_id}")
                if response.status_code == 200:
                    result = response.json()
                    databases = result.get('databases', [])
                    logger.info(f"发现 {len(databases)} 个数据库: {databases[:5]}")
                    
                    if 'default' in databases:
                        # 测试表列表
                        logger.info(f"\n📊 获取default数据库的表列表...")
                        response = requests.get(f"{base_url}/api/v1/tables/tables/{cluster_id}/default")
                        if response.status_code == 200:
                            result = response.json()
                            tables = result.get('tables', [])
                            logger.info(f"default数据库有 {len(tables)} 个表")
                            for table in tables[:3]:
                                logger.info(f"  - {table['table_name']} ({'分区表' if table['is_partitioned'] else '非分区表'})")
                
        else:
            logger.warning("无法获取集群列表")
            
    except requests.exceptions.ConnectionError:
        logger.warning("⚠️ 无法连接到API服务，请确保后端服务正在运行")
        logger.info("启动命令: cd backend && uvicorn app.main:app --reload --port 8000")
    except Exception as e:
        logger.error(f"API测试失败: {e}")

if __name__ == "__main__":
    logger.info("🚀 设置演示集群配置")
    
    try:
        cluster = setup_demo_cluster()
        logger.info(f"\n✅ 演示集群设置完成!")
        logger.info(f"集群名称: {cluster.name}")
        logger.info(f"集群ID: {cluster.id}")
        logger.info(f"MetaStore: {cluster.hive_metastore_url}")
        logger.info(f"HDFS: {cluster.hdfs_namenode_url}")
        
        logger.info(f"\n🧪 现在可以使用以下API进行测试:")
        logger.info(f"1. 连接测试: GET /api/v1/tables/test-connection-real/{cluster.id}")
        logger.info(f"2. 数据库列表: GET /api/v1/tables/databases/{cluster.id}")
        logger.info(f"3. 表列表: GET /api/v1/tables/tables/{cluster.id}/default")
        logger.info(f"4. 真实扫描: POST /api/v1/tables/scan-real/{cluster.id}/default")
        
        logger.info(f"\n🌐 测试API服务连接...")
        test_demo_apis()
        
    except Exception as e:
        logger.error(f"💥 设置失败: {e}")
        sys.exit(1)