"""
执行SQL脚本，创建计划工作量统计所需的表并插入测试数据
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 加载环境变量
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# 获取数据库配置
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL 环境变量未设置")

# 创建数据库引擎
engine = create_engine(database_url)

print(f"连接数据库: {database_url}")
print("=" * 60)

# 读取SQL文件
sql_file_path = os.path.join(os.path.dirname(__file__), 'create_plan_workload_tables.sql')
with open(sql_file_path, 'r', encoding='utf-8') as f:
    sql_script = f.read()

# 分割SQL语句（按分号分割）
sql_statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]

# 执行每条SQL语句
with engine.connect() as connection:
    for i, sql_statement in enumerate(sql_statements, 1):
        try:
            # 跳过注释
            if sql_statement.startswith('--'):
                continue
            
            print(f"\n执行第 {i} 条SQL语句...")
            # print(f"SQL: {sql_statement[:100]}...")
            
            result = connection.execute(text(sql_statement))
            
            # 如果是查询语句，输出结果
            if sql_statement.strip().upper().startswith('SELECT'):
                rows = result.fetchall()
                if rows:
                    print("\n查询结果:")
                    for row in rows:
                        print(f"  {row}")
            else:
                print(f"✅ 执行成功")
                
            connection.commit()
            
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            print(f"SQL: {sql_statement[:200]}...")

print("\n" + "=" * 60)
print("SQL脚本执行完成！")
print("测试数据已插入到数据库中。")
