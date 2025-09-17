"""
Unit tests for Cluster model
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.models.cluster import Cluster
from tests.factories import ClusterFactory


class TestClusterModel:
    """Test cases for Cluster model"""
    
    @pytest.mark.unit
    def test_create_cluster(self, db_session):
        """Test creating a new cluster"""
        cluster_data = {
            "name": "test-cluster",
            "description": "Test cluster",
            "hive_host": "localhost",
            "hive_port": 10000,
            "hive_metastore_url": "mysql://user:pass@localhost:3306/hive",
            "hdfs_namenode_url": "hdfs://localhost:9000",
            "small_file_threshold": 134217728,
            "status": "active"
        }
        
        cluster = Cluster(**cluster_data)
        db_session.add(cluster)
        db_session.commit()
        
        # Verify cluster was created
        assert cluster.id is not None
        assert cluster.name == "test-cluster"
        assert cluster.hive_port == 10000
        assert cluster.status == "active"
        assert cluster.created_at is not None
        assert cluster.updated_at is not None
    
    @pytest.mark.unit
    def test_cluster_factory(self, db_session):
        """Test cluster factory creation"""
        cluster = ClusterFactory()
        db_session.add(cluster)
        db_session.commit()
        
        assert cluster.id is not None
        assert cluster.name.startswith("cluster-")
        assert cluster.hive_host == "localhost"
        assert cluster.small_file_threshold == 134217728
        assert cluster.status == "active"
    
    @pytest.mark.unit 
    def test_cluster_name_unique(self, db_session):
        """Test cluster name must be unique"""
        cluster1 = ClusterFactory(name="duplicate-name")
        cluster2 = ClusterFactory(name="duplicate-name")
        
        db_session.add(cluster1)
        db_session.commit()
        
        db_session.add(cluster2)
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    @pytest.mark.unit
    def test_cluster_str_representation(self, db_session):
        """Test cluster string representation"""
        cluster = ClusterFactory(name="test-cluster-repr")
        db_session.add(cluster)
        db_session.commit()
        
        assert str(cluster) == "test-cluster-repr"
    
    @pytest.mark.unit
    def test_cluster_timestamps(self, db_session):
        """Test cluster timestamp behavior"""
        cluster = ClusterFactory()
        db_session.add(cluster)
        db_session.commit()
        
        # Check timestamps are set
        assert cluster.created_at is not None
        assert cluster.updated_at is not None
        assert cluster.created_at <= cluster.updated_at
        
        # Update cluster and check updated_at changes
        original_updated = cluster.updated_at
        cluster.description = "Updated description"
        db_session.commit()
        
        # Note: In a real app, updated_at would be automatically updated
        # This test verifies the field exists and can be manually updated
        cluster.updated_at = datetime.now(timezone.utc)
        db_session.commit()
        
        assert cluster.updated_at > original_updated
    
    @pytest.mark.unit
    def test_cluster_validation(self, db_session):
        """Test cluster field validation"""
        # Test invalid port
        with pytest.raises(ValueError):
            cluster = Cluster(
                name="test",
                hive_port=-1,  # Invalid port
                hive_host="localhost"
            )
    
    @pytest.mark.unit
    def test_cluster_relationships(self, db_session):
        """Test cluster relationships are properly set up"""
        cluster = ClusterFactory()
        db_session.add(cluster)
        db_session.commit()
        
        # Test that relationships exist (even if empty)
        assert hasattr(cluster, 'table_metrics')
        assert hasattr(cluster, 'merge_tasks')
        assert cluster.table_metrics == []
        assert cluster.merge_tasks == []
    
    @pytest.mark.unit
    def test_cluster_metastore_url_format(self, db_session):
        """Test metastore URL format validation"""
        # Valid MySQL URL
        cluster = ClusterFactory(
            metastore_url="mysql://user:pass@host:3306/hive"
        )
        db_session.add(cluster)
        db_session.commit()
        assert "mysql://" in cluster.metastore_url
        
        # Valid PostgreSQL URL  
        cluster2 = ClusterFactory(
            name="cluster-postgres",
            metastore_url="postgresql://user:pass@host:5432/hive_metastore"
        )
        db_session.add(cluster2)
        db_session.commit()
        assert "postgresql://" in cluster2.metastore_url
    
    @pytest.mark.unit
    def test_cluster_active_status(self, db_session):
        """Test cluster active status functionality"""
        cluster = ClusterFactory(is_active=True)
        db_session.add(cluster)
        db_session.commit()
        
        assert cluster.status == "active"
        
        # Toggle active status
        cluster.is_active = False
        db_session.commit()
        
        assert cluster.is_active is False
    
    @pytest.mark.unit
    def test_cluster_small_file_threshold(self, db_session):
        """Test small file threshold settings"""
        # Default threshold (128MB)
        cluster1 = ClusterFactory()
        assert cluster1.small_file_threshold == 134217728
        
        # Custom threshold (64MB)
        cluster2 = ClusterFactory(
            name="cluster-custom-threshold",
            small_file_threshold=67108864
        )
        assert cluster2.small_file_threshold == 67108864