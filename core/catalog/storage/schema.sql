-- Catalog SQLite schema (PR-7)
-- RU: Схема SQLite для каталога (read-only snapshots)
-- EN: SQLite schema for catalog (read-only snapshots)

PRAGMA foreign_keys = ON;

-- Regions table
CREATE TABLE IF NOT EXISTS regions (
    region_id TEXT PRIMARY KEY,
    country TEXT NOT NULL,
    currency TEXT NOT NULL,
    locale TEXT NOT NULL
);

-- Stores table
CREATE TABLE IF NOT EXISTS stores (
    store_id TEXT PRIMARY KEY,
    region_id TEXT NOT NULL,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    meta_json TEXT,  -- JSON metadata (flexible)
    FOREIGN KEY (region_id) REFERENCES regions(region_id) ON DELETE CASCADE
);

-- SKUs table
CREATE TABLE IF NOT EXISTS skus (
    sku_id TEXT PRIMARY KEY,
    store_id TEXT NOT NULL,
    ean TEXT,  -- Barcode (nullable)
    name TEXT NOT NULL,
    brand TEXT,
    aisle TEXT,
    package_size TEXT,  -- Decimal stored as TEXT
    unit TEXT,
    price TEXT,  -- Decimal stored as TEXT
    currency TEXT NOT NULL,
    updated_at TEXT,  -- ISO date string
    FOREIGN KEY (store_id) REFERENCES stores(store_id) ON DELETE CASCADE
);

-- SKU aliases table (for food_id -> sku_id mapping)
CREATE TABLE IF NOT EXISTS sku_aliases (
    region_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    PRIMARY KEY (region_id, alias),
    FOREIGN KEY (region_id) REFERENCES regions(region_id),
    FOREIGN KEY (sku_id) REFERENCES skus(sku_id) ON DELETE CASCADE
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_stores_region_id ON stores(region_id);
CREATE INDEX IF NOT EXISTS idx_skus_store_id ON skus(store_id);
CREATE INDEX IF NOT EXISTS idx_skus_ean ON skus(ean) WHERE ean IS NOT NULL;
-- Note: idx_alias_region is redundant - PRIMARY KEY (region_id, alias) already creates an index
