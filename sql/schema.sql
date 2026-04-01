CREATE DATABASE IF NOT EXISTS groupchat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'chatuser'@'localhost' IDENTIFIED BY 'chatpass';
GRANT ALL PRIVILEGES ON groupchat.* TO 'chatuser'@'localhost';
FLUSH PRIVILEGES;

USE groupchat;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'homeowner',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS service_bundles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(120) NOT NULL,
  service_type VARCHAR(80) NOT NULL,
  neighborhood VARCHAR(120) NOT NULL,
  homes_count INT NOT NULL,
  target_date VARCHAR(40) NOT NULL,
  description TEXT NOT NULL,
  budget_notes TEXT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'open',
  created_by INT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_bundle_user FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bids (
  id INT AUTO_INCREMENT PRIMARY KEY,
  bundle_id INT NOT NULL,
  vendor_id INT NOT NULL,
  amount FLOAT NOT NULL,
  timeline_days INT NOT NULL,
  proposal TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_bid_bundle FOREIGN KEY (bundle_id) REFERENCES service_bundles(id) ON DELETE CASCADE,
  CONSTRAINT fk_bid_vendor FOREIGN KEY (vendor_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY uq_bundle_vendor (bundle_id, vendor_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
