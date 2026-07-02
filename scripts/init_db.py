"""
初始化数据库
"""
import sys
sys.path.append('/b/agent/MyCode/personal-invest-assistant/backend')

from app.utils.db import engine, Base
from app.models import Fund, IndexDaily, FundFlow, AdviceRecord

def init_db():
    """创建所有表"""
    print("开始初始化数据库...")
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成！")

if __name__ == "__main__":
    init_db()
