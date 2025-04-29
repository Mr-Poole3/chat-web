import mysql.connector
import bcrypt
import random
import string
import csv
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取数据库配置
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "610428"),
    "database": os.getenv("DB_NAME", "ai"),
    "port": int(os.getenv("DB_PORT", "100"))
}

def generate_random_password(length=10):
    """生成一个包含大小写字母和数字的随机密码"""
    characters = string.ascii_uppercase + string.ascii_lowercase + string.digits
    # 确保密码至少包含一个大写字母、一个小写字母和一个数字
    password = random.choice(string.ascii_uppercase) + random.choice(string.ascii_lowercase) + random.choice(string.digits)
    # 添加剩余的随机字符
    password += ''.join(random.choice(characters) for _ in range(length - 3))
    # 打乱密码字符顺序
    password_list = list(password)
    random.shuffle(password_list)
    return ''.join(password_list)

def get_password_hash(password):
    """获取密码哈希值"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_vip_users(start_num=1, count=10):
    """批量创建年卡VIP用户账号"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        print(f"成功连接到数据库: {db_config['database']}")
        
        # 获取年卡订阅计划ID
        cursor.execute("SELECT id FROM subscription_plans WHERE name = '年卡VIP'")
        plan = cursor.fetchone()
        if not plan:
            print("未找到年卡VIP订阅计划")
            return
        
        plan_id = plan['id']
        user_data = []
        
        # 设置订阅时间
        start_date = datetime.now()
        end_date = start_date + timedelta(days=365)
        
        for i in range(count):
            user_num = start_num + i
            username = f"天汇A{user_num:02d}"  # 格式化为2位数字，例如: 天汇A01
            email = f"tianhuiA{user_num:02d}@example.com"
            password = generate_random_password()
            hashed_password = get_password_hash(password)
            
            try:
                # 插入用户数据
                cursor.execute(
                    "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, hashed_password)
                )
                user_id = cursor.lastrowid
                
                # 插入订阅数据
                cursor.execute(
                    """INSERT INTO user_subscriptions 
                       (user_id, plan_id, start_date, end_date, status) 
                       VALUES (%s, %s, %s, %s, 'active')""",
                    (user_id, plan_id, start_date, end_date)
                )
                
                # 保存用户信息
                user_data.append({
                    "用户名": username,
                    "邮箱": email,
                    "密码": password,
                    "开通时间": start_date.strftime("%Y-%m-%d"),
                    "到期时间": end_date.strftime("%Y-%m-%d")
                })
                print(f"成功创建VIP用户: {username}")
                
            except mysql.connector.Error as err:
                print(f"创建用户 {username} 失败: {err}")
                conn.rollback()
                continue
        
        # 提交事务
        conn.commit()
        print(f"成功创建 {len(user_data)} 个VIP用户")
        
        # 导出到CSV文件
        csv_file = "VIP用户账号.csv"
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ["用户名", "邮箱", "密码", "开通时间", "到期时间"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(user_data)
            print(f"VIP用户数据已导出到 {csv_file}")
        except Exception as e:
            print(f"导出CSV文件失败: {e}")
            
    except Exception as e:
        print(f"出现错误: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        print("数据库连接已关闭")

if __name__ == "__main__":
    # 创建10个VIP用户，账号从天汇A01开始
    create_vip_users(start_num=1, count=10) 