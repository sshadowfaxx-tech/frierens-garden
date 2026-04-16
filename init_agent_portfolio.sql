-- Initialize paper portfolio with 2 SOL
INSERT INTO paper_portfolio (id, data) VALUES (1, '{
    "sol_balance": 2.0,
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "total_fees_paid": 0,
    "realized_pnl": 0,
    "positions_count": 0,
    "mode": "learning",
    "learning_start": "2026-03-25T11:56:00",
    "trading_enabled_after": "2026-03-25T12:56:00",
    "timestamp": null
}') ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data;
