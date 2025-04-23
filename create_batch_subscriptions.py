import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import sys

# 加载环境变量
load_dotenv()

# 获取数据库配置
db_config = {
    "host": os.getenv("DEV_DB_HOST", "localhost"),
    "user": os.getenv("DEV_DB_USER", "root"),
    "password": os.getenv("DEV_DB_PASSWORD", "610428"),
    "database": os.getenv("DEV_DB_NAME", "ai"),
    "port": int(os.getenv("DEV_DB_PORT", "100"))
}

def get_subscription_plans():
    """获取所有可用的订阅计划"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, duration_days, price FROM subscription_plans")
        plans = cursor.fetchall()
        return plans
    except mysql.connector.Error as err:
        print(f"获取订阅计划失败: {err}")
        return []
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def parse_user_ids(input_str):
    """解析用户ID输入，支持单个ID和范围格式"""
    user_ids = []
    parts = input_str.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            # 处理范围格式
            try:
                start, end = map(int, part.split('-'))
                if start > end:
                    print(f"警告：范围 {part} 的起始值大于结束值，已自动调整")
                    start, end = end, start
                user_ids.extend(range(start, end + 1))
            except ValueError:
                print(f"警告：无效的范围格式 '{part}'，已跳过")
        else:
            # 处理单个ID
            try:
                user_ids.append(int(part))
            except ValueError:
                print(f"警告：无效的用户ID '{part}'，已跳过")
    
    return list(set(user_ids))  # 去重

def create_subscriptions(user_ids, plan_id):
    """为指定用户创建订阅"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 获取订阅计划信息
        cursor.execute("SELECT duration_days FROM subscription_plans WHERE id = %s", (plan_id,))
        plan = cursor.fetchone()
        if not plan:
            print("订阅计划不存在")
            return False
        
        duration_days = plan[0]
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_days)
        
        # 为每个用户创建订阅
        success_count = 0
        for user_id in user_ids:
            try:
                cursor.execute(
                    "INSERT INTO user_subscriptions (user_id, plan_id, start_date, end_date, status) "
                    "VALUES (%s, %s, %s, %s, 'active')",
                    (user_id, plan_id, start_date, end_date)
                )
                success_count += 1
            except mysql.connector.Error as err:
                print(f"为用户 {user_id} 创建订阅失败: {err}")
        
        conn.commit()
        print(f"成功为 {success_count} 个用户创建订阅")
        return True
        
    except mysql.connector.Error as err:
        print(f"创建订阅失败: {err}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def main():
    # 显示所有可用的订阅计划
    plans = get_subscription_plans()
    if not plans:
        print("没有可用的订阅计划")
        return
    
    print("\n可用的订阅计划:")
    for plan in plans:
        print(f"{plan['id']}. {plan['name']} - {plan['duration_days']}天 - ¥{plan['price']}")
    
    # 选择订阅计划
    while True:
        try:
            plan_id = int(input("\n请选择订阅计划ID: "))
            if any(plan['id'] == plan_id for plan in plans):
                break
            print("无效的订阅计划ID，请重新选择")
        except ValueError:
            print("请输入有效的数字")
    
    # 输入用户ID列表
    while True:
        try:
            user_ids_input = input("\n请输入用户ID列表（支持范围格式，如：101-189，多个范围用逗号分隔）: ")
            user_ids = parse_user_ids(user_ids_input)
            if user_ids:
                break
            print("请输入有效的用户ID")
        except ValueError:
            print("请输入有效的用户ID")
    
    # 显示将要创建订阅的用户ID
    print(f"\n将要为以下用户创建订阅：")
    print(f"用户ID数量: {len(user_ids)}")
    if len(user_ids) <= 20:
        print(f"用户ID列表: {sorted(user_ids)}")
    else:
        print(f"用户ID范围: {min(user_ids)}-{max(user_ids)}")
    
    # 确认操作
    confirm = input(f"\n确认要为 {len(user_ids)} 个用户创建订阅吗？(y/n): ")
    if confirm.lower() != 'y':
        print("操作已取消")
        return
    
    # 创建订阅
    create_subscriptions(user_ids, plan_id)

if __name__ == "__main__":
    main() 