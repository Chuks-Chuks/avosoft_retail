-- Create schema
CREATE SCHEMA IF NOT EXISTS avosoft_retail;
SET search_path TO avosoft_retail;

-- =========================
-- DISTRIBUTION CENTERS
-- =========================
CREATE TABLE IF NOT EXISTS distribution_centers (
    id          UUID PRIMARY KEY,
    name        TEXT NOT NULL,
    latitude    NUMERIC(9,6),
    longitude   NUMERIC(9,6)
);

-- =========================
-- USERS
-- =========================
CREATE TABLE IF NOT EXISTS users (
    id             UUID PRIMARY KEY,
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    email          TEXT UNIQUE NOT NULL,
    age            INT,
    gender         TEXT,
    state          TEXT,
    street_address TEXT,
    postal_code    TEXT,
    city           TEXT,
    country        TEXT,
    latitude       NUMERIC(9,6),
    longitude      NUMERIC(9,6),
    traffic_source TEXT,
    created_at     TIMESTAMP NOT NULL,
    dob            DATE
);

CREATE INDEX IF NOT EXISTS idx_users_country ON users(country);

-- =========================
-- PRODUCTS
-- =========================
CREATE TABLE IF NOT EXISTS products (
    product_id     UUID PRIMARY KEY,
    cost           NUMERIC(12,2) NOT NULL,
    category       TEXT,
    name           TEXT,
    brand          TEXT,
    retail_price   NUMERIC(12,2),
    department     TEXT,
    sku            TEXT UNIQUE,
    subcategory    TEXT
);

CREATE INDEX IF NOT EXISTS idx_products_dept ON products(department);

-- =========================
-- EVENTS
-- =========================
CREATE TABLE IF NOT EXISTS events (
    id             UUID PRIMARY KEY,
    user_id        UUID NOT NULL REFERENCES users(id),
    sequence_number INT,
    session_id     TEXT,
    created_at     TIMESTAMP NOT NULL,
    ip_address     TEXT,
    city           TEXT,
    state          TEXT,
    postal_code    TEXT,
    browser        TEXT,
    traffic_source TEXT,
    uri            TEXT,
    event_type     TEXT,
    device_type    TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id);

-- =========================
-- INVENTORY ITEMS
-- =========================
CREATE TABLE IF NOT EXISTS inventory_items (
    id                           UUID PRIMARY KEY,
    product_id                   UUID NOT NULL REFERENCES products(product_id),
    created_at                   TIMESTAMP NOT NULL,
    sold_at                      TIMESTAMP,
    cost                         NUMERIC(12,2),
    product_category             TEXT,
    product_name                 TEXT,
    product_brand                TEXT,
    product_retail_price         NUMERIC(12,2),
    product_department           TEXT,
    product_sku                  TEXT,
    product_distribution_center_id UUID REFERENCES distribution_centers(id)
);

CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory_items(product_id);

-- =========================
-- ORDERS
-- =========================
CREATE TABLE IF NOT EXISTS orders (
    order_id      UUID PRIMARY KEY,
    user_id       UUID NOT NULL REFERENCES users(id),
    status        TEXT NOT NULL,
    gender        TEXT,
    created_at    TIMESTAMP NOT NULL,
    returned_at   TIMESTAMP,
    shipped_at    TIMESTAMP,
    delivered_at  TIMESTAMP,
    num_of_items  INT
);

CREATE INDEX IF NOT EXISTS idx_orders_user     ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_created  ON orders(created_at);

-- =========================
-- ORDER ITEMS
-- =========================
CREATE TABLE IF NOT EXISTS order_items (
    id                UUID PRIMARY KEY,
    order_id          UUID NOT NULL REFERENCES orders(order_id),
    user_id           UUID NOT NULL REFERENCES users(id),
    product_id        UUID NOT NULL REFERENCES products(product_id),
    inventory_item_id UUID REFERENCES inventory_items(id),
    status            TEXT,
    created_at        TIMESTAMP NOT NULL,
    shipped_at        TIMESTAMP,
    delivered_at      TIMESTAMP,
    returned_at       TIMESTAMP,
    sale_price        NUMERIC(12,2)
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_user  ON order_items(user_id);

-- =========================
-- PAYMENTS
-- =========================
CREATE TABLE IF NOT EXISTS payments (
    payment_id     UUID PRIMARY KEY,
    order_id       UUID NOT NULL REFERENCES orders(order_id),
    payment_date   DATE NOT NULL,
    status         TEXT NOT NULL CHECK (status IN ('success','failed')),
    amount         NUMERIC(12,2) NOT NULL,
    refund_amount  NUMERIC(12,2) DEFAULT 0,
    provider       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_date  ON payments(payment_date);
