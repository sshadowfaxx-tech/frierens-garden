# Alpha Wallet Discovery Methods: The Ultimate Solana Wallet Hunting System

## Executive Summary

This research document outlines comprehensive strategies for discovering profitable Solana wallets that aren't publicly known or followed. The ultimate alpha discovery system combines reverse engineering, community intelligence, technical analysis, automated scoring, and real-time monitoring.

---

## 1. REVERSE ENGINEERING SUCCESS

### 1.1 Starting with Profitable Tokens - Backward Analysis

The most effective method for finding alpha wallets is working backward from successful tokens.

#### Methodology: The Early Buyer Pipeline

```python
# Pseudo-code for Early Buyer Discovery Pipeline
class EarlyBuyerDiscovery:
    def __init__(self, helius_api_key):
        self.helius = HeliusClient(api_key)
        
    async def find_early_buyers(self, token_address, success_threshold=5):
        """
        Find wallets that bought a successful token within first 24h of launch
        and made >500% returns
        """
        # Get token launch timestamp
        launch_tx = await self.helius.get_token_creation(token_address)
        launch_time = launch_tx['timestamp']
        
        # Get first 24h of transactions
        early_transactions = await self.helius.get_transactions(
            token_address,
            start_time=launch_time,
            end_time=launch_time + 86400
        )
        
        # Filter for buys only (exclude sells, lp adds)
        early_buyers = []
        for tx in early_transactions:
            if self.is_buy_transaction(tx):
                wallet = tx['buyer_wallet']
                buy_price = tx['token_price_usd']
                
                # Calculate if they sold at profit
                sells = await self.get_subsequent_sells(wallet, token_address)
                roi = self.calculate_roi(buy_price, sells)
                
                if roi >= success_threshold:  # 5x minimum
                    early_buyers.append({
                        'wallet': wallet,
                        'buy_time': tx['timestamp'],
                        'buy_amount': tx['amount_usd'],
                        'roi': roi,
                        'hold_time': self.calculate_hold_time(tx, sells)
                    })
        
        return sorted(early_buyers, key=lambda x: x['roi'], reverse=True)
```

#### Helius API Implementation

```python
import aiohttp
import asyncio
from datetime import datetime, timedelta

class HeliusWalletAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.helius.xyz/v0"
        
    async def get_wallet_history(self, wallet_address, days_back=90):
        """Fetch complete transaction history for analysis"""
        url = f"{self.base_url}/addresses/{wallet_address}/transactions"
        params = {
            "api-key": self.api_key,
            "limit": 100,
            "type": "SWAP|TRANSFER|TOKEN_MINT"
        }
        
        all_transactions = []
        before = None
        
        async with aiohttp.ClientSession() as session:
            while True:
                if before:
                    params["before"] = before
                    
                async with session.get(url, params=params) as resp:
                    data = await resp.json()
                    
                    if not data.get('transactions'):
                        break
                        
                    all_transactions.extend(data['transactions'])
                    
                    # Stop if we've gone back far enough
                    oldest_tx = data['transactions'][-1]
                    tx_time = datetime.fromtimestamp(oldest_tx['timestamp'])
                    if datetime.now() - tx_time > timedelta(days=days_back):
                        break
                    
                    before = oldest_tx['signature']
                    
        return all_transactions
    
    async def get_token_holders(self, token_address):
        """Get top holders with their balances"""
        url = f"{self.base_url}/token-holders"
        params = {
            "api-key": self.api_key,
            "mintAddress": token_address,
            "limit": 100
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                return await resp.json()
```

### 1.2 Analyzing Top Holders of Successful Launches

#### The 100x Token Analysis Framework

```python
class SuccessfulTokenAnalyzer:
    """Analyze tokens that did 100x+ to find common early buyer patterns"""
    
    SUCCESS_CRITERIA = {
        'min_roi': 50,           # 50x minimum
        'min_market_cap_peak': 50_000_000,  # $50M peak MC
        'min_liquidity_period': 30,  # Days with >$100k liquidity
    }
    
    def analyze_successful_launch(self, token_address):
        report = {
            'early_buyer_profiles': [],
            'buy_timing_patterns': [],
            'wallet_clusters': [],
            'profit_realization_patterns': []
        }
        
        # Get all wallets that bought in first 48h
        early_buyers = self.get_early_buyers(token_address, hours=48)
        
        for wallet in early_buyers:
            profile = self.create_buyer_profile(wallet, token_address)
            
            # Check if this wallet is "stealth" (not known influencer/fundy)
            if self.is_stealth_wallet(wallet):
                report['early_buyer_profiles'].append(profile)
        
        # Cluster analysis - find groups of wallets buying together
        report['wallet_clusters'] = self.detect_coordinated_buying(early_buyers)
        
        return report
    
    def is_stealth_wallet(self, wallet_address):
        """
        Determine if wallet is unknown/untracked alpha
        """
        checks = {
            'twitter_mentions': self.check_twitter_history(wallet_address),
            'known_fund': self.check_fund_databases(wallet_address),
            'nansen_label': self.check_nansen_labels(wallet_address),
            'public_lists': self.check_public_tracking_lists(wallet_address),
            'social_following': self.check_social_graph(wallet_address)
        }
        
        # Stealth = minimal public association
        return sum(checks.values()) < 2
    
    def create_buyer_profile(self, wallet, token):
        """Create detailed profile of early buyer"""
        history = self.get_wallet_history(wallet, days=180)
        
        return {
            'address': wallet,
            'entry_timing': self.get_entry_timing(wallet, token),
            'position_size_usd': self.get_position_size(wallet, token),
            'wallet_balance_at_entry': self.get_historical_balance(wallet, token),
            'profit_realized': self.calculate_realized_profit(wallet, token),
            'other_tokens_bought_early': self.find_other_early_buys(wallet),
            'win_rate': self.calculate_win_rate(history),
            'avg_hold_time': self.calculate_avg_hold_time(history),
            'trade_frequency': self.calculate_trade_frequency(history),
            'concentration_ratio': self.calculate_concentration(history),
            'stealth_score': self.calculate_stealth_score(wallet)
        }
```

### 1.3 Tracking Smart Money Movements

#### Multi-Token Success Pattern Detection

```python
class SmartMoneyTracker:
    """Track wallets that consistently find winners"""
    
    def __init__(self):
        self.scored_wallets = {}
        
    async def score_wallet_alpha(self, wallet_address):
        """
        Score a wallet based on alpha generation capability
        """
        score = {
            'early_detection_rate': 0,    # % of tokens bought <24h after launch
            'win_rate': 0,                # % of trades profitable
            'average_roi': 0,             # Average return on winning trades
            'consistency_score': 0,       # Consistency over time
            'stealth_factor': 0,          # How unknown this wallet is
            'total_alpha_score': 0
        }
        
        # Get all token purchases
        token_buys = await self.get_all_token_purchases(wallet_address)
        
        for buy in token_buys:
            token = buy['token_address']
            buy_time = buy['timestamp']
            
            # Check if this was early
            launch_time = await self.get_token_launch_time(token)
            hours_after_launch = (buy_time - launch_time) / 3600
            
            if hours_after_launch < 24:
                # Check if token became successful
                peak_mcap = await self.get_peak_market_cap(token)
                current_mcap = await self.get_current_market_cap(token)
                
                if peak_mcap > buy['market_cap_at_buy'] * 10:  # 10x+ token
                    score['early_detection_rate'] += 1
                    
        # Calculate final metrics
        total_tokens = len(token_buys)
        if total_tokens > 0:
            score['early_detection_rate'] /= total_tokens
            
        # Win rate calculation
        profitable_trades = await self.get_profitable_trades(wallet_address)
        score['win_rate'] = len(profitable_trades) / total_tokens if total_tokens > 0 else 0
        
        # Calculate weighted alpha score
        score['total_alpha_score'] = (
            score['early_detection_rate'] * 0.35 +
            score['win_rate'] * 0.25 +
            score['stealth_factor'] * 0.25 +
            score['consistency_score'] * 0.15
        )
        
        return score
```

---

## 2. COMMUNITY & DISCORD INTEL

### 2.1 Where Alpha Callers Congregate

#### Key Community Sources

| Platform | Community Type | Signal Quality | Access Level |
|----------|---------------|----------------|--------------|
| Discord Private Groups | Paid alpha groups | High | $50-500/month |
| Telegram Channels | Caller groups | Medium-High | Free-$100/month |
| Twitter/X Lists | Influencer wallets | Medium | Free |
| Pump.fun Livestream | Dev reveals | Variable | Free |
| Protocol Discords | Dev/Contributor chat | Very High | Engagement-based |

#### Discord Intel Gathering Architecture

```python
class DiscordIntelGatherer:
    """Gather wallet intelligence from Discord communities"""
    
    TARGET_CHANNELS = [
        # Alpha/Call groups
        'alpha-calls',
        'whale-wallets',
        'early-entry',
        'gems-chat',
        
        # Dev channels (if accessible)
        'dev-chat',
        'testnet-updates',
        'contributors',
    ]
    
    def __init__(self, discord_bot_token):
        self.discord = DiscordClient(token=discord_bot_token)
        self.wallet_extractor = WalletAddressExtractor()
        
    async def monitor_channels(self, guild_ids):
        """Monitor configured channels for wallet addresses"""
        
        @self.discord.event
        async def on_message(message):
            # Skip bot messages
            if message.author.bot:
                return
                
            # Extract potential wallet addresses
            content = message.content
            wallets = self.wallet_extractor.extract_solana_addresses(content)
            
            if wallets:
                for wallet in wallets:
                    intel = await self.process_wallet_mention(
                        wallet=wallet,
                        context={
                            'channel': message.channel.name,
                            'author': str(message.author),
                            'content': content,
                            'timestamp': message.created_at,
                            'guild': message.guild.name if message.guild else None
                        }
                    )
                    
                    await self.store_intel(intel)
    
    async def process_wallet_mention(self, wallet, context):
        """Analyze a wallet mentioned in Discord"""
        
        # Get current wallet stats
        stats = await self.get_wallet_quick_stats(wallet)
        
        intel = {
            'wallet': wallet,
            'source': 'discord',
            'context': context,
            'discovered_at': datetime.now(),
            'wallet_stats_at_discovery': stats,
            'source_credibility': self.score_source_credibility(context),
            'wallet_age_days': stats.get('wallet_age_days'),
            'current_portfolio_value': stats.get('total_value_usd'),
            'recent_activity': stats.get('recent_transactions_7d'),
            'alpha_potential': None  # To be calculated
        }
        
        # Quick alpha check
        if stats.get('win_rate_30d', 0) > 0.6:
            intel['alpha_potential'] = 'HIGH'
        elif stats.get('early_buys_30d', 0) > 3:
            intel['alpha_potential'] = 'MEDIUM'
            
        return intel
    
    def score_source_credibility(self, context):
        """Score how credible a Discord source is"""
        score = 0
        
        # Paid groups typically higher signal
        if any(x in context['guild'].lower() for x in ['alpha', 'premium', 'whale']):
            score += 2
            
        # Check channel type
        if 'alpha' in context['channel'].lower():
            score += 2
        elif 'general' in context['channel'].lower():
            score += 0.5
            
        # Author reputation (if tracked)
        author_score = self.get_author_reputation(context['author'])
        score += author_score
        
        return min(score, 5)
```

### 2.2 Monitoring Dev/Team Wallets

#### Protocol Contributor Discovery

```python
class DevWalletTracker:
    """Find and monitor wallets of protocol developers and contributors"""
    
    DISCOVERY_METHODS = [
        'github_commit_associations',  # Link GitHub to wallets
        'testnet_funding_trails',      # Follow testnet -> mainnet
        'multisig_signers',            # Monitor protocol multisigs
        'grant_recipients',            # Track grant fund recipients
        'bug_bounty_payments',         # Bug bounty program payouts
    ]
    
    async def find_contributor_wallets(self, protocol_name):
        """Find wallets belonging to protocol contributors"""
        wallets = []
        
        # Method 1: Testnet → Mainnet migration tracking
        testnet_wallets = await self.analyze_testnet_activity(protocol_name)
        for wallet in testnet_wallets:
            mainnet_match = await self.find_mainnet_counterpart(wallet)
            if mainnet_match:
                wallets.append({
                    'address': mainnet_match,
                    'discovery_method': 'testnet_migration',
                    'testnet_wallet': wallet,
                    'confidence': 0.85
                })
        
        # Method 2: Multisig signer analysis
        protocol_multisigs = await self.get_protocol_multisigs(protocol_name)
        for multisig in protocol_multisigs:
            signers = await self.get_multisig_signers(multisig)
            for signer in signers:
                wallets.append({
                    'address': signer,
                    'discovery_method': 'multisig_signer',
                    'multisig': multisig,
                    'confidence': 0.95
                })
        
        return wallets
    
    async def analyze_testnet_activity(self, protocol_name):
        """
        Track testnet wallets that might migrate to mainnet
        """
        # Query testnet (devnet) for protocol interactions
        devnet_programs = await self.get_devnet_programs(protocol_name)
        
        unique_interactors = set()
        for program in devnet_programs:
            # Get recent transaction signers
            signers = await self.helius.get_program_signers(
                program,
                cluster='devnet',
                limit=1000
            )
            unique_interactors.update(signers)
        
        return list(unique_interactors)
    
    async def find_mainnet_counterpart(self, testnet_wallet):
        """
        Try to find mainnet wallet linked to testnet wallet
        """
        # Method: Check for funding patterns
        # Often devs fund testnet wallets from mainnet
        
        testnet_funders = await self.get_testnet_funders(testnet_wallet)
        
        for funder in testnet_funders:
            # Check if funder has mainnet activity
            mainnet_balance = await self.get_mainnet_balance(funder)
            if mainnet_balance > 0:
                # Check transaction patterns match
                if await self.pattern_match(testnet_wallet, funder):
                    return funder
        
        return None
```

### 2.3 Testnet → Mainnet Migration Tracking

```python
class TestnetMigrationTracker:
    """
    Critical alpha source: Follow devs from testnet to mainnet
    """
    
    async def track_devnet_to_mainnet(self):
        """Monitor for wallets active on devnet that appear on mainnet"""
        
        # Get recently funded devnet wallets
        devnet_wallets = await self.get_recently_funded_devnet_wallets(days=7)
        
        migrations = []
        for wallet in devnet_wallets:
            # Check for mainnet counterpart
            mainnet_wallet = await self.correlate_to_mainnet(wallet)
            
            if mainnet_wallet:
                # Check what they're buying on mainnet
                mainnet_activity = await self.get_recent_mainnet_activity(
                    mainnet_wallet, 
                    hours=48
                )
                
                if mainnet_activity:
                    migrations.append({
                        'devnet_wallet': wallet,
                        'mainnet_wallet': mainnet_wallet,
                        'first_mainnet_activity': mainnet_activity[0]['timestamp'],
                        'tokens_purchased': [tx['token'] for tx in mainnet_activity],
                        'total_volume_48h': sum(tx['amount'] for tx in mainnet_activity),
                        'alpha_urgency': 'HIGH'  # Fresh migration = potential alpha
                    })
        
        return migrations
    
    async def correlate_to_mainnet(self, devnet_wallet):
        """
        Match devnet wallet to mainnet using multiple signals
        """
        signals = []
        
        # Signal 1: Common funding source
        devnet_funders = await self.get_devnet_funders(devnet_wallet)
        for funder in devnet_funders:
            if await self.has_mainnet_presence(funder):
                signals.append(('funding_source', funder, 0.4))
        
        # Signal 2: Transaction pattern similarity
        pattern_match = await self.compare_transaction_patterns(devnet_wallet)
        if pattern_match:
            signals.append(('pattern_match', pattern_match, 0.35))
        
        # Signal 3: Temporal correlation (devnet stops, mainnet starts)
        temporal_match = await self.check_temporal_correlation(devnet_wallet)
        if temporal_match:
            signals.append(('temporal', temporal_match, 0.25))
        
        # Combine signals
        if signals:
            total_confidence = sum(s[2] for s in signals)
            if total_confidence > 0.7:
                return signals[0][1]  # Return highest confidence match
        
        return None
```

---

## 3. TECHNICAL ANALYSIS OF WALLETS

### 3.1 Portfolio Concentration Analysis

```python
class PortfolioConcentrationAnalyzer:
    """Analyze how wallets allocate capital across positions"""
    
    CONCENTRATION_PROFILES = {
        'HIGH_CONCENTRATION': {
            'description': 'All-in style, high conviction plays',
            'typical_allocation': '>50% in single position',
            'risk_level': 'High',
            'alpha_potential': 'Very High'
        },
        'MODERATE_CONCENTRATION': {
            'description': '3-5 core positions',
            'typical_allocation': '20-40% per position',
            'risk_level': 'Medium',
            'alpha_potential': 'High'
        },
        'DIVERSIFIED': {
            'description': 'Many small positions',
            'typical_allocation': '<10% per position',
            'risk_level': 'Low',
            'alpha_potential': 'Medium'
        },
        'SINGLE_PLAY': {
            'description': 'New wallet, one position',
            'typical_allocation': '100%',
            'risk_level': 'Very High',
            'alpha_potential': 'Variable'
        }
    }
    
    async def analyze_concentration(self, wallet_address):
        """Analyze portfolio concentration patterns"""
        
        holdings = await self.get_current_holdings(wallet_address)
        total_value = sum(h['value_usd'] for h in holdings)
        
        if total_value == 0:
            return {'profile': 'EMPTY', 'concentration_score': 0}
        
        # Calculate concentration metrics
        allocations = []
        for holding in holdings:
            allocation_pct = holding['value_usd'] / total_value
            allocations.append({
                'token': holding['token'],
                'value_usd': holding['value_usd'],
                'allocation_pct': allocation_pct,
                'entry_time': holding.get('first_acquired')
            })
        
        # Sort by allocation
        allocations.sort(key=lambda x: x['allocation_pct'], reverse=True)
        
        # Calculate Herfindahl-Hirschman Index (concentration measure)
        hhi = sum(a['allocation_pct'] ** 2 for a in allocations)
        
        # Determine profile
        if len(allocations) == 1:
            profile = 'SINGLE_PLAY'
        elif hhi > 0.5:  # >50% in top position
            profile = 'HIGH_CONCENTRATION'
        elif hhi > 0.25:
            profile = 'MODERATE_CONCENTRATION'
        else:
            profile = 'DIVERSIFIED'
        
        return {
            'profile': profile,
            'concentration_score': hhi,
            'top_holdings': allocations[:5],
            'num_positions': len(allocations),
            'total_portfolio_value': total_value,
            'profile_description': self.CONCENTRATION_PROFILES[profile]
        }
    
    async def analyze_rotation_patterns(self, wallet_address):
        """
        Analyze how wallet rotates between concentrated positions
        """
        history = await self.get_wallet_history(wallet_address, days=90)
        
        rotations = []
        current_positions = {}
        
        for tx in sorted(history, key=lambda x: x['timestamp']):
            if tx['type'] == 'BUY':
                token = tx['token']
                if token not in current_positions:
                    # New position
                    rotations.append({
                        'action': 'ENTER',
                        'token': token,
                        'timestamp': tx['timestamp'],
                        'amount': tx['amount_usd'],
                        'concentration_at_entry': len(current_positions)
                    })
                    current_positions[token] = tx['amount_usd']
                    
            elif tx['type'] == 'SELL':
                token = tx['token']
                if token in current_positions:
                    # Full or partial exit
                    rotations.append({
                        'action': 'EXIT',
                        'token': token,
                        'timestamp': tx['timestamp'],
                        'amount': tx['amount_usd'],
                        'hold_duration_hours': self.calculate_hold_duration(
                            current_positions[token], tx['timestamp']
                        )
                    })
                    del current_positions[token]
        
        return {
            'rotation_count_90d': len(rotations),
            'avg_hold_time_hours': self.avg_hold_time(rotations),
            'position_turnover_rate': len(rotations) / 90,  # per day
            'concentration_behavior': self.classify_rotation_style(rotations)
        }
```

### 3.2 Diversification vs Concentration Strategies

```python
class StrategyClassifier:
    """Classify wallet trading strategies"""
    
    STRATEGY_TYPES = {
        'SNIPER': {
            'pattern': 'Ultra-early entry, quick rotation',
            'avg_hold_time': '<1 hour',
            'position_count': 'High turnover',
            'win_condition': 'Speed, information edge'
        },
        'SWING_TRADER': {
            'pattern': 'Days to weeks hold, momentum capture',
            'avg_hold_time': '1-14 days',
            'position_count': '3-8 active',
            'win_condition': 'Timing, trend recognition'
        },
        'CONVICTION_INVESTOR': {
            'pattern': 'Few positions, high confidence',
            'avg_hold_time': 'Weeks to months',
            'position_count': '1-3 core positions',
            'win_condition': 'Fundamental thesis, patience'
        },
        'INDEXER': {
            'pattern': 'Broad exposure, systematic',
            'avg_hold_time': 'Variable',
            'position_count': '20+ positions',
            'win_condition': 'Diversification, market beta'
        },
        'ARBITRAGEUR': {
            'pattern': 'Same-token, cross-venue trades',
            'avg_hold_time': 'Minutes',
            'position_count': 'High frequency',
            'win_condition': 'Latency, execution'
        }
    }
    
    async def classify_wallet_strategy(self, wallet_address):
        """Determine the trading strategy of a wallet"""
        
        history = await self.get_trade_history(wallet_address, days=30)
        
        if len(history) < 5:
            return {'strategy': 'INSUFFICIENT_DATA', 'confidence': 0}
        
        metrics = {
            'avg_hold_time_hours': self.calculate_avg_hold_time(history),
            'trades_per_day': len(history) / 30,
            'unique_tokens_traded': len(set(t['token'] for t in history)),
            'avg_position_size': self.calculate_avg_position_size(history),
            'win_rate': self.calculate_win_rate(history),
            'profit_factor': self.calculate_profit_factor(history)
        }
        
        # Classification rules
        if metrics['avg_hold_time_hours'] < 1 and metrics['trades_per_day'] > 20:
            strategy = 'SNIPER'
        elif metrics['avg_hold_time_hours'] < 0.1:
            strategy = 'ARBITRAGEUR'
        elif metrics['avg_hold_time_hours'] < 24 * 14:
            strategy = 'SWING_TRADER'
        elif metrics['unique_tokens_traded'] > 20:
            strategy = 'INDEXER'
        else:
            strategy = 'CONVICTION_INVESTOR'
        
        return {
            'strategy': strategy,
            'confidence': self.calculate_strategy_confidence(metrics, strategy),
            'metrics': metrics,
            'description': self.STRATEGY_TYPES[strategy]
        }
```

### 3.3 Position Sizing & Timing Pattern Analysis

```python
class PositionSizingAnalyzer:
    """Analyze how wallets size positions and time entries"""
    
    async def analyze_position_sizing(self, wallet_address):
        """
        Analyze position sizing relative to wallet balance
        """
        trades = await self.get_trade_history(wallet_address)
        
        sizing_patterns = []
        
        for trade in trades:
            # Get wallet balance at time of trade
            balance_at_trade = await self.get_historical_balance(
                wallet_address, 
                trade['timestamp']
            )
            
            if balance_at_trade > 0:
                position_pct = trade['amount_usd'] / balance_at_trade
                
                sizing_patterns.append({
                    'timestamp': trade['timestamp'],
                    'token': trade['token'],
                    'position_size_usd': trade['amount_usd'],
                    'wallet_balance': balance_at_trade,
                    'position_pct_of_portfolio': position_pct,
                    'market_cap_at_entry': trade.get('market_cap'),
                    'token_age_at_entry': trade.get('token_age_hours')
                })
        
        # Analyze patterns
        avg_position_pct = sum(p['position_pct_of_portfolio'] for p in sizing_patterns) / len(sizing_patterns)
        
        # Categorize sizing behavior
        if avg_position_pct > 0.5:
            sizing_style = 'AGGRESSIVE'
        elif avg_position_pct > 0.2:
            sizing_style = 'MODERATE'
        else:
            sizing_style = 'CONSERVATIVE'
        
        # Analyze market cap preference
        mcap_buckets = {
            'micro': [],      # <$100k
            'small': [],      # $100k-$1M
            'medium': [],     # $1M-$10M
            'large': []       # >$10M
        }
        
        for p in sizing_patterns:
            mcap = p.get('market_cap_at_entry', 0)
            if mcap < 100000:
                mcap_buckets['micro'].append(p)
            elif mcap < 1000000:
                mcap_buckets['small'].append(p)
            elif mcap < 10000000:
                mcap_buckets['medium'].append(p)
            else:
                mcap_buckets['large'].append(p)
        
        # Find preferred market cap range
        preferred_mcap = max(mcap_buckets, key=lambda k: len(mcap_buckets[k]))
        
        return {
            'sizing_style': sizing_style,
            'avg_position_pct': avg_position_pct,
            'preferred_market_cap_range': preferred_mcap,
            'mcap_distribution': {k: len(v) for k, v in mcap_buckets.items()},
            'sizing_consistency': self.calculate_sizing_consistency(sizing_patterns),
            'patterns': sizing_patterns[-20:]  # Last 20 trades
        }
    
    async def analyze_timing_patterns(self, wallet_address):
        """
        Analyze when wallet tends to make profitable trades
        """
        trades = await self.get_trade_history(wallet_address)
        
        timing_analysis = {
            'hour_of_day': {},
            'day_of_week': {},
            'relative_to_launch': {},
            'entry_timing_quality': 0
        }
        
        for trade in trades:
            # Hour analysis
            hour = datetime.fromtimestamp(trade['timestamp']).hour
            if hour not in timing_analysis['hour_of_day']:
                timing_analysis['hour_of_day'][hour] = {'trades': 0, 'wins': 0}
            timing_analysis['hour_of_day'][hour]['trades'] += 1
            if trade.get('profitable'):
                timing_analysis['hour_of_day'][hour]['wins'] += 1
            
            # Day of week analysis
            day = datetime.fromtimestamp(trade['timestamp']).weekday()
            if day not in timing_analysis['day_of_week']:
                timing_analysis['day_of_week'][day] = {'trades': 0, 'wins': 0}
            timing_analysis['day_of_week'][day]['trades'] += 1
            if trade.get('profitable'):
                timing_analysis['day_of_week'][day]['wins'] += 1
            
            # Time from token launch
            token_launch = await self.get_token_launch_time(trade['token'])
            if token_launch:
                hours_from_launch = (trade['timestamp'] - token_launch) / 3600
                
                bucket = '<1h' if hours_from_launch < 1 else \
                         '1-6h' if hours_from_launch < 6 else \
                         '6-24h' if hours_from_launch < 24 else \
                         '1-7d' if hours_from_launch < 168 else '>7d'
                
                if bucket not in timing_analysis['relative_to_launch']:
                    timing_analysis['relative_to_launch'][bucket] = {'trades': 0, 'wins': 0}
                timing_analysis['relative_to_launch'][bucket]['trades'] += 1
                if trade.get('profitable'):
                    timing_analysis['relative_to_launch'][bucket]['wins'] += 1
        
        # Find optimal timing
        best_hour = max(timing_analysis['hour_of_day'].items(), 
                       key=lambda x: x[1]['wins'] / max(x[1]['trades'], 1))
        best_day = max(timing_analysis['day_of_week'].items(),
                      key=lambda x: x[1]['wins'] / max(x[1]['trades'], 1))
        best_entry = max(timing_analysis['relative_to_launch'].items(),
                        key=lambda x: x[1]['wins'] / max(x[1]['trades'], 1))
        
        return {
            'best_trading_hour': best_hour[0],
            'best_trading_day': best_day[0],
            'optimal_entry_timing': best_entry[0],
            'hour_analysis': timing_analysis['hour_of_day'],
            'day_analysis': timing_analysis['day_of_week'],
            'launch_timing_analysis': timing_analysis['relative_to_launch']
        }
```

---

## 4. AUTOMATED DISCOVERY SYSTEMS

### 4.1 Wallet Scoring Algorithm

```python
class WalletScoringEngine:
    """
    Comprehensive wallet scoring system for alpha discovery
    """
    
    WEIGHTS = {
        'profitability': 0.25,
        'early_detection': 0.20,
        'consistency': 0.15,
        'stealth_factor': 0.15,
        'risk_management': 0.10,
        'activity_quality': 0.10,
        'pattern_recognition': 0.05
    }
    
    async def calculate_wallet_score(self, wallet_address):
        """
        Calculate comprehensive alpha score for a wallet
        Returns score 0-100
        """
        score_components = {}
        
        # 1. Profitability Score (0-100)
        score_components['profitability'] = await self.score_profitability(wallet_address)
        
        # 2. Early Detection Score (0-100)
        score_components['early_detection'] = await self.score_early_detection(wallet_address)
        
        # 3. Consistency Score (0-100)
        score_components['consistency'] = await self.score_consistency(wallet_address)
        
        # 4. Stealth Factor (0-100) - Higher = more stealth
        score_components['stealth_factor'] = await self.score_stealth(wallet_address)
        
        # 5. Risk Management (0-100)
        score_components['risk_management'] = await self.score_risk_management(wallet_address)
        
        # 6. Activity Quality (0-100)
        score_components['activity_quality'] = await self.score_activity_quality(wallet_address)
        
        # 7. Pattern Recognition (0-100)
        score_components['pattern_recognition'] = await self.score_patterns(wallet_address)
        
        # Calculate weighted total
        total_score = sum(
            score_components[k] * self.WEIGHTS[k] 
            for k in score_components
        )
        
        return {
            'total_score': round(total_score, 2),
            'components': score_components,
            'grade': self.score_to_grade(total_score),
            'confidence': self.calculate_confidence(score_components),
            'recommendation': self.generate_recommendation(total_score, score_components)
        }
    
    async def score_profitability(self, wallet):
        """Score based on realized and unrealized profits"""
        trades = await self.get_trade_history(wallet, days=90)
        
        if len(trades) < 5:
            return 0
        
        # Calculate metrics
        realized_pnl = sum(t.get('realized_pnl', 0) for t in trades)
        winning_trades = [t for t in trades if t.get('realized_pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('realized_pnl', 0) <= 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0
        avg_win = sum(t['realized_pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = abs(sum(t['realized_pnl'] for t in losing_trades) / len(losing_trades)) if losing_trades else 1
        
        profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
        
        # ROI calculation
        total_invested = sum(t.get('amount_usd', 0) for t in trades if t['type'] == 'BUY')
        roi = (realized_pnl / total_invested * 100) if total_invested > 0 else 0
        
        # Score components
        win_rate_score = min(win_rate * 100, 100)
        profit_factor_score = min(profit_factor * 20, 100)  # PF of 5 = 100
        roi_score = min(max(roi, 0), 100)  # Cap at 100% ROI
        
        # Weighted combination
        score = (win_rate_score * 0.4) + (profit_factor_score * 0.3) + (roi_score * 0.3)
        
        return min(score, 100)
    
    async def score_early_detection(self, wallet):
        """Score based on ability to find tokens early"""
        trades = await self.get_trade_history(wallet, days=90)
        
        early_buys = 0
        successful_early_buys = 0
        
        for trade in trades:
            if trade['type'] != 'BUY':
                continue
                
            token = trade['token']
            token_launch = await self.get_token_launch_time(token)
            
            if not token_launch:
                continue
                
            hours_after_launch = (trade['timestamp'] - token_launch) / 3600
            
            if hours_after_launch < 24:  # Within 24h of launch
                early_buys += 1
                
                # Check if token became successful (10x+)
                peak_mcap = await self.get_peak_market_cap(token)
                entry_mcap = trade.get('market_cap_at_buy', 0)
                
                if entry_mcap > 0 and peak_mcap / entry_mcap >= 10:
                    successful_early_buys += 1
        
        if early_buys == 0:
            return 0
        
        early_success_rate = successful_early_buys / early_buys
        
        # Score based on rate and volume of early buys
        score = (early_success_rate * 70) + (min(early_buys, 10) * 3)
        
        return min(score, 100)
    
    async def score_stealth(self, wallet):
        """
        Score how "stealth" (unknown) a wallet is
        Higher score = less known = more valuable
        """
        stealth_indicators = []
        
        # Check if wallet is in public databases
        in_nansen = await self.check_nansen_labels(wallet)
        in_public_lists = await self.check_public_tracking_lists(wallet)
        twitter_mentions = await self.count_twitter_mentions(wallet)
        
        # Score inversely - less presence = higher stealth score
        if not in_nansen:
            stealth_indicators.append(30)
        if not in_public_lists:
            stealth_indicators.append(30)
        if twitter_mentions == 0:
            stealth_indicators.append(25)
        elif twitter_mentions < 5:
            stealth_indicators.append(15)
        
        # Wallet age factor (older = potentially more established)
        wallet_age = await self.get_wallet_age(wallet)
        if wallet_age > 365:  # >1 year
            stealth_indicators.append(15)
        elif wallet_age > 90:
            stealth_indicators.append(10)
        
        return min(sum(stealth_indicators), 100)
    
    async def score_consistency(self, wallet):
        """Score consistency of performance over time"""
        # Get monthly performance
        monthly_pnl = await self.get_monthly_pnl(wallet, months=6)
        
        if len(monthly_pnl) < 3:
            return 50  # Neutral for new wallets
        
        profitable_months = sum(1 for m in monthly_pnl if m['pnl'] > 0)
        consistency_ratio = profitable_months / len(monthly_pnl)
        
        # Calculate variance in returns
        returns = [m['pnl_pct'] for m in monthly_pnl]
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        
        # Lower variance = more consistent
        consistency_score = 100 - min(variance * 10, 50)
        
        # Combined score
        score = (consistency_ratio * 60) + (consistency_score * 0.4)
        
        return min(score, 100)
    
    async def score_risk_management(self, wallet):
        """Score based on risk management practices"""
        trades = await self.get_trade_history(wallet, days=90)
        
        if len(trades) < 5:
            return 50
        
        # Max drawdown analysis
        portfolio_values = await self.get_historical_portfolio_values(wallet)
        max_drawdown = self.calculate_max_drawdown(portfolio_values)
        
        # Position sizing consistency
        position_sizes = [t.get('amount_usd', 0) for t in trades if t['type'] == 'BUY']
        size_variance = self.calculate_variance(position_sizes)
        avg_size = sum(position_sizes) / len(position_sizes) if position_sizes else 1
        
        # Lower variance in position sizing = better risk management
        sizing_consistency = 100 - min((size_variance / avg_size) * 50, 50)
        
        # Drawdown score
        drawdown_score = 100 - min(max_drawdown * 2, 100)  # 50% drawdown = 0 score
        
        return (sizing_consistency * 0.5) + (drawdown_score * 0.5)
    
    def score_to_grade(self, score):
        if score >= 90: return 'S'
        if score >= 80: return 'A'
        if score >= 70: return 'B'
        if score >= 60: return 'C'
        if score >= 50: return 'D'
        return 'F'
```

### 4.2 Noise Filtering System

```python
class NoiseFilter:
    """
    Filter out market makers, arbitrageurs, and bots
    """
    
    BOT_INDICATORS = {
        'arbitrage': {
            'indicators': [
                'same_token_different_venue',
                'high_frequency_same_block',
                'zero_hold_time',
                'perfect_round_amounts'
            ],
            'threshold': 0.7
        },
        'market_maker': {
            'indicators': [
                'two_sided_quotes',
                'inventory_management',
                'consistent_spread_capture',
                'high_trade_count_low_profit'
            ],
            'threshold': 0.6
        },
        'sniper_bot': {
            'indicators': [
                'first_block_entry',
                'automated_gas_pricing',
                'identical_patterns_multiple_wallets',
                'no_manual_dex_approvals'
            ],
            'threshold': 0.75
        },
        'wash_trader': {
            'indicators': [
                'circular_trades_same_tokens',
                'repeated_counterparties',
                'volume_without_price_impact',
                'coordinated_multi_wallet'
            ],
            'threshold': 0.8
        }
    }
    
    async def classify_wallet_type(self, wallet):
        """
        Classify if wallet is bot, MM, or genuine trader
        """
        scores = {}
        
        for bot_type, config in self.BOT_INDICATORS.items():
            score = 0
            for indicator in config['indicators']:
                check = await self.check_indicator(wallet, indicator)
                if check:
                    score += 1
            
            scores[bot_type] = score / len(config['indicators'])
        
        # Determine classification
        max_score = max(scores.values())
        max_type = max(scores, key=scores.get)
        
        if max_score >= self.BOT_INDICATORS[max_type]['threshold']:
            return {
                'type': max_type.upper(),
                'confidence': max_score,
                'is_noise': True,
                'scores': scores
            }
        
        return {
            'type': 'Genuine Trader',
            'confidence': 1 - max_score,
            'is_noise': False,
            'scores': scores
        }
    
    async def check_indicator(self, wallet, indicator):
        """Check specific bot indicator"""
        checks = {
            'same_token_different_venue': self.check_arbitrage_pattern,
            'high_frequency_same_block': self.check_high_frequency,
            'zero_hold_time': self.check_zero_hold_time,
            'perfect_round_amounts': self.check_round_amounts,
            'two_sided_quotes': self.check_mm_behavior,
            'inventory_management': self.check_inventory_management,
            'first_block_entry': self.check_first_block_entry,
            'circular_trades_same_tokens': self.check_circular_trades,
            'repeated_counterparties': self.check_repeated_counterparties,
        }
        
        check_func = checks.get(indicator)
        if check_func:
            return await check_func(wallet)
        return False
    
    async def check_arbitrage_pattern(self, wallet):
        """Detect arbitrage trading patterns"""
        trades = await self.get_trade_history(wallet, days=7)
        
        # Look for buy on one venue, sell on another within minutes
        arbitrage_candidates = 0
        
        for i, trade in enumerate(trades):
            if trade['type'] != 'BUY':
                continue
                
            # Look for matching sell within 5 minutes
            for j in range(i+1, min(i+5, len(trades))):
                next_trade = trades[j]
                if (next_trade['type'] == 'SELL' and 
                    next_trade['token'] == trade['token'] and
                    next_trade['timestamp'] - trade['timestamp'] < 300):  # 5 min
                    arbitrage_candidates += 1
                    break
        
        return arbitrage_candidates > len(trades) * 0.3  # >30% arbitrage style
    
    async def check_first_block_entry(self, wallet):
        """Check if wallet consistently enters tokens in first block"""
        trades = await self.get_trade_history(wallet, days=30)
        
        first_block_entries = 0
        
        for trade in trades:
            if trade['type'] != 'BUY':
                continue
                
            token = trade['token']
            launch_time = await self.get_token_launch_time(token)
            
            if launch_time:
                seconds_from_launch = trade['timestamp'] - launch_time
                if seconds_from_launch < 30:  # Within 30 seconds
                    first_block_entries += 1
        
        total_buys = sum(1 for t in trades if t['type'] == 'BUY')
        if total_buys == 0:
            return False
            
        return first_block_entries / total_buys > 0.5  # >50% first block
```

### 4.3 Ranking & Discovery Pipeline

```python
class WalletDiscoveryPipeline:
    """
    End-to-end pipeline for discovering and ranking alpha wallets
    """
    
    def __init__(self):
        self.scoring_engine = WalletScoringEngine()
        self.noise_filter = NoiseFilter()
        self.database = WalletDatabase()
        
    async def run_discovery_cycle(self):
        """
        Main discovery pipeline
        """
        # Stage 1: Candidate Collection
        candidates = await self.collect_candidates()
        print(f"Collected {len(candidates)} candidate wallets")
        
        # Stage 2: Noise Filtering
        filtered = await self.filter_noise(candidates)
        print(f"Filtered to {len(filtered)} non-bot wallets")
        
        # Stage 3: Scoring
        scored = await self.score_wallets(filtered)
        print(f"Scored {len(scored)} wallets")
        
        # Stage 4: Ranking
        ranked = self.rank_wallets(scored)
        
        # Stage 5: Storage
        await self.store_discovered_wallets(ranked)
        
        return ranked[:100]  # Top 100
    
    async def collect_candidates(self):
        """Collect wallet candidates from multiple sources"""
        all_candidates = set()
        
        # Source 1: Early buyers of recent successful tokens
        recent_successful_tokens = await self.get_recent_successful_tokens(
            min_roi=5,
            days_back=30
        )
        for token in recent_successful_tokens:
            early_buyers = await self.get_early_buyers(token, hours=48)
            all_candidates.update(early_buyers)
        
        # Source 2: Top holders of trending tokens
        trending_tokens = await self.get_trending_tokens()
        for token in trending_tokens:
            holders = await self.get_top_holders(token, limit=50)
            all_candidates.update(holders)
        
        # Source 3: Community mentions
        discord_wallets = await self.get_discord_mentioned_wallets()
        all_candidates.update(discord_wallets)
        
        # Source 4: Transaction graph analysis
        graph_wallets = await self.analyze_transaction_graph()
        all_candidates.update(graph_wallets)
        
        return list(all_candidates)
    
    async def filter_noise(self, candidates):
        """Filter out bots and market makers"""
        genuine_wallets = []
        
        for wallet in candidates:
            classification = await self.noise_filter.classify_wallet_type(wallet)
            
            if not classification['is_noise']:
                genuine_wallets.append({
                    'address': wallet,
                    'classification': classification
                })
        
        return genuine_wallets
    
    async def score_wallets(self, wallets):
        """Score all genuine wallets"""
        scored = []
        
        for wallet_info in wallets:
            wallet = wallet_info['address']
            score = await self.scoring_engine.calculate_wallet_score(wallet)
            
            scored.append({
                'address': wallet,
                'score': score,
                'classification': wallet_info['classification']
            })
        
        return scored
    
    def rank_wallets(self, scored_wallets):
        """Final ranking with tiebreakers"""
        
        def ranking_key(wallet):
            score = wallet['score']
            return (
                score['total_score'],                           # Primary: total score
                score['components']['stealth_factor'],          # Tiebreaker 1: stealth
                score['components']['early_detection'],         # Tiebreaker 2: early detection
                score['components']['consistency']              # Tiebreaker 3: consistency
            )
        
        ranked = sorted(scored_wallets, key=ranking_key, reverse=True)
        
        # Add rank
        for i, wallet in enumerate(ranked):
            wallet['rank'] = i + 1
            
        return ranked
```

---

## 5. INTEGRATION WITH SHADOWHUNTER

### 5.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SHADOWHUNTER ALPHA DISCOVERY                         │
│                           SYSTEM ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │  DATA SOURCES    │    │  PROCESSING      │    │  OUTPUT          │      │
│  │                  │    │                  │    │                  │      │
│  │ • Helius RPC     │───▶│ • Wallet Scorer  │───▶│ • Ranked Wallets │      │
│  │ • Jupiter API    │    │ • Noise Filter   │    │ • Real-time      │      │
│  │ • Birdeye        │    │ • Pattern Recog  │    │   Alerts         │      │
│  │ • Discord Bots   │    │ • Cluster Detect │    │ • Copy Trade     │      │
│  │ • Webhooks       │    │                  │    │   Signals        │      │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘      │
│           │                       │                       │                 │
│           ▼                       ▼                       ▼                 │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │                      DATABASE LAYER                               │      │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐  │      │
│  │  │ wallets     │  │ transactions│  │ scores      │  │ alerts  │  │      │
│  │  │ (profile)   │  │ (history)   │  │ (ranking)   │  │ (triggers)│      │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘  │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │                    MONITORING ENGINE                              │      │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │      │
│  │  │ Real-time    │  │ Alert        │  │ Copy Trade   │            │      │
│  │  │ WebSocket    │  │ Processor    │  │ Executor     │            │      │
│  │  │ Listener     │  │              │  │              │            │      │
│  │  └──────────────┘  └──────────────┘  └──────────────┘            │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Database Schema for Wallet Intelligence

```sql
-- Core wallet table
CREATE TABLE wallets (
    id SERIAL PRIMARY KEY,
    address VARCHAR(44) UNIQUE NOT NULL,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_updated TIMESTAMP DEFAULT NOW(),
    
    -- Classification
    wallet_type VARCHAR(50), -- 'genuine_trader', 'bot', 'market_maker', etc.
    classification_confidence DECIMAL(3,2),
    
    -- Performance metrics
    total_realized_pnl DECIMAL(18,2),
    total_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2),
    profit_factor DECIMAL(8,2),
    avg_roi DECIMAL(8,2),
    
    -- Activity metrics
    last_activity TIMESTAMP,
    avg_trade_frequency DECIMAL(4,2), -- trades per day
    avg_hold_time_hours DECIMAL(8,2),
    
    -- Scores
    alpha_score DECIMAL(5,2),
    stealth_score DECIMAL(5,2),
    consistency_score DECIMAL(5,2),
    
    -- Metadata
    tags TEXT[], -- e.g., ['early_buyer', 'high_concentration', 'micro_cap_specialist']
    source VARCHAR(50), -- how discovered
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Transaction history
CREATE TABLE wallet_transactions (
    id SERIAL PRIMARY KEY,
    wallet_id INTEGER REFERENCES wallets(id),
    signature VARCHAR(100) UNIQUE NOT NULL,
    
    transaction_type VARCHAR(20), -- 'BUY', 'SELL', 'TRANSFER'
    token_address VARCHAR(44),
    token_symbol VARCHAR(20),
    
    amount_token DECIMAL(24,8),
    amount_usd DECIMAL(18,2),
    price_usd DECIMAL(18,8),
    
    -- Entry/exit context
    market_cap_at_tx DECIMAL(18,2),
    token_age_hours DECIMAL(8,2),
    
    -- PnL (for sells)
    realized_pnl DECIMAL(18,2),
    roi_pct DECIMAL(8,2),
    
    timestamp TIMESTAMP NOT NULL,
    
    -- Raw data
    raw_data JSONB
);

-- Portfolio snapshots (for tracking concentration)
CREATE TABLE portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    wallet_id INTEGER REFERENCES wallets(id),
    snapshot_time TIMESTAMP DEFAULT NOW(),
    
    total_value_usd DECIMAL(18,2),
    num_positions INTEGER,
    concentration_score DECIMAL(5,2), -- HHI
    
    top_holdings JSONB, -- [{token, value_usd, allocation_pct}]
    
    -- Allocation breakdown
    micro_cap_pct DECIMAL(5,2),    -- <$100k
    small_cap_pct DECIMAL(5,2),    -- $100k-$1M
    mid_cap_pct DECIMAL(5,2),      -- $1M-$10M
    large_cap_pct DECIMAL(5,2)     -- >$10M
);

-- Scoring history (track score changes over time)
CREATE TABLE scoring_history (
    id SERIAL PRIMARY KEY,
    wallet_id INTEGER REFERENCES wallets(id),
    calculated_at TIMESTAMP DEFAULT NOW(),
    
    total_score DECIMAL(5,2),
    grade VARCHAR(2),
    
    component_scores JSONB, -- {profitability: 85, early_detection: 72, ...}
    
    confidence DECIMAL(3,2)
);

-- Alert configuration and history
CREATE TABLE alert_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    rule_type VARCHAR(50), -- 'wallet_activity', 'score_threshold', 'new_discovery'
    
    -- Conditions
    wallet_id INTEGER REFERENCES wallets(id), -- NULL = any wallet
    min_score DECIMAL(5,2),
    min_transaction_usd DECIMAL(18,2),
    token_age_max_hours DECIMAL(8,2),
    
    -- Notification settings
    webhook_url TEXT,
    discord_channel_id VARCHAR(50),
    telegram_chat_id VARCHAR(50),
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE alert_history (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER REFERENCES alert_rules(id),
    wallet_id INTEGER REFERENCES wallets(id),
    
    alert_type VARCHAR(50),
    alert_data JSONB,
    
    triggered_at TIMESTAMP DEFAULT NOW(),
    notified BOOLEAN DEFAULT FALSE
);

-- Copy trading configuration
CREATE TABLE copy_trade_settings (
    id SERIAL PRIMARY KEY,
    wallet_id INTEGER REFERENCES wallets(id),
    
    -- Source (the alpha wallet)
    source_wallet_address VARCHAR(44) NOT NULL,
    
    -- Copy parameters
    is_active BOOLEAN DEFAULT TRUE,
    copy_percentage DECIMAL(5,2), -- Copy X% of their position size
    max_position_usd DECIMAL(18,2),
    min_position_usd DECIMAL(18,2),
    
    -- Filters
    min_source_position_usd DECIMAL(18,2), -- Only copy if they buy >$X
    max_token_age_hours DECIMAL(8,2), -- Don't copy if token older than X
    blacklist_tokens TEXT[],
    
    -- Risk management
    stop_loss_pct DECIMAL(5,2),
    take_profit_pct DECIMAL(5,2),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_wallets_alpha_score ON wallets(alpha_score DESC);
CREATE INDEX idx_wallets_stealth_score ON wallets(stealth_score DESC);
CREATE INDEX idx_wallets_type ON wallets(wallet_type);
CREATE INDEX idx_transactions_wallet_time ON wallet_transactions(wallet_id, timestamp DESC);
CREATE INDEX idx_transactions_token ON wallet_transactions(token_address);
CREATE INDEX idx_portfolio_wallet_time ON portfolio_snapshots(wallet_id, snapshot_time DESC);

-- Materialized view for top wallets by category
CREATE MATERIALIZED VIEW top_alpha_wallets AS
SELECT 
    address,
    alpha_score,
    stealth_score,
    win_rate,
    total_realized_pnl,
    wallet_type,
    tags
FROM wallets
WHERE wallet_type = 'genuine_trader' 
  AND alpha_score >= 70
ORDER BY alpha_score DESC;
```

### 5.3 Real-Time Monitoring Implementation

```python
class ShadowHunterMonitor:
    """
    Real-time monitoring system for high-score wallets
    """
    
    def __init__(self, database, helius_api_key):
        self.db = database
        self.helius = HeliusClient(helius_api_key)
        self.alert_processor = AlertProcessor()
        
    async def start_monitoring(self):
        """Start real-time monitoring pipeline"""
        
        # Get wallets to monitor (top 1000 by score)
        monitored_wallets = await self.db.get_high_score_wallets(
            min_score=70,
            limit=1000
        )
        
        wallet_addresses = [w['address'] for w in monitored_wallets]
        
        # Subscribe to WebSocket stream
        await self.helius.subscribe_addresses(
            wallet_addresses,
            callback=self.handle_transaction,
            commitment='confirmed'
        )
        
    async def handle_transaction(self, transaction):
        """Process incoming transaction from monitored wallet"""
        
        wallet = transaction['account']
        
        # Parse transaction
        parsed = self.parse_transaction(transaction)
        
        # Check if it's a token buy
        if parsed['type'] == 'BUY':
            await self.process_buy_signal(wallet, parsed)
        elif parsed['type'] == 'SELL':
            await self.process_sell_signal(wallet, parsed)
        
        # Update wallet stats
        await self.update_wallet_stats(wallet)
        
    async def process_buy_signal(self, wallet, transaction):
        """
        Process a buy signal from monitored wallet
        """
        token = transaction['token']
        
        # Get wallet info
        wallet_info = await self.db.get_wallet(wallet)
        
        # Calculate signal strength
        signal_strength = self.calculate_signal_strength(wallet_info, transaction)
        
        alert_data = {
            'wallet': wallet,
            'wallet_score': wallet_info['alpha_score'],
            'token': token,
            'token_symbol': transaction.get('token_symbol'),
            'amount_usd': transaction['amount_usd'],
            'market_cap_at_buy': transaction.get('market_cap'),
            'token_age_hours': transaction.get('token_age_hours'),
            'signal_strength': signal_strength,
            'timestamp': transaction['timestamp'],
            'transaction_signature': transaction['signature'],
            'stealth_factor': wallet_info['stealth_score']
        }
        
        # Store transaction
        await self.db.store_transaction(alert_data)
        
        # Trigger alerts if signal strong enough
        if signal_strength >= 7:  # Out of 10
            await self.alert_processor.send_alert('STRONG_BUY_SIGNAL', alert_data)
            
            # Check for copy trade settings
            copy_settings = await self.db.get_copy_trade_settings_for_source(wallet)
            for setting in copy_settings:
                await self.execute_copy_trade(setting, transaction)
        
        # Check for cluster signal (multiple wallets buying same token)
        await self.check_cluster_signal(token)
        
    def calculate_signal_strength(self, wallet_info, transaction):
        """
        Calculate signal strength 0-10
        """
        strength = 0
        
        # Base score from wallet alpha score
        strength += (wallet_info['alpha_score'] / 100) * 3
        
        # Early entry bonus
        if transaction.get('token_age_hours', 100) < 1:
            strength += 3
        elif transaction.get('token_age_hours', 100) < 6:
            strength += 2
        elif transaction.get('token_age_hours', 100) < 24:
            strength += 1
        
        # Position size relative to portfolio
        position_pct = transaction['amount_usd'] / wallet_info.get('total_value_usd', 1)
        if position_pct > 0.5:
            strength += 2
        elif position_pct > 0.2:
            strength += 1
        
        # Stealth bonus
        strength += (wallet_info['stealth_score'] / 100) * 1
        
        return min(strength, 10)
    
    async def check_cluster_signal(self, token):
        """
        Detect when multiple high-score wallets buy same token
        """
        # Get all buys of this token in last 24h
        recent_buys = await self.db.get_token_buys(token, hours=24)
        
        # Filter to high-score wallets only
        high_score_buys = [
            b for b in recent_buys 
            if b['wallet_score'] >= 70
        ]
        
        if len(high_score_buys) >= 3:  # 3+ high-score wallets
            await self.alert_processor.send_alert('CLUSTER_BUY_SIGNAL', {
                'token': token,
                'num_wallets': len(high_score_buys),
                'avg_wallet_score': sum(b['wallet_score'] for b in high_score_buys) / len(high_score_buys),
                'total_volume_usd': sum(b['amount_usd'] for b in high_score_buys),
                'buys': high_score_buys
            })
```

### 5.4 Alert Trigger System

```python
class AlertProcessor:
    """
    Process and send alerts through multiple channels
    """
    
    ALERT_TEMPLATES = {
        'STRONG_BUY_SIGNAL': {
            'priority': 'HIGH',
            'channels': ['discord', 'telegram', 'webhook'],
            'template': '''
🚨 **HIGH ALPHA BUY SIGNAL**

👤 Wallet: `{wallet}`
⭐ Score: {wallet_score}/100 | Stealth: {stealth_factor}/100

🪙 Token: {token_symbol} (`{token}`)
💰 Amount: ${amount_usd:,.2f}
📊 Market Cap: ${market_cap_at_buy:,.0f}
⏱️ Token Age: {token_age_hours:.1f}h

📈 Signal Strength: {signal_strength}/10

[View Transaction](https://solscan.io/tx/{transaction_signature})
            '''
        },
        'CLUSTER_BUY_SIGNAL': {
            'priority': 'CRITICAL',
            'channels': ['discord', 'telegram', 'webhook'],
            'template': '''
🔥 **CLUSTER BUY ALERT - MULTIPLE ALPHA WALLETS**

🪙 Token: `{token}`
👥 Wallets Buying: {num_wallets}
⭐ Avg Wallet Score: {avg_wallet_score:.1f}
💰 Combined Volume: ${total_volume_usd:,.2f}

This many high-score wallets buying simultaneously is a strong signal!
            '''
        },
        'NEW_HIGH_SCORE_WALLET': {
            'priority': 'MEDIUM',
            'channels': ['discord'],
            'template': '''
✨ **New High-Score Wallet Discovered**

👤 Wallet: `{wallet}`
⭐ Alpha Score: {alpha_score}/100
📊 Win Rate: {win_rate:.1%}
💰 Total PnL: ${total_pnl:,.2f}

Added to monitoring list.
            '''
        }
    }
    
    async def send_alert(self, alert_type, data):
        """Send alert through configured channels"""
        
        template = self.ALERT_TEMPLATES.get(alert_type)
        if not template:
            return
        
        message = template['template'].format(**data)
        
        # Send to Discord
        if 'discord' in template['channels']:
            await self.send_discord_alert(message, template['priority'])
        
        # Send to Telegram
        if 'telegram' in template['channels']:
            await self.send_telegram_alert(message, template['priority'])
        
        # Send to webhook
        if 'webhook' in template['channels']:
            await self.send_webhook_alert({
                'type': alert_type,
                'priority': template['priority'],
                'data': data,
                'message': message
            })
    
    async def send_discord_alert(self, message, priority):
        """Send alert to Discord webhook"""
        import aiohttp
        
        webhook_url = os.getenv('DISCORD_ALERT_WEBHOOK')
        
        color = {
            'CRITICAL': 0xFF0000,
            'HIGH': 0xFFA500,
            'MEDIUM': 0xFFFF00,
            'LOW': 0x00FF00
        }.get(priority, 0x808080)
        
        payload = {
            'embeds': [{
                'description': message,
                'color': color,
                'timestamp': datetime.utcnow().isoformat()
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json=payload)
```

---

## 6. THE ULTIMATE ALPHA DISCOVERY TOOL

### 6.1 Feature Specification

The ultimate alpha discovery system would include:

| Module | Feature | Description |
|--------|---------|-------------|
| **Discovery** | Multi-source ingestion | Helius, Birdeye, Jupiter, Discord, Twitter, custom webhooks |
| | Graph analysis | Find connected wallets through transaction clustering |
| | Dev tracking | Testnet → mainnet migration detection |
| **Scoring** | ML-enhanced scoring | Neural network for wallet success prediction |
| | Dynamic weights | Adjust scoring based on market conditions |
| | Backtesting | Test scoring against historical data |
| **Monitoring** | Sub-second latency | ShredStream integration for real-time detection |
| | Multi-wallet clusters | Detect coordinated buying patterns |
| | Insider detection | Flag dev/team wallet activity |
| **Execution** | Copy trading | Automatic position mirroring |
| | Smart sizing | Dynamic position sizing based on confidence |
| | Risk controls | Stop losses, exposure limits, blacklists |

### 6.2 API Integration Reference

```python
# Helius API - Primary data source
HELIUS_ENDPOINTS = {
    'wallet_history': 'https://api.helius.xyz/v0/addresses/{address}/transactions',
    'token_holders': 'https://api.helius.xyz/v0/token-holders',
    'enhanced_transactions': 'https://api.helius.xyz/v0/transactions',
    'webhooks': 'https://api.helius.xyz/v0/webhooks',
}

# Jupiter API - Price and swap data
JUPITER_ENDPOINTS = {
    'price': 'https://api.jup.ag/price/v2',
    'swap_quote': 'https://quote-api.jup.ag/v6/quote',
    'swap_instruction': 'https://quote-api.jup.ag/v6/swap-instruction',
}

# Birdeye API - Token analytics
BIRDEYE_ENDPOINTS = {
    'token_overview': 'https://public-api.birdeye.so/public/token/{address}',
    'wallet_portfolio': 'https://public-api.birdeye.so/v1/wallet/portfolio',
    'wallet_history': 'https://public-api.birdeye.so/v1/wallet/transaction_history',
}
```

### 6.3 Implementation Roadmap

**Phase 1: Foundation (Weeks 1-2)**
- Set up Helius integration
- Build wallet scoring engine v1
- Create basic database schema
- Implement noise filtering

**Phase 2: Discovery (Weeks 3-4)**
- Implement reverse engineering pipeline
- Build community intel gathering
- Create dev wallet tracking
- Deploy scoring system

**Phase 3: Monitoring (Weeks 5-6)**
- Real-time WebSocket monitoring
- Alert system implementation
- Copy trading foundation
- Dashboard creation

**Phase 4: Optimization (Weeks 7-8)**
- ML-enhanced scoring
- Performance optimization
- Advanced clustering detection
- Risk management features

---

## 7. KEY TAKEAWAYS

### High-Value Discovery Methods

1. **Reverse Engineering**: Start with successful tokens, find who bought in first 24-48 hours
2. **Testnet Tracking**: Follow dev activity from devnet to mainnet
3. **Community Intel**: Discord alpha groups contain high-signal wallet mentions
4. **Transaction Graphs**: Cluster analysis reveals coordinated wallet groups

### Scoring Priorities

| Factor | Weight | Why |
|--------|--------|-----|
| Early Detection Rate | 20% | Catches future winners |
| Profitability | 25% | Proven track record |
| Stealth Factor | 15% | Less competition |
| Consistency | 15% | Sustainable edge |
| Risk Management | 10% | Capital preservation |

### Red Flags to Filter

- First-block entry on every token (sniper bot)
- Same-block buy/sell pairs (arbitrage)
- Circular trades (wash trading)
- Perfect round amounts (automation)
- No hold time (MEV bot)

---

*This research provides the foundation for building the most advanced wallet hunting system on Solana.*
