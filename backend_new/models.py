from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Float, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

class Cluster(Base):
    __tablename__ = "clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    hive_metastore_url = Column(String(500), nullable=False)
    hdfs_namenode_url = Column(String(500), nullable=False)
    small_file_threshold = Column(Integer, default=128*1024*1024)  # 128MB
    created_time = Column(DateTime, server_default=func.now())

class TableMetric(Base):
    __tablename__ = "table_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    database_name = Column(String(100), nullable=False)
    table_name = Column(String(200), nullable=False)
    table_path = Column(String(500), nullable=False)
    total_files = Column(Integer, default=0)
    small_files = Column(Integer, default=0)
    total_size = Column(BigInteger, default=0)
    avg_file_size = Column(Float, default=0.0)
    scan_time = Column(DateTime, server_default=func.now())

# Database setup
DATABASE_URL = "sqlite:///./hive_platform.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()