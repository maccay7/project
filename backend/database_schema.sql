CREATE TABLE IF NOT EXISTS ui_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id INT DEFAULT 0,
    name VARCHAR(255),
    status VARCHAR(64) DEFAULT 'in-progress',
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    versions JSON,
    instrument_workflows JSON,
    payload JSON,
    instrument_data JSON,
    instrument_count INT DEFAULT 0,
    total_value DECIMAL(20,2) DEFAULT 0,
    version_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX (created_at),
    INDEX (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS version_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version_id VARCHAR(64),
    version_number INT DEFAULT 1,
    session_id VARCHAR(255),
    instrument_type VARCHAR(64),
    change_summary TEXT,
    dataset_snapshot JSON,
    mapping_snapshot JSON,
    calculation_snapshot JSON,
    portfolio_snapshot JSON,
    report_snapshot JSON,
    user_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX (session_id),
    INDEX (version_id),
    INDEX (version_number),
    INDEX (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Persist visualization selections.
CREATE TABLE IF NOT EXISTS report_configurations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    selected_instruments JSON,
    report_type VARCHAR(64) DEFAULT 'session',
    visualisation_config JSON,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_session_report (session_id),
    INDEX (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;