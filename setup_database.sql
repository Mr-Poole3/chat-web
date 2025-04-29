-- 创建数据库
CREATE DATABASE IF NOT EXISTS ai;
USE ai;

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_username ON users(username);
CREATE INDEX idx_email ON users(email);

-- 聊天会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id VARCHAR(36) PRIMARY KEY,  -- 使用UUID格式
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    model VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 聊天消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    role ENUM('user', 'assistant') NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    sequence INT NOT NULL,  -- 消息在会话中的顺序
    is_terminated BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);

-- 订阅计划表
CREATE TABLE IF NOT EXISTS subscription_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    duration_days INT NOT NULL,  -- 订阅持续天数
    price DECIMAL(10, 2) NOT NULL,
    description TEXT,
    features TEXT,  -- 可用功能列表JSON格式存储
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 用户订阅表
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    plan_id INT NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    status ENUM('active', 'expired', 'cancelled', 'frozen') DEFAULT 'frozen',
    payment_id VARCHAR(100),  -- 支付相关ID，如有需要
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id) ON DELETE RESTRICT
);

-- 创建订阅相关索引
CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_end_date ON user_subscriptions(end_date);

-- 插入基础订阅计划数据
INSERT INTO subscription_plans (name, duration_days, price, description, features) VALUES
('周卡VIP', 7, 19.99, '7天高级会员，畅享所有AI模型', '{"all_models": true, "all_tools": true, "all_pages": true}'),
('月卡VIP', 30, 59.99, '30天高级会员，畅享所有AI模型，优惠更多', '{"all_models": true, "all_tools": true, "all_pages": true}'),
('年卡VIP', 365, 499.99, '365天高级会员，超值体验，享受所有功能', '{"all_models": true, "all_tools": true, "all_pages": true}');

-- 修改 user_subscriptions 表，添加新的状态和首次激活相关字段
ALTER TABLE user_subscriptions 
    -- 修改状态枚举，添加 frozen 状态
    MODIFY COLUMN status ENUM('active', 'expired', 'cancelled', 'frozen') DEFAULT 'frozen',
    -- 添加首次激活时间字段
    ADD COLUMN first_activated_at TIMESTAMP NULL,
    -- 添加实际结束时间字段（考虑冻结时间后的真实结束时间）
    ADD COLUMN actual_end_date TIMESTAMP NULL;

-- 创建首次激活时间的索引
CREATE INDEX idx_user_subscriptions_first_activated ON user_subscriptions(first_activated_at);