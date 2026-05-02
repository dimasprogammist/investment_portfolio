-- init_db.sql — схема базы данных Investment Portfolio

CREATE DATABASE IF NOT EXISTS investment_portfolio;
USE investment_portfolio;

-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Пополнения
CREATE TABLE IF NOT EXISTS deposits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    date DATE NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Сделки с акциями
CREATE TABLE IF NOT EXISTS stock_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    operation VARCHAR(4) NOT NULL,
    quantity DECIMAL(12,2) NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Сделки с облигациями
CREATE TABLE IF NOT EXISTS bond_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    operation VARCHAR(4) NOT NULL,
    quantity DECIMAL(12,2) NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Дивиденды
CREATE TABLE IF NOT EXISTS dividends (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    quantity DECIMAL(12,2) DEFAULT 0,
    amount DECIMAL(12,2) NOT NULL,
    avg_price DECIMAL(12,2) DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Купоны
CREATE TABLE IF NOT EXISTS coupons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    quantity DECIMAL(12,2) DEFAULT 0,
    amount DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Налоги
CREATE TABLE IF NOT EXISTS taxes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    date DATE NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Погашения облигаций
CREATE TABLE IF NOT EXISTS bond_redemptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    quantity DECIMAL(12,2) NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Возвраты налогов
CREATE TABLE IF NOT EXISTS tax_refunds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    date DATE NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Вклады
CREATE TABLE IF NOT EXISTS deposits_accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,
    current_amount DECIMAL(12,2) NOT NULL,
    interest_rate DECIMAL(5,2),
    maturity_date DATE,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Выплаты по вкладам
CREATE TABLE IF NOT EXISTS deposit_payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    account_id INT NOT NULL,
    user_id INT NOT NULL DEFAULT 1,
    date DATE NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (account_id) REFERENCES deposits_accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Налоговые вычеты
CREATE TABLE IF NOT EXISTS tax_deductions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    date DATE NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    type VARCHAR(50) NOT NULL,
    description TEXT,
    year INT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Активы пользователей
CREATE TABLE IF NOT EXISTS user_assets (
    user_id INT NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    security_type VARCHAR(10) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (user_id, ticker),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Финансовые цели
CREATE TABLE IF NOT EXISTS financial_goals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    target_amount DECIMAL(12,2) NOT NULL,
    created_at DATE NOT NULL,
    target_date DATE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Исторические цены
CREATE TABLE IF NOT EXISTS historical_prices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    security_type VARCHAR(10) NOT NULL,
    UNIQUE KEY unique_date_ticker (date, ticker)
);

-- Бенчмарк: цены на недвижимость (квартиры)
CREATE TABLE IF NOT EXISTS benchmark_real_estate (
    date DATE PRIMARY KEY,
    value DECIMAL(12,2) NOT NULL,  -- цена за кв.м
    source VARCHAR(100) DEFAULT 'Росстат/Дом.РФ'
);

-- Бенчмарк: инфляция (ИПЦ)
CREATE TABLE IF NOT EXISTS benchmark_inflation (
    date DATE PRIMARY KEY,
    value DECIMAL(12,4) NOT NULL,  -- ИПЦ (месяц к месяцу прошлого года)
    source VARCHAR(100) DEFAULT 'Росстат'
);




-- Данные по инфляции (ИПЦ, % год к году)
INSERT IGNORE INTO benchmark_inflation (date, value) VALUES
('2023-06-30', 2.5),
('2023-07-31', 4.3),
('2023-08-31', 5.2),
('2023-09-30', 6.0),
('2023-10-31', 6.7),
('2023-11-30', 7.5),
('2023-12-31', 7.4),
('2024-01-31', 7.4),
('2024-02-29', 7.7),
('2024-03-31', 7.7),
('2024-04-30', 7.8),
('2024-05-31', 8.3),
('2024-06-30', 8.6),
('2024-07-31', 9.1),
('2024-08-31', 9.0),
('2024-09-30', 8.6),
('2024-10-31', 8.5),
('2024-11-30', 8.9),
('2024-12-31', 9.5),
('2025-01-31', 9.9),
('2025-02-28', 10.1),
('2025-03-31', 10.3),
('2025-04-30', 10.2);

-- Данные по ценам на недвижимость (руб/кв.м, вторичка Москва)
INSERT IGNORE INTO benchmark_real_estate (date, value) VALUES
('2023-06-30', 250000),
('2023-12-31', 265000),
('2024-06-30', 285000),
('2024-12-31', 310000),
('2025-06-30', 340000),
('2025-12-31', 375000),
('2026-03-31', 395000);