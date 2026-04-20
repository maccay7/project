-- Database schema for storing yield curve data from St. Louis Fed

-- Table for storing Treasury yield curve observations
CREATE TABLE IF NOT EXISTS yield_curve_observations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    series_id VARCHAR(20) NOT NULL,
    observation_date DATE NOT NULL,
    rate DECIMAL(10, 4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_series_date (series_id, observation_date),
    INDEX idx_series_date (series_id, observation_date),
    INDEX idx_observation_date (observation_date)
);

-- Table for storing calculated yield curve metrics
CREATE TABLE IF NOT EXISTS yield_curve_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    calculation_date DATE NOT NULL,
    two_year_ten_year_spread DECIMAL(10, 4),
    five_year_thirty_year_spread DECIMAL(10, 4),
    three_month_ten_year_spread DECIMAL(10, 4),
    curve_shape ENUM('normal', 'inverted', 'flat') NOT NULL,
    latest_rates JSON, -- Store latest rates for all maturities
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY unique_calc_date (calculation_date),
    INDEX idx_calculation_date (calculation_date)
);

-- Table for series metadata
CREATE TABLE IF NOT EXISTS treasury_series (
    id INT AUTO_INCREMENT PRIMARY KEY,
    series_id VARCHAR(20) NOT NULL UNIQUE,
    series_name VARCHAR(255) NOT NULL,
    description TEXT,
    units VARCHAR(100),
    frequency VARCHAR(50),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_series_id (series_id)
);

-- Insert common Treasury series metadata
INSERT IGNORE INTO treasury_series (series_id, series_name, description, units, frequency) VALUES
('DGS10', '10-Year Treasury Constant Maturity Rate', 'Market yield on U.S. Treasury securities adjusted to a constant maturity of 10 years', 'Percent', 'Daily, Close'),
('DGS2', '2-Year Treasury Constant Maturity Rate', 'Market yield on U.S. Treasury securities adjusted to a constant maturity of 2 years', 'Percent', 'Daily, Close'),
('DGS5', '5-Year Treasury Constant Maturity Rate', 'Market yield on U.S. Treasury securities adjusted to a constant maturity of 5 years', 'Percent', 'Daily, Close'),
('DGS30', '30-Year Treasury Constant Maturity Rate', 'Market yield on U.S. Treasury securities adjusted to a constant maturity of 30 years', 'Percent', 'Daily, Close'),
('DGS3MO', '3-Month Treasury Constant Maturity Rate', 'Market yield on U.S. Treasury securities adjusted to a constant maturity of 3 months', 'Percent', 'Daily, Close'),
('DGS1', '1-Year Treasury Constant Maturity Rate', 'Market yield on U.S. Treasury securities adjusted to a constant maturity of 1 year', 'Percent', 'Daily, Close');
