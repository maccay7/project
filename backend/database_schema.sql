-- DuraCapital Financial Instrument Automation System
-- MySQL Database Schema

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role ENUM('Administrator', 'User', 'Viewer') DEFAULT 'User',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX (email)
);

-- User Preferences Table
CREATE TABLE IF NOT EXISTS user_preferences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    language VARCHAR(50) DEFAULT 'English',
    timezone VARCHAR(50) DEFAULT 'GMT+2',
    date_format VARCHAR(20) DEFAULT 'DD/MM/YYYY',
    currency VARCHAR(10) DEFAULT 'USD',
    email_notifications BOOLEAN DEFAULT TRUE,
    push_notifications BOOLEAN DEFAULT FALSE,
    weekly_reports BOOLEAN DEFAULT TRUE,
    system_alerts BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX (user_id)
);

-- Calculations Table
CREATE TABLE IF NOT EXISTS calculations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instrument_type ENUM('yield_curve', 'bond_pricing', 'money_market', 'treasury_analysis') NOT NULL,
    input_data JSON,
    result_data JSON,
    calculation_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX (instrument_type),
    INDEX (calculation_status),
    INDEX (created_at)
);

-- Financial Instruments Table
CREATE TABLE IF NOT EXISTS financial_instruments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instrument_type ENUM('treasury_bills', 'bonds', 'money_market', 'corporate_bonds', 'municipal_bonds') NOT NULL,
    fred_series_id VARCHAR(20) NOT NULL,
    instrument_name VARCHAR(100) NOT NULL,
    description TEXT,
    calculation_method ENUM('yield_to_maturity', 'discount_rate', 'spot_rate', 'forward_rate') NOT NULL,
    current_rate DECIMAL(10, 6),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX (instrument_type),
    UNIQUE KEY (fred_series_id)
);

-- Yield Curve Data Table
CREATE TABLE IF NOT EXISTS yield_curve_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    calculation_id INT,
    instrument_type VARCHAR(50) NOT NULL,
    maturity_period VARCHAR(20) NOT NULL,
    rate DECIMAL(10, 6) NOT NULL,
    data_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (calculation_id) REFERENCES calculations(id) ON DELETE CASCADE,
    INDEX (calculation_id),
    INDEX (instrument_type),
    INDEX (data_date)
);

-- Audit Log Table
CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX (user_id),
    INDEX (action),
    INDEX (created_at)
);

-- Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX (user_id),
    INDEX (token),
    INDEX (expires_at)
);

-- Upload History Table
CREATE TABLE IF NOT EXISTS upload_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size INT NOT NULL,
    upload_status ENUM('uploading', 'processing', 'completed', 'failed') DEFAULT 'uploading',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX (user_id),
    INDEX (upload_status),
    INDEX (created_at)
);

-- Reports Table
CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    report_type VARCHAR(100) NOT NULL,
    report_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    generation_status ENUM('pending', 'generating', 'completed', 'failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX (user_id),
    INDEX (report_type),
    INDEX (generation_status),
    INDEX (created_at)
);

-- System Configuration Table
CREATE TABLE IF NOT EXISTS system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX (config_key)
);

-- Insert default system configuration
INSERT IGNORE INTO system_config (config_key, config_value, description) VALUES
('version', '1.0.0', 'Application version'),
('environment', 'Development', 'Current environment'),
('database_type', 'MySQL', 'Database system'),
('api_status', 'Online', 'API status'),
('storage_used', '2.3 GB / 10 GB', 'Storage usage information');

-- Insert default financial instruments
INSERT IGNORE INTO financial_instruments (instrument_type, fred_series_id, instrument_name, description, calculation_method) VALUES
('treasury_bills', 'TB3MS', '3-Month Treasury Bill Rate', 'yield_to_maturity'),
('bonds', 'DGS10', '10-Year Treasury Constant Maturity Rate', 'yield_to_maturity'),
('money_market', 'DFF', 'Federal Funds Effective Rate', 'discount_rate');

-- Insert default user (for development)
INSERT IGNORE INTO users (email, password_hash, first_name, last_name, role) VALUES
('makanakakanyai@gmail.com', 'hashed_password_here', 'Makanaka', 'Kanyai', 'Administrator');

-- Insert default user preferences
INSERT IGNORE INTO user_preferences (user_id, language, timezone, date_format, currency, email_notifications, push_notifications, weekly_reports, system_alerts) VALUES
(1, 'English', 'GMT+2', 'DD/MM/YYYY', 'USD', TRUE, FALSE, TRUE, TRUE);
