# Stealth Pump Detection ML Pipeline

## Executive Summary

This document outlines the machine learning architecture for detecting stealth pump operations in cryptocurrency markets with **4-6 days advance warning** and a target **F1-score ≥ 87%**. The pipeline combines on-chain metrics, exchange data, social signals, and wallet clustering to identify coordinated accumulation patterns before price impact.

---

## 1. Feature Engineering

### 1.1 Core Feature Categories

| Category | Feature Name | Description | Lead Time | Importance |
|----------|-------------|-------------|-----------|------------|
| **On-Chain Velocity** | `velocity_24h_change` | 24h token velocity vs 30d baseline | 4-6d | 🔴 Critical |
| | `velocity_variance` | Rolling 7d variance in transaction frequency | 3-5d | 🔴 Critical |
| | `median_tx_size_trend` | Slope of median transaction size (7d) | 5-6d | 🟡 High |
| **Wallet Clustering** | `new_whale_ratio` | % of volume from wallets < 30 days old | 4-5d | 🔴 Critical |
| | `cluster_concentration` | Gini coefficient of top 50 holders | 4-6d | 🔴 Critical |
| | `stealth_wallet_count` | Wallets with exactly 2-5 transactions | 3-5d | 🟡 High |
| **Exchange Flows** | `cex_netflow_7d` | Cumulative CEX inflow - outflow | 4-5d | 🔴 Critical |
| | `withdrawal_to_deposit_ratio` | Ratio of exchange withdrawals vs deposits | 3-5d | 🟡 High |
| | `large_withdrawal_count` | >$100K withdrawals per day | 2-4d | 🟡 High |
| **Order Book Microstructure** | `bid_imbalance_slope` | Change in bid/ask depth ratio | 2-3d | 🟡 High |
| | `spread_compression` | Bid-ask spread vs volatility | 1-3d | 🟡 High |
| | `hidden_liquidity_score` | Detected iceberg orders / visible depth | 2-4d | 🟡 High |
| **Social/Sentiment** | `social_volume_acceleration` | d²/dt² of social media mentions | 3-5d | 🟢 Medium |
| | `influencer_mention_spike` | Sudden increase in high-follower accounts | 2-4d | 🟢 Medium |
| | `discord_telegram_growth` | New member velocity in token communities | 3-6d | 🟢 Medium |
| **Cross-Token Patterns** | `similar_token_pre_pump` | Pumps in tokens sharing holder overlap | 4-6d | 🔴 Critical |
| | `dex_pool_correlation` | Liquidity pool movements across DEXs | 3-5d | 🟡 High |

### 1.2 Derived Composite Features

```python
# Accumulation Pressure Index (API)
# Combines wallet clustering + exchange outflows
API = (cluster_concentration * 0.4) + 
      (normalized_cex_outflow * 0.3) + 
      (new_whale_ratio * 0.3)

# Stealth Score (SS)
# Identifies intentionally low-visibility accumulation
SS = (stealth_wallet_count / total_wallets) * 
     (1 - social_volume_normalized) * 
     velocity_variance

# Coordination Index (CI)
# Detects synchronized buying patterns
CI = temporal_correlation_matrix(top_100_wallets, window='7d')
```

### 1.3 Temporal Feature Windows

| Feature Type | Lookback Window | Aggregation | Rationale |
|-------------|-----------------|-------------|-----------|
| Velocity metrics | 7d, 14d, 30d | Mean, std, slope | Establish baseline behavior |
| Wallet metrics | 14d, 30d, 90d | Count, concentration | Identify accumulation phases |
| Exchange flows | 3d, 7d, 14d | Cumulative sum | Early institutional movement |
| Order book | 1h, 4h, 24h | Snapshot analysis | Microstructure signals |
| Social metrics | 7d, 14d | Velocity, acceleration | Pre-announcement chatter |

---

## 2. Model Selection

### 2.1 Candidate Model Comparison

| Criterion | Random Forest | XGBoost | Neural Network (TabNet) | Recommendation |
|-----------|---------------|---------|------------------------|----------------|
| **F1-Score Potential** | 82-85% | 87-91% | 84-88% | **XGBoost** |
| **Training Speed** | Fast | Fast | Slow | Tie (RF/XGB) |
| **Inference Latency** | <10ms | <5ms | 20-50ms | **XGBoost** |
| **Feature Importance** | Native | Native | Attention | Tie |
| **Handles Missing Data** | Yes | Yes | No (needs imputation) | Tie (RF/XGB) |
| **Interpretability** | High (SHAP) | High (SHAP) | Medium | Tie (RF/XGB) |
| **Non-linear Interactions** | Good | Excellent | Excellent | **XGBoost** |
| **Cold Start (new tokens)** | Good | Good | Poor | Tie (RF/XGB) |
| **Ensemble Potential** | Good | Excellent | Good | **XGBoost** |

### 2.2 Recommended Architecture: XGBoost Ensemble

```python
# Primary Model: XGBoost Classifier
primary_params = {
    'objective': 'binary:logistic',
    'eval_metric': ['auc', 'f1'],  # Optimizing for F1
    'max_depth': 6,                # Balance complexity/generalization
    'learning_rate': 0.05,
    'n_estimators': 1000,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'scale_pos_weight': 15,        # Handle class imbalance (pumps are rare)
    'min_child_weight': 3,
    'gamma': 0.1,
    'reg_alpha': 0.1,              # L1 regularization
    'reg_lambda': 1.0,             # L2 regularization
    'tree_method': 'hist',         # Fast histogram-based algorithm
    'random_state': 42
}

# Secondary Model: Random Forest (for diversity)
rf_params = {
    'n_estimators': 500,
    'max_depth': 12,
    'min_samples_split': 10,
    'min_samples_leaf': 4,
    'max_features': 'sqrt',
    'class_weight': 'balanced_subsample',
    'random_state': 42
}

# Ensemble Strategy: Stacking
# Meta-learner: Logistic Regression on XGBoost + RF probabilities
```

### 2.3 Model Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT FEATURE VECTOR                      │
│   [35 engineered features from on-chain, exchange, social]  │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│     XGBoost           │       │   Random Forest       │
│   (Primary Model)     │       │  (Secondary Model)    │
│                       │       │                       │
│  - Handles imbalance  │       │  - Robust to noise    │
│  - Feature importance │       │  - Different bias     │
│  - Fast inference     │       │  - Diversity boost    │
└───────────┬───────────┘       └───────────┬───────────┘
            │                               │
            ▼                               ▼
     [Pump Probability]              [Pump Probability]
            │                               │
            └───────────────┬───────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │   Stacking Meta-Learner       │
            │   (Logistic Regression)       │
            │                               │
            │   Weights learned from        │
            │   validation performance      │
            └───────────────┬───────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │   FINAL PREDICTION            │
            │   Pump Probability: 0.87      │
            │   Confidence: 0.92            │
            │   Lead Time: 5.2 days         │
            └───────────────────────────────┘
```

---

## 3. Training Data Requirements

### 3.1 Historical Stealth Pump Examples

| Requirement | Specification | Rationale |
|------------|---------------|-----------|
| **Total Labeled Examples** | 2,500+ stealth pumps | Sufficient for model generalization |
| **Positive Class (Pumps)** | ~250 events (10%) | Class imbalance handling via scale_pos_weight |
| **Negative Class (Normal)** | ~2,250 examples | Include false positives from previous runs |
| **Time Range** | 2020-01-01 to present | Capture evolving pump strategies |
| **Token Diversity** | 500+ distinct tokens | Prevent overfitting to specific assets |
| **Chain Coverage** | ETH, BSC, SOL, ARB, BASE | Multi-chain generalization |

### 3.2 Labeling Criteria (What Constitutes a "Pump")

```python
pump_label_definition = {
    # Price Criteria
    'price_increase_7d': '> 100%',      # Minimum 2x in 7 days
    'price_increase_3d': '> 50%',       # Acceleration phase
    'volume_spike_ratio': '> 5x',       # vs 30d average
    
    # Timing Criteria
    'detection_lead_time': '4-6 days',  # Must predict BEFORE major move
    'accumulation_phase': '7-14 days',  # Quiet buying period
    
    # Exclusion Criteria (Filter Out)
    'exclude_major_news': True,         # Fundamental-driven pumps
    'exclude_listing_announcements': True,  # Exchange listing effects
    'exclude_market_wide_rallies': True,    # BTC correlation > 0.8
    
    # Confirmation Criteria
    'post_pump_dump': '< -30% in 7d after peak',  # Classic P&D pattern
    'wallet_distribution_shift': 'top_10 holders reduce by >20%'
}
```

### 3.3 Data Sources & Collection

| Data Type | Source | Frequency | Historical Depth | Cost Est. |
|-----------|--------|-----------|------------------|-----------|
| On-chain transactions | Dune Analytics, Nansen | Real-time | 4+ years | $2K-5K/mo |
| Exchange flows | Glassnode, CryptoQuant | Hourly | 3+ years | $1K-3K/mo |
| Order book data | Binance, Coinbase APIs | 1-second | 2+ years | API limits |
| Social sentiment | LunarCrush, Twitter API | 15-minute | 3+ years | $500-2K/mo |
| DEX liquidity | TheGraph, DEX Screener | Real-time | 3+ years | $500/mo |
| Wallet labels | Arkham, Nansen | Weekly updates | 2+ years | $3K-10K/mo |

### 3.4 Data Quality & Validation

```python
# Data Validation Pipeline
def validate_training_sample(sample):
    checks = {
        'temporal_consistency': verify_feature_timestamps(sample),
        'label_integrity': cross_reference_pump_events(sample),
        'feature_completeness': check_missing_values(sample, threshold=0.05),
        'outlier_detection': z_score_check(sample, threshold=5),
        'survivorship_bias': include_failed pumps and delisted tokens
    }
    return all(checks.values())

# Train/Validation/Test Split (Time-Based)
# Critical: Prevent data leakage from future pumps
train_period = '2020-01-01 to 2022-06-30'    # 60%
val_period = '2022-07-01 to 2023-06-30'      # 20%  
test_period = '2023-07-01 to present'        # 20%
```

---

## 4. Real-Time Inference Architecture

### 4.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION LAYER                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
│  │  On-Chain    │ │   Exchange   │ │    Social    │ │   DEX LPs    ││
│  │  Streams     │ │    APIs      │ │   Streams    │ │   TheGraph   ││
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘│
└─────────┼────────────────┼────────────────┼────────────────┼────────┘
          │                │                │                │
          └────────────────┴────────────────┴────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FEATURE ENGINEERING PIPELINE                    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  Stream Processing (Apache Flink / Kafka Streams)               ││
│  │  - Windowed aggregations (1h, 4h, 24h tumbling windows)        ││
│  │  - Real-time wallet clustering                                  ││
│  │  - Anomaly detection on feature streams                         ││
│  └────────────────────────────────┬────────────────────────────────┘│
└───────────────────────────────────┼──────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       MODEL SERVING LAYER                            │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  Model Server (Triton / Seldon Core / Custom Flask)             ││
│  │                                                                  ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  ││
│  │  │  XGBoost     │  │  Random      │  │  Ensemble Logic      │  ││
│  │  │  Model       │  │  Forest      │  │  (Weighted Avg)      │  ││
│  │  │  (ONNX)      │  │  Model       │  │                      │  ││
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘  ││
│  │                                                                  ││
│  │  Latency Target: < 50ms p99 inference time                     ││
│  └─────────────────────────────────────────────────────────────────┘│
└───────────────────────────────────┼──────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ALERT & ACTION LAYER                            │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │  Confidence  │  │   Alert      │  │   Position   │  │  Audit   │ │
│  │  Scoring     │  │   Routing    │  │   Sizing     │  │  Logging │ │
│  │              │  │  (Discord,   │  │  (Kelly/     │  │          │ │
│  │  Thresholds: │  │   Telegram,  │  │  Risk-based) │  │  All     │ │
│  │  >0.8: High  │  │   Webhook)   │  │              │  │  preds   │ │
│  │  0.6-0.8: Med│  │              │  │              │  │  logged  │ │
│  │  <0.6: Low   │  │              │  │              │  │          │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Infrastructure Specifications

| Component | Technology | Specs | Cost/Month |
|-----------|-----------|-------|------------|
| Stream Processing | Apache Kafka + Flink | 3-node cluster, 32GB RAM each | $800-1,500 |
| Feature Store | Feast (Redis backend) | Sub-10ms feature retrieval | $400-800 |
| Model Serving | NVIDIA Triton | 1x GPU instance (A10G) | $1,000-1,500 |
| Database (Raw) | TimescaleDB | 2TB time-series storage | $300-600 |
| Database (Features) | Redis Cluster | In-memory feature cache | $200-400 |
| Monitoring | Prometheus + Grafana | Metrics & alerting | $100-200 |
| **Total Infrastructure** | | | **$2,800-5,000** |

### 4.3 Inference Workflow

```python
class StealthPumpInferencePipeline:
    """
    Real-time inference pipeline with <100ms end-to-end latency
    """
    
    def __init__(self):
        self.xgb_model = load_xgboost_model('models/xgb_primary.json')
        self.rf_model = load_sklearn_model('models/rf_secondary.pkl')
        self.feature_store = FeatureStoreClient()
        
    def predict(self, token_address: str) -> PredictionResult:
        # Step 1: Fetch real-time features (target: <30ms)
        features = self.feature_store.get_online_features(
            entity_rows=[{'token_address': token_address}],
            feature_refs=self.feature_list
        )
        
        # Step 2: Preprocess (target: <10ms)
        feature_vector = self.preprocessor.transform(features)
        
        # Step 3: Model inference (target: <20ms)
        xgb_prob = self.xgb_model.predict_proba(feature_vector)[0][1]
        rf_prob = self.rf_model.predict_proba(feature_vector)[0][1]
        
        # Step 4: Ensemble (target: <5ms)
        final_prob = 0.6 * xgb_prob + 0.4 * rf_prob
        
        # Step 5: Post-processing
        confidence = self.calculate_confidence_interval(features)
        lead_time_estimate = self.estimate_lead_time(features)
        
        return PredictionResult(
            token=token_address,
            pump_probability=final_prob,
            confidence=confidence,
            estimated_lead_time_days=lead_time_estimate,
            top_features=self.get_shap_explanation(feature_vector),
            timestamp=datetime.utcnow()
        )
    
    def should_alert(self, prediction: PredictionResult) -> bool:
        return (
            prediction.pump_probability > 0.75 and
            prediction.confidence > 0.7 and
            prediction.estimated_lead_time_days >= 4
        )
```

### 4.4 Latency Budget

| Stage | Target Latency | Max Latency | Optimization |
|-------|---------------|-------------|--------------|
| Feature retrieval | 20ms | 50ms | Redis caching, pre-aggregated windows |
| Feature computation | 15ms | 30ms | Incremental updates, materialized views |
| Model inference | 10ms | 25ms | ONNX runtime, GPU batching |
| Post-processing | 5ms | 15ms | Optimized NumPy operations |
| Network overhead | 10ms | 20ms | Same-region deployment |
| **Total End-to-End** | **60ms** | **140ms** | **p99 < 100ms** |

---

## 5. Performance Targets & Evaluation

### 5.1 Target Metrics

| Metric | Target | Minimum Acceptable | Measurement |
|--------|--------|-------------------|-------------|
| **F1-Score** | ≥ 87% | ≥ 82% | On held-out test set (time-based split) |
| **Precision** | ≥ 80% | ≥ 75% | Avoid false positive fatigue |
| **Recall** | ≥ 85% | ≥ 80% | Don't miss real pumps |
| **Lead Time Accuracy** | ±1 day | ±2 days | Predicted vs actual pump start |
| **Inference Latency** | < 60ms | < 100ms | p99 latency per prediction |
| **Throughput** | 1,000 TPS | 500 TPS | Tokens evaluated per second |

### 5.2 Evaluation Framework

```python
# Time-Based Cross-Validation
def time_series_cv(model, X, y, dates, n_splits=5):
    """
    Ensure no data leakage from future pumps
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    scores = []
    
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        scores.append({
            'f1': f1_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'lead_time_error': mean_absolute_error(actual_lead, predicted_lead)
        })
    
    return scores

# Business Impact Metrics
def calculate_profit_factor(predictions, actual_returns):
    """
    Ultimate metric: Does it make money?
    """
    true_positives = predictions[predictions == 1 & actual_returns > 0.5]
    false_positives = predictions[predictions == 1 & actual_returns < 0.1]
    
    avg_win = true_positives.mean_return
    avg_loss = false_positives.mean_return
    win_rate = len(true_positives) / (len(true_positives) + len(false_positives))
    
    return {
        'profit_factor': avg_win / abs(avg_loss),
        'win_rate': win_rate,
        'expectancy': (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))
    }
```

### 5.3 Model Monitoring & Drift Detection

| Drift Type | Detection Method | Threshold | Action |
|------------|------------------|-----------|--------|
| **Data Drift** | KS-test on feature distributions | p < 0.05 | Alert, trigger retraining |
| **Concept Drift** | Performance decay on recent labels | F1 drop > 5% | Immediate retraining |
| **Prediction Drift** | Distribution shift in output probabilities | KL divergence > 0.1 | Investigate, review features |
| **Feature Drift** | PSI (Population Stability Index) | PSI > 0.25 | Feature engineering review |

---

## 6. Implementation Roadmap

### Phase 1: MVP (Weeks 1-4)
- [ ] Collect and label 500 historical pump events
- [ ] Implement 15 core on-chain features
- [ ] Train baseline XGBoost model (target: 80% F1)
- [ ] Build simple batch inference pipeline

### Phase 2: Production v1 (Weeks 5-8)
- [ ] Expand to full 35-feature set
- [ ] Implement real-time streaming pipeline
- [ ] Deploy XGBoost + RF ensemble
- [ ] Build alerting system (Discord/Telegram)
- [ ] Target: 85% F1, <100ms inference

### Phase 3: Optimization (Weeks 9-12)
- [ ] Hyperparameter tuning with Optuna
- [ ] Feature selection and engineering refinements
- [ ] Implement full monitoring suite
- [ ] A/B test model variants
- [ ] Target: 87%+ F1, <60ms inference

### Phase 4: Scale (Weeks 13-16)
- [ ] Multi-chain expansion (BSC, SOL, ARB)
- [ ] Advanced wallet clustering algorithms
- [ ] Transfer learning for new chains
- [ ] Automated retraining pipeline

---

## 7. Risk & Limitations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Adversarial pump groups evolve tactics | High | Model degradation | Continuous monitoring, active learning |
| Data quality issues (RPC failures) | Medium | False signals | Redundant data sources, fallback logic |
| Exchange API rate limits | Medium | Data gaps | Multiple exchange feeds, priority queuing |
| Overfitting to historical patterns | Medium | Poor generalization | Strict time-based validation, regularization |
| Regulatory changes | Low | Data availability | Diversified global data sources |

---

## 8. Appendix: Feature Importance Reference

Based on preliminary analysis of historical stealth pumps, expected SHAP feature importance rankings:

| Rank | Feature | Expected Importance | Rationale |
|------|---------|---------------------|-----------|
| 1 | `cluster_concentration` | 0.18 | Coordinated buying is the strongest signal |
| 2 | `cex_netflow_7d` | 0.14 | Institutional/smart money leads retail |
| 3 | `new_whale_ratio` | 0.12 | Fresh wallets = new participants |
| 4 | `velocity_variance` | 0.10 | Unusual transaction patterns |
| 5 | `similar_token_pre_pump` | 0.09 | Groups often repeat patterns |
| 6 | `API_composite` | 0.08 | Combined accumulation pressure |
| 7 | `stealth_wallet_count` | 0.07 | Intentional low-visibility |
| 8 | `withdrawal_to_deposit_ratio` | 0.06 | Moving off exchanges = holding |
| 9 | `social_volume_acceleration` | 0.05 | Early chatter before public pump |
| 10 | `velocity_24h_change` | 0.04 | Short-term velocity shifts |

---

*Document Version: 1.0*  
*Last Updated: 2026-03-09*  
*Author: ML Pipeline Design Sub-agent*
