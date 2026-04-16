-- Create table for paper trading portfolio state
CREATE TABLE IF NOT EXISTS paper_portfolio (
    id INTEGER PRIMARY KEY DEFAULT 1,
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create table for paper trade history
CREATE TABLE IF NOT EXISTS paper_trades (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    action VARCHAR(10) NOT NULL, -- BUY or SELL
    token VARCHAR(44) NOT NULL,
    token_symbol VARCHAR(50),
    amount_sol NUMERIC(20, 9),
    tokens NUMERIC(36, 9),
    price_usd NUMERIC(36, 18),
    market_cap NUMERIC(36, 2),
    fee NUMERIC(10, 9) DEFAULT 0.01,
    realized_pnl NUMERIC(20, 9) DEFAULT 0,
    realized_roi NUMERIC(10, 2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_paper_trades_token ON paper_trades(token);
CREATE INDEX IF NOT EXISTS idx_paper_trades_timestamp ON paper_trades(timestamp);

-- Initialize portfolio
INSERT INTO paper_portfolio (id, data) VALUES (1, '{
    "sol_balance": 1.0,
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "total_fees_paid": 0,
    "realized_pnl": 0,
    "positions_count": 0,
    "timestamp": null
}') ON CONFLICT (id) DO NOTHING;
