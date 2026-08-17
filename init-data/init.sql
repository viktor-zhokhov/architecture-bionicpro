CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(200),
    phone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO customers (id, first_name, last_name, email, phone) VALUES
(1, 'Prothetic', 'One',   'prothetic1@example.com', '+79001234567'),
(2, 'Prothetic', 'Two',   'prothetic2@example.com', '+79001234568'),
(3, 'Prothetic', 'Three', 'prothetic3@example.com', '+79001234569');

CREATE TABLE IF NOT EXISTS telemetry (
    id SERIAL PRIMARY KEY,
    customer_id INT,
    device_id VARCHAR(50),
    signal_quality REAL,
    battery_level REAL,
    response_time_ms REAL,
    session_duration_sec INT,
    movements_count INT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO telemetry (customer_id, device_id, signal_quality, battery_level, response_time_ms, session_duration_sec, movements_count, recorded_at) VALUES
(1, 'BPC-001', 87.5, 92.3, 45.2, 3600, 1250, CURRENT_TIMESTAMP),
(1, 'BPC-001', 85.0, 88.1, 48.7, 2400,  980, CURRENT_TIMESTAMP - INTERVAL '1 hour'),
(1, 'BPC-002', 90.1, 94.5, 42.0, 3000, 1100, CURRENT_TIMESTAMP),
(2, 'BPC-003', 91.2, 95.0, 38.5, 4200, 1800, CURRENT_TIMESTAMP),
(2, 'BPC-003', 89.8, 90.2, 41.3, 3800, 1650, CURRENT_TIMESTAMP - INTERVAL '2 hours'),
(3, 'BPC-004', 78.3, 82.5, 55.1, 1800,  650, CURRENT_TIMESTAMP),
(3, 'BPC-004', 80.1, 85.0, 52.3, 2100,  750, CURRENT_TIMESTAMP - INTERVAL '30 minutes');
