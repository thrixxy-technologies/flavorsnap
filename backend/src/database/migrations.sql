-- FlavorSnap Database Schema
-- MySQL Migration Script

-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS flavorsnap CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE flavorsnap;

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  uuid VARCHAR(36) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  username VARCHAR(50) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  avatar_url VARCHAR(500),
  email_verified BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  role ENUM('user', 'admin') DEFAULT 'user',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  last_login TIMESTAMP NULL,
  INDEX idx_email (email),
  INDEX idx_username (username),
  INDEX idx_uuid (uuid)
);

-- Food categories table
CREATE TABLE IF NOT EXISTS food_categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  description TEXT,
  image_url VARCHAR(500),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_name (name)
);

-- Food classifications table
CREATE TABLE IF NOT EXISTS classifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  uuid VARCHAR(36) UNIQUE NOT NULL,
  user_id INT NOT NULL,
  food_category_id INT NOT NULL,
  image_url VARCHAR(500) NOT NULL,
  original_filename VARCHAR(255) NOT NULL,
  file_size INT NOT NULL,
  mime_type VARCHAR(100) NOT NULL,
  confidence_score DECIMAL(5,2) NOT NULL,
  processing_time DECIMAL(8,3) NOT NULL,
  model_version VARCHAR(20) DEFAULT '1.0.0',
  ip_address VARCHAR(45),
  user_agent TEXT,
  is_correct BOOLEAN DEFAULT NULL, -- User feedback on classification
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (food_category_id) REFERENCES food_categories(id) ON DELETE RESTRICT,
  INDEX idx_user_id (user_id),
  INDEX idx_food_category_id (food_category_id),
  INDEX idx_created_at (created_at),
  INDEX idx_confidence_score (confidence_score)
);

-- Classification predictions table (stores all predictions for a classification)
CREATE TABLE IF NOT EXISTS classification_predictions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  classification_id INT NOT NULL,
  food_category_id INT NOT NULL,
  confidence_score DECIMAL(5,2) NOT NULL,
  rank_order INT NOT NULL,
  FOREIGN KEY (classification_id) REFERENCES classifications(id) ON DELETE CASCADE,
  FOREIGN KEY (food_category_id) REFERENCES food_categories(id) ON DELETE RESTRICT,
  INDEX idx_classification_id (classification_id),
  INDEX idx_confidence_score (confidence_score),
  UNIQUE KEY unique_classification_rank (classification_id, rank_order)
);

-- User sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  uuid VARCHAR(36) UNIQUE NOT NULL,
  user_id INT NOT NULL,
  token_hash VARCHAR(255) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  ip_address VARCHAR(45),
  user_agent TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user_id (user_id),
  INDEX idx_token_hash (token_hash),
  INDEX idx_expires_at (expires_at)
);

-- API usage statistics table
CREATE TABLE IF NOT EXISTS api_usage_stats (
  id INT AUTO_INCREMENT PRIMARY KEY,
  date DATE NOT NULL,
  total_classifications INT DEFAULT 0,
  unique_users INT DEFAULT 0,
  avg_confidence DECIMAL(5,2) DEFAULT 0,
  most_classified_food VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY unique_date (date),
  INDEX idx_date (date)
);

-- System settings table
CREATE TABLE IF NOT EXISTS system_settings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  setting_key VARCHAR(100) UNIQUE NOT NULL,
  setting_value TEXT,
  description TEXT,
  is_public BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_setting_key (setting_key)
);

-- Insert default food categories
INSERT IGNORE INTO food_categories (name, description) VALUES
('Akara', 'Nigerian bean cake made from black-eyed peas'),
('Bread', 'Various types of bread including sliced, loaf, and specialty breads'),
('Egusi', 'Nigerian soup made from melon seeds'),
('Moi Moi', 'Nigerian steamed bean pudding'),
('Rice and Stew', 'Rice served with tomato-based stew'),
('Yam', 'Yam dishes including boiled, fried, and porridge');

-- Insert default system settings
INSERT IGNORE INTO system_settings (setting_key, setting_value, description, is_public) VALUES
('max_file_size', '10485760', 'Maximum file size for uploads in bytes', TRUE),
('allowed_file_types', 'jpg,jpeg,png,webp', 'Allowed file types for uploads', TRUE),
('confidence_threshold', '0.6', 'Minimum confidence threshold for classifications', TRUE),
('model_version', '1.0.0', 'Current ML model version', TRUE),
('maintenance_mode', 'false', 'Whether the system is in maintenance mode', TRUE),
('registration_enabled', 'true', 'Whether user registration is enabled', TRUE),
('classification_history_enabled', 'true', 'Whether to save classification history', TRUE);

-- Create views for common queries

-- User statistics view
CREATE OR REPLACE VIEW user_stats AS
SELECT 
  u.id,
  u.uuid,
  u.email,
  u.username,
  COUNT(c.id) as total_classifications,
  AVG(c.confidence_score) as avg_confidence,
  MAX(c.created_at) as last_classification,
  u.created_at as user_created_at
FROM users u
LEFT JOIN classifications c ON u.id = c.user_id
GROUP BY u.id, u.uuid, u.email, u.username, u.created_at;

-- Food category statistics view
CREATE OR REPLACE VIEW food_category_stats AS
SELECT 
  fc.id,
  fc.name,
  fc.description,
  COUNT(c.id) as total_classifications,
  AVG(c.confidence_score) as avg_confidence,
  COUNT(DISTINCT c.user_id) as unique_users,
  MAX(c.created_at) as last_classification
FROM food_categories fc
LEFT JOIN classifications c ON fc.id = c.food_category_id
GROUP BY fc.id, fc.name, fc.description;

-- Daily statistics view
CREATE OR REPLACE VIEW daily_stats AS
SELECT 
  DATE(c.created_at) as date,
  COUNT(c.id) as total_classifications,
  COUNT(DISTINCT c.user_id) as unique_users,
  AVG(c.confidence_score) as avg_confidence,
  fc.name as most_classified_food
FROM classifications c
JOIN food_categories fc ON c.food_category_id = fc.id
GROUP BY DATE(c.created_at)
ORDER BY date DESC;
