-- ============================================================================
-- UzTrack (UZ-LTS) - PostgreSQL 16 + PostGIS Database Initialization Schema
-- Tailored for High-Performance Logistics Routing & Tracking in Uzbekistan
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- 1. Integrated Logistics Carriers
CREATE TABLE IF NOT EXISTS carriers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,           -- 'fargo', 'bts', 'emu', 'yandex'
    name VARCHAR(150) NOT NULL,
    support_phone VARCHAR(50),
    webhook_url VARCHAR(255),
    api_key_hash VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Registered Marketplaces & Classifieds Clients
CREATE TABLE IF NOT EXISTS marketplaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_code VARCHAR(50) UNIQUE NOT NULL,     -- 'uzum', 'olx', 'asaxiy', 'zoodmall'
    name VARCHAR(150) NOT NULL,
    webhook_url VARCHAR(255),
    api_secret_hash VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Regional Sorting Hubs & Waypoint Checkpoints across Uzbekistan
CREATE TABLE IF NOT EXISTS hubs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    city VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    geom GEOMETRY(Point, 4326),
    is_central_hub BOOLEAN DEFAULT FALSE
);

-- 4. Core Shipments Aggregate
CREATE TABLE IF NOT EXISTS shipments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tracking_code VARCHAR(30) UNIQUE NOT NULL,   -- e.g. 'UZ77019283401'
    external_order_no VARCHAR(100) NOT NULL,
    marketplace_id VARCHAR(50) NOT NULL,
    carrier_code VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ORDER_CREATED',
    recipient_name VARCHAR(150),
    recipient_phone VARCHAR(50),
    
    origin_city VARCHAR(100) NOT NULL,
    origin_hub VARCHAR(150),
    origin_lat DOUBLE PRECISION,
    origin_lng DOUBLE PRECISION,
    
    dest_city VARCHAR(100) NOT NULL,
    dest_hub VARCHAR(150),
    dest_lat DOUBLE PRECISION,
    dest_lng DOUBLE PRECISION,
    
    current_lat DOUBLE PRECISION,
    current_lng DOUBLE PRECISION,
    current_city VARCHAR(100),
    current_hub VARCHAR(150),
    
    eta TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_shipments_tracking_code ON shipments(tracking_code);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_carrier ON shipments(carrier_code);
CREATE INDEX IF NOT EXISTS idx_shipments_marketplace ON shipments(marketplace_id);

-- 5. Checkpoints / Timeline Milestones (Immutable Event Log)
CREATE TABLE IF NOT EXISTS checkpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_id UUID REFERENCES shipments(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    title_uz VARCHAR(200) NOT NULL,
    title_ru VARCHAR(200) NOT NULL,
    title_en VARCHAR(200) NOT NULL,
    description_uz TEXT,
    description_ru TEXT,
    description_en TEXT,
    location_name VARCHAR(150),
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_shipment ON checkpoints(shipment_id);

-- ============================================================================
-- Seed Data: Regional Hubs in Uzbekistan with GPS Coordinates
-- ============================================================================
INSERT INTO hubs (code, name, city, region, lat, lng, geom, is_central_hub) VALUES
('HUB_TAS_SERGELI', 'Toshkent Sergeli Markaziy Saralash Markazi', 'Toshkent', 'Toshkent shahri', 41.2268, 69.2198, ST_SetSRID(ST_MakePoint(69.2198, 41.2268), 4326), TRUE),
('HUB_SAM_CENTRAL', 'Samarqand Viloyat Saralash Markazi', 'Samarqand', 'Samarqand viloyati', 39.6542, 66.9597, ST_SetSRID(ST_MakePoint(66.9597, 39.6542), 4326), TRUE),
('HUB_BUK_CENTRAL', 'Buxoro Logistika Markazi', 'Buxoro', 'Buxoro viloyati', 39.7747, 64.4286, ST_SetSRID(ST_MakePoint(64.4286, 39.7747), 4326), TRUE),
('HUB_FER_CENTRAL', 'Farg''ona Vodiy Birlashgan Hubi', 'Farg''ona', 'Farg''ona viloyati', 40.3842, 71.7843, ST_SetSRID(ST_MakePoint(71.7843, 40.3842), 4326), TRUE),
('HUB_AND_CENTRAL', 'Andijon Saralash Markazi', 'Andijon', 'Andijon viloyati', 40.7821, 72.3442, ST_SetSRID(ST_MakePoint(72.3442, 40.7821), 4326), FALSE),
('HUB_NAM_CENTRAL', 'Namangan Saralash Markazi', 'Namangan', 'Namangan viloyati', 40.9983, 71.6726, ST_SetSRID(ST_MakePoint(71.6726, 40.9983), 4326), FALSE),
('HUB_NUK_CENTRAL', 'Nukus Qoraqalpog''iston Markazi', 'Nukus', 'Qoraqalpog''iston', 42.4619, 59.6166, ST_SetSRID(ST_MakePoint(59.6166, 42.4619), 4326), TRUE),
('HUB_URG_CENTRAL', 'Urganch Xorazm Saralash Markazi', 'Urganch', 'Xorazm viloyati', 41.5562, 60.6317, ST_SetSRID(ST_MakePoint(60.6317, 41.5562), 4326), FALSE),
('HUB_QAR_CENTRAL', 'Qarshi Qashqadaryo Hubi', 'Qarshi', 'Qashqadaryo viloyati', 38.8606, 65.7891, ST_SetSRID(ST_MakePoint(65.7891, 38.8606), 4326), FALSE),
('HUB_TER_CENTRAL', 'Termiz Surxondaryo Hubi', 'Termiz', 'Surxondaryo viloyati', 37.2242, 67.2783, ST_SetSRID(ST_MakePoint(67.2783, 37.2242), 4326), FALSE),
('HUB_NAV_CENTRAL', 'Navoiy Erkin Iqtisodiy Hubi', 'Navoiy', 'Navoiy viloyati', 40.0844, 65.3792, ST_SetSRID(ST_MakePoint(65.3792, 40.0844), 4326), FALSE),
('HUB_JIZ_TRANSIT', 'Jizzax M39 Tranzit Nazorati', 'Jizzax', 'Jizzax viloyati', 40.1158, 67.8422, ST_SetSRID(ST_MakePoint(67.8422, 40.1158), 4326), FALSE),
('HUB_GUL_TRANSIT', 'Guliston Sirdaryo Tranzit Punkti', 'Guliston', 'Sirdaryo viloyati', 40.4912, 68.7842, ST_SetSRID(ST_MakePoint(68.7842, 40.4912), 4326), FALSE)
ON CONFLICT (code) DO NOTHING;

-- Seed default carriers
INSERT INTO carriers (code, name, support_phone) VALUES
('fargo', 'Fargo Express', '+998712000000'),
('bts', 'BTS Express Cargo', '+998712072020'),
('emu', 'EMU Express Mail Uzbekistan', '+998712009669'),
('yandex', 'Yandex Delivery Uzbekistan', '+998712003344'),
('uzpost', 'O''zbekiston Pochtasi (UzPost)', '+998712335747')
ON CONFLICT (code) DO NOTHING;
