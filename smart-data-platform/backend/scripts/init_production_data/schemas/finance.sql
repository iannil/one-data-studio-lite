-- Finance System Schema (PostgreSQL)
-- Database: finance_db (public schema)
-- Data Volume: ~5M records total

-- Set search path to public
SET search_path TO public;

-- Drop existing tables (for re-creation)
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS risk_assessments CASCADE;
DROP TABLE IF EXISTS portfolio_holdings CASCADE;
DROP TABLE IF EXISTS portfolios CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ============================================
-- 1. Customers Table (100,000 records)
-- ============================================
CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
    customer_code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    id_card_encrypted VARCHAR(64) NOT NULL,  -- Masked ID card
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    address TEXT,
    city VARCHAR(50),
    province VARCHAR(50),
    postal_code VARCHAR(10),
    customer_type VARCHAR(20) NOT NULL DEFAULT 'individual',  -- individual, corporate
    risk_level INTEGER NOT NULL DEFAULT 3 CHECK (risk_level BETWEEN 1 AND 5),
    credit_score INTEGER CHECK (credit_score BETWEEN 300 AND 850),
    kyc_status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, verified, rejected
    kyc_verified_at TIMESTAMP WITH TIME ZONE,
    total_assets DECIMAL(18, 4) NOT NULL DEFAULT 0,
    total_liabilities DECIMAL(18, 4) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, inactive, frozen, closed
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_by VARCHAR(50),
    updated_by VARCHAR(50)
);

-- Indexes for customers
CREATE INDEX idx_customers_customer_code ON customers(customer_code);
CREATE INDEX idx_customers_phone ON customers(phone);
CREATE INDEX idx_customers_city ON customers(city);
CREATE INDEX idx_customers_status ON customers(status);
CREATE INDEX idx_customers_created_at ON customers(created_at);

-- ============================================
-- 2. Accounts Table (200,000 records)
-- ============================================
CREATE TABLE accounts (
    id BIGSERIAL PRIMARY KEY,
    account_number VARCHAR(32) NOT NULL UNIQUE,
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    account_type VARCHAR(30) NOT NULL,  -- checking, savings, investment, credit
    currency VARCHAR(3) NOT NULL DEFAULT 'CNY',
    balance DECIMAL(18, 4) NOT NULL DEFAULT 0,
    available_balance DECIMAL(18, 4) NOT NULL DEFAULT 0,
    frozen_amount DECIMAL(18, 4) NOT NULL DEFAULT 0,
    credit_limit DECIMAL(18, 4),  -- For credit accounts
    interest_rate DECIMAL(8, 6),
    last_transaction_at TIMESTAMP WITH TIME ZONE,
    overdraft_protection BOOLEAN NOT NULL DEFAULT FALSE,
    daily_limit DECIMAL(18, 4) DEFAULT 50000,
    monthly_limit DECIMAL(18, 4) DEFAULT 500000,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for accounts
CREATE INDEX idx_accounts_customer_id ON accounts(customer_id);
CREATE INDEX idx_accounts_account_type ON accounts(account_type);
CREATE INDEX idx_accounts_status ON accounts(status);
CREATE INDEX idx_accounts_balance ON accounts(balance);

-- ============================================
-- 3. Transactions Table (3,000,000 records)
-- Partitioned by month for better performance
-- ============================================
CREATE TABLE transactions (
    id BIGSERIAL,
    transaction_id VARCHAR(64) NOT NULL,
    account_id BIGINT NOT NULL,
    transaction_type VARCHAR(30) NOT NULL,  -- deposit, withdrawal, transfer, payment, fee, interest
    direction VARCHAR(10) NOT NULL,  -- in, out
    amount DECIMAL(18, 4) NOT NULL,
    balance_before DECIMAL(18, 4) NOT NULL,
    balance_after DECIMAL(18, 4) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'CNY',
    counterparty_account VARCHAR(32),
    counterparty_name VARCHAR(100),
    counterparty_bank VARCHAR(100),
    channel VARCHAR(30) NOT NULL,  -- mobile, web, atm, branch, api
    device_id VARCHAR(64),
    ip_address VARCHAR(45),
    location VARCHAR(100),
    description TEXT,
    reference_number VARCHAR(64),
    fee_amount DECIMAL(18, 4) DEFAULT 0,
    exchange_rate DECIMAL(12, 6),
    status VARCHAR(20) NOT NULL DEFAULT 'completed',  -- pending, processing, completed, failed, reversed
    risk_score INTEGER CHECK (risk_score BETWEEN 0 AND 100),
    is_suspicious BOOLEAN NOT NULL DEFAULT FALSE,
    transaction_at TIMESTAMP WITH TIME ZONE NOT NULL,
    settled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, transaction_at)
) PARTITION BY RANGE (transaction_at);

-- Create monthly partitions for 2024-2026
CREATE TABLE transactions_2024_01 PARTITION OF transactions
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE transactions_2024_02 PARTITION OF transactions
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE transactions_2024_03 PARTITION OF transactions
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE transactions_2024_04 PARTITION OF transactions
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE transactions_2024_05 PARTITION OF transactions
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE transactions_2024_06 PARTITION OF transactions
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE transactions_2024_07 PARTITION OF transactions
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE transactions_2024_08 PARTITION OF transactions
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE transactions_2024_09 PARTITION OF transactions
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE transactions_2024_10 PARTITION OF transactions
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE transactions_2024_11 PARTITION OF transactions
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE transactions_2024_12 PARTITION OF transactions
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

CREATE TABLE transactions_2025_01 PARTITION OF transactions
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE transactions_2025_02 PARTITION OF transactions
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE transactions_2025_03 PARTITION OF transactions
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE transactions_2025_04 PARTITION OF transactions
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE transactions_2025_05 PARTITION OF transactions
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE transactions_2025_06 PARTITION OF transactions
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE transactions_2025_07 PARTITION OF transactions
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE transactions_2025_08 PARTITION OF transactions
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE transactions_2025_09 PARTITION OF transactions
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE transactions_2025_10 PARTITION OF transactions
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE transactions_2025_11 PARTITION OF transactions
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE transactions_2025_12 PARTITION OF transactions
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

CREATE TABLE transactions_2026_01 PARTITION OF transactions
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE transactions_2026_02 PARTITION OF transactions
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE transactions_2026_03 PARTITION OF transactions
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Indexes for transactions
CREATE INDEX idx_transactions_account_id ON transactions(account_id);
CREATE INDEX idx_transactions_transaction_type ON transactions(transaction_type);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_transaction_at ON transactions(transaction_at);
CREATE INDEX idx_transactions_amount ON transactions(amount);
CREATE INDEX idx_transactions_is_suspicious ON transactions(is_suspicious) WHERE is_suspicious = TRUE;

-- ============================================
-- 4. Portfolios Table (50,000 records)
-- ============================================
CREATE TABLE portfolios (
    id BIGSERIAL PRIMARY KEY,
    portfolio_code VARCHAR(32) NOT NULL UNIQUE,
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    name VARCHAR(100) NOT NULL,
    portfolio_type VARCHAR(30) NOT NULL,  -- conservative, balanced, growth, aggressive
    risk_tolerance INTEGER NOT NULL CHECK (risk_tolerance BETWEEN 1 AND 5),
    target_return DECIMAL(8, 4),
    investment_horizon INTEGER,  -- months
    total_value DECIMAL(18, 4) NOT NULL DEFAULT 0,
    total_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
    unrealized_pnl DECIMAL(18, 4) NOT NULL DEFAULT 0,
    realized_pnl DECIMAL(18, 4) NOT NULL DEFAULT 0,
    annual_return DECIMAL(8, 4),
    benchmark VARCHAR(50),
    rebalance_frequency VARCHAR(20),  -- daily, weekly, monthly, quarterly
    last_rebalanced_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for portfolios
CREATE INDEX idx_portfolios_customer_id ON portfolios(customer_id);
CREATE INDEX idx_portfolios_portfolio_type ON portfolios(portfolio_type);
CREATE INDEX idx_portfolios_status ON portfolios(status);

-- ============================================
-- 5. Portfolio Holdings Table (300,000 records)
-- ============================================
CREATE TABLE portfolio_holdings (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id BIGINT NOT NULL REFERENCES portfolios(id),
    asset_code VARCHAR(20) NOT NULL,
    asset_name VARCHAR(100) NOT NULL,
    asset_type VARCHAR(30) NOT NULL,  -- stock, bond, fund, etf, cash, other
    quantity DECIMAL(18, 6) NOT NULL,
    average_cost DECIMAL(18, 6) NOT NULL,
    current_price DECIMAL(18, 6) NOT NULL,
    market_value DECIMAL(18, 4) NOT NULL,
    unrealized_pnl DECIMAL(18, 4) NOT NULL,
    weight_percent DECIMAL(8, 4) NOT NULL,
    target_weight DECIMAL(8, 4),
    currency VARCHAR(3) NOT NULL DEFAULT 'CNY',
    exchange VARCHAR(20),
    sector VARCHAR(50),
    last_price_update TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for portfolio_holdings
CREATE INDEX idx_portfolio_holdings_portfolio_id ON portfolio_holdings(portfolio_id);
CREATE INDEX idx_portfolio_holdings_asset_type ON portfolio_holdings(asset_type);
CREATE INDEX idx_portfolio_holdings_asset_code ON portfolio_holdings(asset_code);

-- ============================================
-- 6. Risk Assessments Table (100,000 records)
-- ============================================
CREATE TABLE risk_assessments (
    id BIGSERIAL PRIMARY KEY,
    assessment_code VARCHAR(32) NOT NULL UNIQUE,
    account_id BIGINT NOT NULL REFERENCES accounts(id),
    assessment_type VARCHAR(30) NOT NULL,  -- credit, market, liquidity, operational
    risk_score INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    risk_level VARCHAR(20) NOT NULL,  -- low, medium, high, critical
    var_1d DECIMAL(18, 4),  -- Value at Risk (1 day)
    var_10d DECIMAL(18, 4),  -- Value at Risk (10 days)
    expected_shortfall DECIMAL(18, 4),
    stress_test_result DECIMAL(18, 4),
    probability_of_default DECIMAL(8, 6),
    loss_given_default DECIMAL(8, 4),
    exposure_at_default DECIMAL(18, 4),
    factors JSONB,  -- Risk factors
    recommendations TEXT[],
    assessed_by VARCHAR(50),
    reviewed_by VARCHAR(50),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    valid_until TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for risk_assessments
CREATE INDEX idx_risk_assessments_account_id ON risk_assessments(account_id);
CREATE INDEX idx_risk_assessments_risk_level ON risk_assessments(risk_level);
CREATE INDEX idx_risk_assessments_assessment_type ON risk_assessments(assessment_type);
CREATE INDEX idx_risk_assessments_created_at ON risk_assessments(created_at);

-- ============================================
-- 7. Audit Logs Table (1,000,000 records)
-- ============================================
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    trace_id VARCHAR(64) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,  -- customer, account, transaction, portfolio
    entity_id BIGINT NOT NULL,
    action VARCHAR(30) NOT NULL,  -- create, update, delete, view, export
    actor_id VARCHAR(50),
    actor_type VARCHAR(20) NOT NULL,  -- user, system, api
    actor_ip VARCHAR(45),
    actor_user_agent TEXT,
    old_values JSONB,
    new_values JSONB,
    changes JSONB,
    metadata JSONB,
    result VARCHAR(20) NOT NULL DEFAULT 'success',  -- success, failure, partial
    error_message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for audit_logs
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_actor_id ON audit_logs(actor_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_trace_id ON audit_logs(trace_id);

-- ============================================
-- Comments for documentation
-- ============================================
COMMENT ON DATABASE finance_db IS 'Financial trading system database with customer accounts, transactions, portfolios, and risk assessments';
COMMENT ON TABLE customers IS 'Customer master data with KYC information';
COMMENT ON TABLE accounts IS 'Customer bank accounts (checking, savings, investment, credit)';
COMMENT ON TABLE transactions IS 'Transaction ledger with monthly partitions';
COMMENT ON TABLE portfolios IS 'Investment portfolio metadata';
COMMENT ON TABLE portfolio_holdings IS 'Individual asset holdings in portfolios';
COMMENT ON TABLE risk_assessments IS 'Risk evaluation records for accounts';
COMMENT ON TABLE audit_logs IS 'System audit trail for compliance';
