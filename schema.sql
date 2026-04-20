-- Dura Capital — run in MySQL Workbench on your local server.
-- After this, set backend/.env: MYSQL_*, FLASK_SECRET_KEY, ALLOWED_LOGIN_EMAIL

CREATE DATABASE IF NOT EXISTS dura_capital
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE dura_capital;

CREATE TABLE IF NOT EXISTS users (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(512) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS instruments (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  instrument_type VARCHAR(64) NOT NULL COMMENT 'Bonds | T-Bills | Money Market',
  issuer VARCHAR(255) NOT NULL DEFAULT '',
  face_value DECIMAL(18, 2) NOT NULL DEFAULT 0,
  current_value DECIMAL(18, 2) NOT NULL DEFAULT 0,
  yield_pct DECIMAL(12, 6) NOT NULL DEFAULT 0 COMMENT 'e.g. 4.5 for 4.5%',
  maturity_label VARCHAR(64) NOT NULL DEFAULT '' COMMENT 'YYYY-MM-DD or Rolling',
  days_left INT NULL,
  rating VARCHAR(32) DEFAULT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'Active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_type (instrument_type)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS file_uploads (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  original_name VARCHAR(512) NOT NULL,
  stored_path VARCHAR(1024) NOT NULL,
  instrument_type VARCHAR(64) DEFAULT NULL,
  counter_party VARCHAR(255) DEFAULT NULL,
  eval_date DATE NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  action VARCHAR(64) NOT NULL,
  detail JSON NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Single owner account (password is NOT stored here — only a Werkzeug scrypt hash).
-- Plain password was chosen by you; change it in MySQL only by generating a new hash in Python.
DELETE FROM users;

INSERT INTO users (email, password_hash) VALUES (
  'makanakakanyai@gmail.com',
  'scrypt:32768:8:1$hbkr0iW6TKT5cDac$d78aa0e5dcf3c10bf2dbcde4b8825af5b9c8cc1c865cc4dd80b127514c5d3ea8911d98086e6029f9b94178921e8787e8dc0f7c3185f2d5b3221c4e78c55992b4'
);

-- No seed instruments: add rows via your import pipeline or manual INSERT so all UI values come from the DB.
