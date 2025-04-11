import mysql.connector
import bcrypt
import random
import string
import csv
import os
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

# 生成随机密码
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

# 获取密码哈希
def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_batch_users(start_num=1, count=100):
    """批量创建用户账号"""
    # 创建数据库连接
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        print(f"成功连接到数据库: {db_config['database']}")
    except mysql.connector.Error as err:
        print(f"数据库连接失败: {err}")
        return
    
    # 准备存储用户信息的列表
    user_data = []
    
    try:
        for i in range(count):
            user_num = start_num + i
            username = f"tianhuiai{user_num:05d}"  # 格式化为5位数字，例如: tianhuiai00001
            email = f"{username}@example.com"
            password = generate_random_password()
            hashed_password = get_password_hash(password)
            
            # 将用户信息保存到数据库
            try:
                cursor.execute(
                    "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                    (username, email, hashed_password)
                )
                # 将原始密码（未哈希）和用户名保存到列表中
                user_data.append({
                    "用户名": username,
                    "邮箱": email,
                    "密码": password
                })
                print(f"成功创建用户: {username}")
            except mysql.connector.Error as err:
                print(f"创建用户 {username} 失败: {err}")
        
        # 提交事务
        conn.commit()
        print(f"成功创建 {len(user_data)} 个用户")
        
        # 导出到CSV文件
        csv_file = "批量用户账号.csv"
        try:
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ["用户名", "邮箱", "密码"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(user_data)
            print(f"用户数据已导出到 {csv_file}")
        except Exception as e:
            print(f"导出CSV文件失败: {e}")
        
    except Exception as e:
        print(f"出现错误: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
        print("数据库连接已关闭")

if __name__ == "__main__":
    # 创建100个用户，账号从tianhuiai20001开始
    create_batch_users(start_num=20001, count=100) 