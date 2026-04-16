"""
ShadowHunter Alpha Wallet Discovery System
Implementation Module

This module provides the core components for discovering and monitoring
high-alpha Solana wallets.
"""

import asyncio
import aiohttp
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import json
from decimal import Decimal

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class Config:
    """System configuration"""
    HELIUS_API_KEY: str = ""
    BIRDEYE_API_KEY: str = ""
    DISCORD_WEBHOOK: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    
    # Scoring thresholds
    MIN_ALPHA_SCORE: float = 70.0
    MIN_STEALTH_SCORE: float = 50.0
    
    # Monitoring settings
    MONITORED_WALLET_LIMIT: int = 1000
    WEBSOCKET_COMMITMENT: str = "confirmed"
    
    # Alert thresholds
    STRONG_SIGNAL_THRESHOLD: float = 7.0  # Out of 10
    CLUSTER_MIN_WALLETS: int = 3
    
    # Copy trading
    DEFAULT_COPY_PERCENTAGE: float = 10.0
    MAX_COPY_POSITION_USD: float = 5000.0


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class WalletScore:
    """Comprehensive wallet scoring result"""
    total_score: float
    components: Dict[str, float]
    grade: str
    confidence: float
    recommendation: str

@dataclass
class Transaction:
    """Parsed transaction data"""
    signature: str
    wallet: str
    type: str  # 'BUY', 'SELL', 'TRANSFER'
    token: str
    token_symbol: str
    amount_token: Decimal
    amount_usd: Decimal
    price_usd: Decimal
    market_cap: Optional[Decimal]
    token_age_hours: Optional[float]
    timestamp: datetime
    raw_data: Dict

@dataclass
class Alert:
    """Alert data structure"""
    alert_type: str
    priority: str
    wallet: str
    data: Dict
    timestamp: datetime


# ============================================================================
# HELIUS API CLIENT
# ============================================================================

class HeliusClient:
    """Helius API client for Solana data"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.helius.xyz/v0"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def get_wallet_history(
        self, 
        address: str, 
        days_back: int = 90,
        transaction_types: List[str] = None
    ) -> List[Dict]:
        """
        Fetch complete transaction history for a wallet
        
        Args:
            address: Wallet address
            days_back: How many days of history to fetch
            transaction_types: Filter by types (SWAP, TRANSFER, etc.)
        
        Returns:
            List of transaction dictionaries
        """
        url = f"{self.base_url}/addresses/{address}/transactions"
        params = {
            "api-key": self.api_key,
            "limit": 100
        }
        
        if transaction_types:
            params["type"] = "|".join(transaction_types)
        
        all_transactions = []
        before = None
        cutoff_time = datetime.now() - timedelta(days=days_back)
        
        while True:
            if before:
                params["before"] = before
            
            async with self.session.get(url, params=params) as resp:
                data = await resp.json()
                
                if not data:
                    break
                
                transactions = data if isinstance(data, list) else data.get('transactions', [])
                
                if not transactions:
                    break
                
                # Check if we've gone back far enough
                oldest_tx = transactions[-1]
                tx_time = datetime.fromtimestamp(oldest_tx.get('timestamp', 0))
                
                if tx_time < cutoff_time:
                    # Filter to only include transactions after cutoff
                    transactions = [
                        t for t in transactions 
                        if datetime.fromtimestamp(t.get('timestamp', 0)) >= cutoff_time
                    ]
                    all_transactions.extend(transactions)
                    break
                
                all_transactions.extend(transactions)
                before = oldest_tx.get('signature')
        
        return all_transactions
    
    async def get_token_holders(
        self, 
        token_address: str, 
        limit: int = 100
    ) -> List[Dict]:
        """Get top holders of a token"""
        url = f"{self.base_url}/token-holders"
        params = {
            "api-key": self.api_key,
            "mintAddress": token_address,
            "limit": limit
        }
        
        async with self.session.get(url, params=params) as resp:
            return await resp.json()
    
    async def get_enhanced_transactions(
        self, 
        signatures: List[str]
    ) -> List[Dict]:
        """Get enhanced transaction details"""
        url = f"{self.base_url}/transactions"
        params = {"api-key": self.api_key}
        
        payload = {"transactions": signatures}
        
        async with self.session.post(url, params=params, json=payload) as resp:
            return await resp.json()
    
    async def create_webhook(
        self, 
        webhook_url: str, 
        addresses: List[str],
        account_addresses: List[str] = None,
        transaction_types: List[str] = None,
        webhook_type: str = "enhanced"
    ) -> Dict:
        """Create a Helius webhook for real-time monitoring"""
        url = f"{self.base_url}/webhooks"
        params = {"api-key": self.api_key}
        
        payload = {
            "webhookURL": webhook_url,
            "accountAddresses": account_addresses or addresses,
            "webhookType": webhook_type,
            "authHeader": "shadowhunter-webhook-auth"
        }
        
        if transaction_types:
            payload["transactionTypes"] = transaction_types
        
        async with self.session.post(url, params=params, json=payload) as resp:
            return await resp.json()


# ============================================================================
# WALLET SCORING ENGINE
# ============================================================================

class WalletScoringEngine:
    """
    Comprehensive wallet scoring for alpha discovery
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
    
    def __init__(self, helius: HeliusClient):
        self.helius = helius
    
    async def calculate_score(self, wallet_address: str) -> WalletScore:
        """Calculate comprehensive alpha score for a wallet"""
        
        components = {}
        
        # Calculate each component
        components['profitability'] = await self._score_profitability(wallet_address)
        components['early_detection'] = await self._score_early_detection(wallet_address)
        components['consistency'] = await self._score_consistency(wallet_address)
        components['stealth_factor'] = await self._score_stealth(wallet_address)
        components['risk_management'] = await self._score_risk_management(wallet_address)
        components['activity_quality'] = await self._score_activity_quality(wallet_address)
        components['pattern_recognition'] = await self._score_patterns(wallet_address)
        
        # Calculate weighted total
        total_score = sum(
            components[k] * self.WEIGHTS[k] 
            for k in components
        )
        
        # Determine grade
        grade = self._score_to_grade(total_score)
        
        # Calculate confidence
        confidence = self._calculate_confidence(components)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(total_score, components)
        
        return WalletScore(
            total_score=round(total_score, 2),
            components=components,
            grade=grade,
            confidence=confidence,
            recommendation=recommendation
        )
    
    async def _score_profitability(self, wallet: str) -> float:
        """Score based on realized profits and win rate"""
        trades = await self.helius.get_wallet_history(wallet, days=90)
        
        if len(trades) < 5:
            return 50.0  # Neutral for new wallets
        
        # Calculate basic metrics
        total_pnl = sum(
            Decimal(str(t.get('nativeBalanceChange', 0))) 
            for t in trades
        )
        
        # Estimate win rate from balance changes
        positive_trades = sum(
            1 for t in trades 
            if t.get('nativeBalanceChange', 0) > 0
        )
        win_rate = positive_trades / len(trades)
        
        # Score components
        win_rate_score = min(win_rate * 100, 100)
        
        # Normalize PnL score (assume $10k profit = 100 score)
        pnl_score = min(float(total_pnl) / 10000 * 100, 100)
        
        return (win_rate_score * 0.6) + (pnl_score * 0.4)
    
    async def _score_early_detection(self, wallet: str) -> float:
        """Score based on early token entry"""
        # This would require token launch time analysis
        # Simplified implementation
        return 50.0  # Placeholder
    
    async def _score_consistency(self, wallet: str) -> float:
        """Score based on consistent performance over time"""
        trades = await self.helius.get_wallet_history(wallet, days=90)
        
        if len(trades) < 10:
            return 50.0
        
        # Group by week
        weekly_performance = {}
        for trade in trades:
            week = datetime.fromtimestamp(
                trade.get('timestamp', 0)
            ).isocalendar()[1]
            
            if week not in weekly_performance:
                weekly_performance[week] = []
            
            weekly_performance[week].append(
                trade.get('nativeBalanceChange', 0)
            )
        
        # Calculate weekly win rates
        weekly_wins = [
            1 if sum(week) > 0 else 0
            for week in weekly_performance.values()
        ]
        
        consistency = sum(weekly_wins) / len(weekly_wins) if weekly_wins else 0
        
        return consistency * 100
    
    async def _score_stealth(self, wallet: str) -> float:
        """
        Score how "stealth" (unknown) a wallet is
        Higher = less known = more valuable
        """
        score = 0
        
        # Check transaction count (newer wallets less known)
        trades = await self.helius.get_wallet_history(wallet, days=365)
        
        if len(trades) < 50:
            score += 30
        elif len(trades) < 200:
            score += 15
        
        # Check wallet age
        if trades:
            first_tx_time = datetime.fromtimestamp(
                min(t.get('timestamp', datetime.now().timestamp()) for t in trades)
            )
            age_days = (datetime.now() - first_tx_time).days
            
            if age_days > 365:
                score += 20
            elif age_days > 180:
                score += 15
            elif age_days > 90:
                score += 10
        
        # Check interaction diversity (diverse = more natural)
        programs = set()
        for trade in trades:
            for instruction in trade.get('instructions', []):
                programs.add(instruction.get('programId'))
        
        if len(programs) > 10:
            score += 25
        elif len(programs) > 5:
            score += 15
        
        return min(score, 100)
    
    async def _score_risk_management(self, wallet: str) -> float:
        """Score based on risk management practices"""
        trades = await self.helius.get_wallet_history(wallet, days=90)
        
        if len(trades) < 5:
            return 50.0
        
        # Calculate drawdowns
        balance_changes = [
            t.get('nativeBalanceChange', 0) for t in trades
        ]
        
        peak = 0
        max_drawdown = 0
        running_balance = 0
        
        for change in balance_changes:
            running_balance += change
            if running_balance > peak:
                peak = running_balance
            
            drawdown = peak - running_balance
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Score inversely to max drawdown
        if max_drawdown == 0:
            return 100.0
        
        # Assume $50k max drawdown = 0 score
        drawdown_score = max(0, 100 - (max_drawdown / 50000 * 100))
        
        return drawdown_score
    
    async def _score_activity_quality(self, wallet: str) -> float:
        """Score based on activity patterns"""
        trades = await self.helius.get_wallet_history(wallet, days=30)
        
        if not trades:
            return 0.0
        
        # Check for spam transactions
        spam_indicators = 0
        for trade in trades:
            # Small transfers often indicate spam
            if abs(trade.get('nativeBalanceChange', 0)) < 0.001:
                spam_indicators += 1
        
        spam_ratio = spam_indicators / len(trades)
        quality_score = (1 - spam_ratio) * 100
        
        return quality_score
    
    async def _score_patterns(self, wallet: str) -> float:
        """Score based on recognizable profitable patterns"""
        # Placeholder for pattern recognition ML model
        return 50.0
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade"""
        if score >= 90: return 'S'
        if score >= 80: return 'A'
        if score >= 70: return 'B'
        if score >= 60: return 'C'
        if score >= 50: return 'D'
        return 'F'
    
    def _calculate_confidence(self, components: Dict[str, float]) -> float:
        """Calculate confidence in the score"""
        # Higher variance in components = lower confidence
        values = list(components.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        
        # Normalize to 0-1
        confidence = 1 - min(variance / 1000, 1)
        return round(confidence, 2)
    
    def _generate_recommendation(
        self, 
        total_score: float, 
        components: Dict[str, float]
    ) -> str:
        """Generate human-readable recommendation"""
        if total_score >= 80:
            return "HIGH PRIORITY: Add to monitoring and consider copy trading"
        elif total_score >= 70:
            return "MEDIUM PRIORITY: Add to monitoring list"
        elif total_score >= 60:
            return "LOW PRIORITY: Track for potential improvement"
        else:
            return "SKIP: Does not meet alpha criteria"


# ============================================================================
# NOISE FILTER
# ============================================================================

class NoiseFilter:
    """
    Filter out market makers, arbitrageurs, and bots
    """
    
    async def classify_wallet(self, wallet: str, helius: HeliusClient) -> Dict:
        """
        Classify wallet type and determine if it's "noise"
        
        Returns:
            Dict with 'type', 'is_noise', and 'confidence'
        """
        trades = await helius.get_wallet_history(wallet, days=30)
        
        if len(trades) < 10:
            return {
                'type': 'UNKNOWN',
                'is_noise': False,
                'confidence': 0.5
            }
        
        scores = {
            'arbitrage': await self._check_arbitrage(trades),
            'market_maker': await self._check_market_maker(trades),
            'sniper': await self._check_sniper(trades),
            'genuine': 0
        }
        
        # Calculate genuine score
        scores['genuine'] = 1 - max(scores.values())
        
        # Determine type
        max_type = max(scores, key=scores.get)
        max_score = scores[max_type]
        
        return {
            'type': max_type.upper(),
            'is_noise': max_type != 'genuine' and max_score > 0.7,
            'confidence': max_score,
            'scores': scores
        }
    
    async def _check_arbitrage(self, trades: List[Dict]) -> float:
        """Check for arbitrage patterns"""
        # Look for rapid buy/sell of same token
        rapid_pairs = 0
        
        for i, trade in enumerate(trades[:-1]):
            next_trade = trades[i + 1]
            
            time_diff = (
                next_trade.get('timestamp', 0) - 
                trade.get('timestamp', 0)
            )
            
            # If within 60 seconds
            if time_diff < 60:
                rapid_pairs += 1
        
        return min(rapid_pairs / len(trades) * 3, 1.0)
    
    async def _check_market_maker(self, trades: List[Dict]) -> float:
        """Check for market maker patterns"""
        # Look for consistent two-sided activity
        buy_count = sum(
            1 for t in trades 
            if t.get('nativeBalanceChange', 0) < 0
        )
        sell_count = sum(
            1 for t in trades 
            if t.get('nativeBalanceChange', 0) > 0
        )
        
        if buy_count == 0 or sell_count == 0:
            return 0.0
        
        # Market makers have balanced buy/sell
        ratio = min(buy_count, sell_count) / max(buy_count, sell_count)
        
        return ratio if ratio > 0.8 else 0.0
    
    async def _check_sniper(self, trades: List[Dict]) -> float:
        """Check for sniper bot patterns"""
        # Look for very high frequency
        if len(trades) < 20:
            return 0.0
        
        # Calculate trades per day
        time_span = (
            max(t.get('timestamp', 0) for t in trades) -
            min(t.get('timestamp', 0) for t in trades)
        ) / 86400  # Convert to days
        
        if time_span == 0:
            return 0.0
        
        trades_per_day = len(trades) / time_span
        
        # More than 100 trades per day suggests bot
        return min(trades_per_day / 200, 1.0)


# ============================================================================
# DISCOVERY PIPELINE
# ============================================================================

class DiscoveryPipeline:
    """
    End-to-end pipeline for discovering alpha wallets
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.helius = None
        self.scorer = None
        self.filter = NoiseFilter()
    
    async def __aenter__(self):
        self.helius = HeliusClient(self.config.HELIUS_API_KEY)
        await self.helius.__aenter__()
        self.scorer = WalletScoringEngine(self.helius)
        return self
    
    async def __aexit__(self, *args):
        if self.helius:
            await self.helius.__aexit__(*args)
    
    async def discover_from_successful_tokens(
        self, 
        token_addresses: List[str],
        min_roi: float = 5.0,
        early_hours: int = 48
    ) -> List[Dict]:
        """
        Discover wallets by analyzing early buyers of successful tokens
        
        Args:
            token_addresses: List of successful token addresses
            min_roi: Minimum ROI to consider token successful
            early_hours: Consider buyers within this many hours of launch
        
        Returns:
            List of wallet data with scores
        """
        discovered = []
        
        for token in token_addresses:
            # Get early buyers
            holders = await self.helius.get_token_holders(token, limit=100)
            
            for holder in holders:
                wallet = holder.get('owner')
                
                if not wallet:
                    continue
                
                # Quick filter check
                classification = await self.filter.classify_wallet(
                    wallet, self.helius
                )
                
                if classification['is_noise']:
                    continue
                
                # Score the wallet
                score = await self.scorer.calculate_score(wallet)
                
                if score.total_score >= self.config.MIN_ALPHA_SCORE:
                    discovered.append({
                        'address': wallet,
                        'score': score,
                        'source_token': token,
                        'classification': classification
                    })
        
        # Sort by score
        discovered.sort(
            key=lambda x: x['score'].total_score, 
            reverse=True
        )
        
        return discovered
    
    async def discover_from_community(
        self, 
        wallet_mentions: List[Dict]
    ) -> List[Dict]:
        """
        Process wallets mentioned in community channels
        
        Args:
            wallet_mentions: List of {wallet, source, context} dicts
        
        Returns:
            List of scored wallet data
        """
        discovered = []
        
        for mention in wallet_mentions:
            wallet = mention['wallet']
            
            # Classify and score
            classification = await self.filter.classify_wallet(
                wallet, self.helius
            )
            
            if classification['is_noise']:
                continue
            
            score = await self.scorer.calculate_score(wallet)
            
            discovered.append({
                'address': wallet,
                'score': score,
                'source': mention.get('source'),
                'context': mention.get('context'),
                'classification': classification
            })
        
        return discovered


# ============================================================================
# ALERT SYSTEM
# ============================================================================

class AlertSystem:
    """
    Send alerts through multiple channels
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def send_buy_signal_alert(
        self,
        wallet: str,
        wallet_score: WalletScore,
        transaction: Dict,
        signal_strength: float
    ):
        """Send alert for strong buy signal"""
        
        message = f"""
🚨 **HIGH ALPHA BUY SIGNAL**

👤 Wallet: `{wallet[:8]}...{wallet[-8:]}`
⭐ Score: {wallet_score.total_score}/100 | Grade: {wallet_score.grade}
🕵️ Stealth: {wallet_score.components.get('stealth_factor', 0):.0f}/100

🪙 Token: `{transaction.get('token', 'Unknown')[:16]}...`
💰 Amount: ${transaction.get('amount_usd', 0):,.2f}
📊 Market Cap: ${transaction.get('market_cap', 0):,.0f}
⏱️ Token Age: {transaction.get('token_age_hours', 0):.1f}h

📈 Signal Strength: {signal_strength:.1f}/10

[View on Solscan](https://solscan.io/tx/{transaction.get('signature', '')})
        """
        
        await self._send_discord(message)
    
    async def send_cluster_alert(
        self,
        token: str,
        wallets: List[Dict],
        total_volume: float
    ):
        """Send alert for cluster buying"""
        
        avg_score = sum(w['score'] for w in wallets) / len(wallets)
        
        message = f"""
🔥 **CLUSTER BUY ALERT - MULTIPLE ALPHA WALLETS**

🪙 Token: `{token[:20]}...`
👥 Wallets Buying: {len(wallets)}
⭐ Avg Wallet Score: {avg_score:.1f}
💰 Combined Volume: ${total_volume:,.2f}

⚠️ This many high-score wallets buying simultaneously is a strong signal!
        """
        
        await self._send_discord(message, priority='CRITICAL')
    
    async def _send_discord(
        self, 
        message: str, 
        priority: str = 'HIGH'
    ):
        """Send alert to Discord webhook"""
        
        if not self.config.DISCORD_WEBHOOK:
            return
        
        colors = {
            'CRITICAL': 0xFF0000,
            'HIGH': 0xFFA500,
            'MEDIUM': 0xFFFF00,
            'LOW': 0x00FF00
        }
        
        payload = {
            'embeds': [{
                'description': message,
                'color': colors.get(priority, 0x808080),
                'timestamp': datetime.utcnow().isoformat()
            }]
        }
        
        async with self.session.post(
            self.config.DISCORD_WEBHOOK, 
            json=payload
        ) as resp:
            if resp.status != 204:
                print(f"Failed to send Discord alert: {resp.status}")


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def main():
    """
    Example usage of the alpha wallet discovery system
    """
    config = Config(
        HELIUS_API_KEY="your-helius-api-key",
        DISCORD_WEBHOOK="your-discord-webhook-url"
    )
    
    # Initialize pipeline
    async with DiscoveryPipeline(config) as pipeline:
        async with AlertSystem(config) as alerts:
            
            # Example: Discover from successful tokens
            successful_tokens = [
                # Add your successful token addresses here
                "So11111111111111111111111111111111111111112",  # Example
            ]
            
            print("Starting wallet discovery...")
            discovered = await pipeline.discover_from_successful_tokens(
                successful_tokens
            )
            
            print(f"\nDiscovered {len(discovered)} high-alpha wallets:")
            
            for wallet_data in discovered[:10]:
                wallet = wallet_data['address']
                score = wallet_data['score']
                
                print(f"\n{wallet[:16]}...")
                print(f"  Score: {score.total_score}/100 ({score.grade})")
                print(f"  Components: {score.components}")
                print(f"  Recommendation: {score.recommendation}")
                
                # Send alert for top wallets
                if score.total_score >= 80:
                    await alerts.send_buy_signal_alert(
                        wallet=wallet,
                        wallet_score=score,
                        transaction={'amount_usd': 1000},  # Example
                        signal_strength=8.5
                    )


if __name__ == "__main__":
    asyncio.run(main())
