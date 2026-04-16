#!/usr/bin/env python3
"""
Himmel - Solana Token Info Bot
/top command - Shows top 10 holders + shared holdings analysis
/cross command - Cross-wallet token analysis (3+ holders only)
"""

import os
import re
import asyncio
import aiohttp
import json
import time
import random
from typing import Optional, Dict, List, Set
from collections import defaultdict
# Fix SSL certificates on Windows
import ssl
import certifi

# Create SSL context with proper certificates
ssl_context = ssl.create_default_context(cafile=certifi.where())

# Set environment variables
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY', '')
BIRDEYE_API_KEY = os.getenv('BIRDEYE_API_KEY', '')
ALCHEMY_API_KEY = os.getenv('ALCHEMY_API_KEY', '')

SOLANA_ADDRESS = re.compile(r'[1-9A-HJ-NP-Za-km-z]{32,44}')

# RPC Priority: Alchemy primary (higher free tier), Helius fallback
HELIUS_RPC = "https://mainnet.helius-rpc.com"
ALCHEMY_RPC = "https://solana-mainnet.g.alchemy.com/v2"
PUBLIC_RPC = "https://api.mainnet-beta.solana.com"

def get_rpc_url(alchemy_key: str = '', helius_key: str = '') -> str:
    """Get RPC URL - Alchemy primary, Helius fallback, Public last resort"""
    if alchemy_key:
        return f"{ALCHEMY_RPC}/{alchemy_key}"
    elif helius_key:
        return f"{HELIUS_RPC}/?api-key={helius_key}"
    else:
        return PUBLIC_RPC

DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"
BIRDEYE_BASE = "https://public-api.birdeye.so"

EXCLUDED_SYMBOLS: Set[str] = {
    'SOL', 'USDC', 'USDT', 'USDG', 'BUSD', 'DAI', 'TUSD', 'USDD', 'USDP',
    'UST', 'FRAX', 'LUSD', 'GUSD', 'sUSD', 'mUSD', 'nUSD', 'USDN'
}

SOL_TOKEN_ADDRESS = "So11111111111111111111111111111111111111111"
MIN_HOLDING_VALUE_USD = 100
MIN_CROSS_HOLDERS = 3  # Only show tokens held by 3+ wallets
MIN_LIQUIDITY_USD = 1000  # Filter out low liquidity tokens
MAX_TELEGRAM_MESSAGE_LENGTH = 4000
LPOOLS_FILE = "lpools.txt"
EXCHANGES_FILE = "exchanges.txt"


def load_address_list(filepath: str) -> Set[str]:
    """Load a list of addresses from a text file."""
    addresses = set()

    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        addr = line.split()[0] if ' ' in line else line
                        if len(addr) >= 32:
                            addresses.add(addr)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    else:
        print(f"Warning: {filepath} not found.")

    return addresses


class HimmelBot:

    def __init__(self, token: str, helius_key: str = '', birdeye_key: str = '', alchemy_key: str = ''):
        self.token = token
        self.helius_key = helius_key
        self.birdeye_key = birdeye_key
        self.alchemy_key = alchemy_key
        self.session: Optional[aiohttp.ClientSession] = None
        self._wallet_cache: Dict[str, bool] = {}
        self._holdings_cache: Dict[str, Dict] = {}
        self._token_symbols_cache: Dict[str, str] = {}
        self.birdeye_semaphore = asyncio.Semaphore(3)
        self.birdeye_delay = 1.2
        self.helius_delay = 0.1

        self.known_lp_programs: Set[str] = load_address_list(LPOOLS_FILE)
        self.exchange_wallets: Set[str] = load_address_list(EXCHANGES_FILE)

    def get_rpc_url(self) -> str:
        """Get RPC URL for this instance - Alchemy primary, Helius fallback"""
        if self.alchemy_key:
            return f"{ALCHEMY_RPC}/{self.alchemy_key}"
        elif self.helius_key:
            return f"{HELIUS_RPC}/?api-key={self.helius_key}"
        else:
            return PUBLIC_RPC

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_with_backoff(self, url: str, headers: dict, params: dict, max_retries: int = 3):
        for attempt in range(max_retries):
            try:
                async with self.birdeye_semaphore:
                    if attempt > 0:
                        wait = (2 ** attempt) + random.uniform(0.5, 1.5)
                        await asyncio.sleep(wait)
                    else:
                        await asyncio.sleep(self.birdeye_delay)

                    resp = await self.session.get(url, params=params, headers=headers, timeout=15)
                    return resp

            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    continue
                raise
        return None

    async def get_wallet_holdings(self, wallet_address: str, exclude_token: str = "") -> Optional[Dict]:
        if not self.birdeye_key:
            return None

        cache_key = f"{wallet_address}_{exclude_token}"
        if cache_key in self._holdings_cache:
            cache_entry = self._holdings_cache[cache_key]
            if time.time() - cache_entry.get('timestamp', 0) < 300:
                return cache_entry.get('data')

        url = f"{BIRDEYE_BASE}/wallet/v2/net-worth-details"
        params = {"wallet": wallet_address}
        headers = {
            "X-API-KEY": self.birdeye_key,
            "Accept": "application/json"
        }

        try:
            resp = await self.fetch_with_backoff(url, headers, params)

            if not resp or resp.status != 200:
                return None

            text = await resp.text()
            data = json.loads(text)

            if not data.get('success'):
                return None

            response_data = data.get('data', {})
            net_worth = float(response_data.get('net_worth', 0) or 0)
            assets = response_data.get('net_assets', [])

            sol_balance = 0.0
            for asset in assets:
                if asset.get('token_address') == SOL_TOKEN_ADDRESS:
                    balance_str = asset.get('balance', '0')
                    decimals = int(asset.get('decimal', 9))
                    sol_balance = float(balance_str) / (10 ** decimals)
                    break

            filtered_assets = [
                asset for asset in assets
                if asset.get('symbol', '').strip().upper() not in EXCLUDED_SYMBOLS
                and asset.get('token_address') != SOL_TOKEN_ADDRESS
                and asset.get('token_address') != exclude_token
                and float(asset.get('value', 0) or 0) >= MIN_HOLDING_VALUE_USD
            ]

            sorted_assets = sorted(
                filtered_assets,
                key=lambda x: float(x.get('value', 0) or 0),
                reverse=True
            )

            top_3 = sorted_assets[:3]
            top_holdings = []
            all_holdings_symbols = []

            for asset in sorted_assets:
                symbol = asset.get('symbol', '???').strip()
                all_holdings_symbols.append(symbol)

            for asset in top_3:
                symbol = asset.get('symbol', '???').strip()
                value = float(asset.get('value', 0) or 0)
                top_holdings.append({'symbol': symbol, 'value': value})

            result = {
                'net_worth': net_worth,
                'sol_balance': sol_balance,
                'top_holdings': top_holdings,
                'all_holdings': all_holdings_symbols
            }

            self._holdings_cache[cache_key] = {
                'timestamp': time.time(),
                'data': result
            }

            return result

        except Exception:
            return None

    async def get_token_accounts_by_owner(self, wallet_address: str) -> List[Dict]:
        """Get all token accounts owned by a wallet using RPC (Alchemy or Helius)."""
        rpc_url = self.get_rpc_url()
        if not rpc_url or rpc_url == PUBLIC_RPC:
            print(f"Warning: No API key available for getTokenAccountsByOwner")
            return []

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address,
                {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                {"encoding": "jsonParsed"}
            ]
        }

        try:
            await asyncio.sleep(self.helius_delay)

            async with self.session.post(rpc_url, json=payload, timeout=15) as resp:
                if resp.status != 200:
                    return []

                data = await resp.json()

                if 'error' in data:
                    return []

                accounts = data.get('result', {}).get('value', [])
                tokens = []

                for acc in accounts:
                    parsed = acc.get('account', {}).get('data', {}).get('parsed', {})
                    info = parsed.get('info', {}) if isinstance(parsed, dict) else {}

                    mint = info.get('mint')
                    token_amount = info.get('tokenAmount', {})
                    amount = token_amount.get('amount', '0')
                    decimals = token_amount.get('decimals', 0)
                    ui_amount = token_amount.get('uiAmount', 0)

                    if int(amount) == 0:
                        continue

                    tokens.append({
                        'mint': mint,
                        'amount': amount,
                        'decimals': decimals,
                        'ui_amount': ui_amount
                    })

                return tokens

        except Exception:
            return []

    async def get_token_symbol(self, token_address: str) -> str:
        """Get token symbol from DexScreener or cache."""
        if token_address in self._token_symbols_cache:
            return self._token_symbols_cache[token_address]

        try:
            async with self.session.get(
                f"{DEXSCREENER_BASE}/tokens/{token_address}",
                timeout=5
            ) as resp:
                if resp.status != 200:
                    self._token_symbols_cache[token_address] = "???"
                    return "???"

                data = await resp.json()
                pairs = data.get('pairs', [])

                if pairs:
                    symbol = pairs[0].get('baseToken', {}).get('symbol', '???')
                    self._token_symbols_cache[token_address] = symbol
                    return symbol

                self._token_symbols_cache[token_address] = "???"
                return "???"

        except Exception:
            self._token_symbols_cache[token_address] = "???"
            return "???"

    async def get_token_liquidity(self, token_address: str) -> float:
        """Get token liquidity (USD) from DexScreener. Returns 0 if no data."""
        try:
            async with self.session.get(
                f"{DEXSCREENER_BASE}/tokens/{token_address}", 
                timeout=5
            ) as resp:
                if resp.status != 200:
                    return 0
                
                data = await resp.json()
                pairs = data.get('pairs', [])
                
                if not pairs:
                    return 0
                
                # Sum liquidity across all pairs
                total_liquidity = 0
                for pair in pairs:
                    liq = pair.get('liquidity', {}).get('usd', 0)
                    if liq:
                        total_liquidity += float(liq)
                
                return total_liquidity
                
        except Exception:
            return 0

    def is_exchange_wallet(self, wallet_address: str) -> bool:
        return wallet_address in self.exchange_wallets

    async def is_wallet_lp(self, wallet_address: str) -> bool:
        rpc_url = self.get_rpc_url()
        if not rpc_url or rpc_url == PUBLIC_RPC:
            return False

        if wallet_address in self._wallet_cache:
            return self._wallet_cache[wallet_address]

        if wallet_address in self.known_lp_programs:
            self._wallet_cache[wallet_address] = True
            return True

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [wallet_address, {"encoding": "jsonParsed"}]
        }

        try:
            async with self.session.post(rpc_url, json=payload, timeout=8) as resp:
                if resp.status != 200:
                    self._wallet_cache[wallet_address] = False
                    return False

                data = await resp.json()
                result = data.get('result', {}).get('value', {})

                if not result:
                    self._wallet_cache[wallet_address] = False
                    return False

                if result.get('owner') in self.known_lp_programs:
                    self._wallet_cache[wallet_address] = True
                    return True

                self._wallet_cache[wallet_address] = False
                return False

        except Exception:
            self._wallet_cache[wallet_address] = False
            return False

    async def get_token_supply(self, token_address: str) -> Optional[int]:
        rpc_url = self.get_rpc_url()
        if not rpc_url or rpc_url == PUBLIC_RPC:
            return None

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenSupply",
            "params": [token_address]
        }

        try:
            async with self.session.post(rpc_url, json=payload, timeout=10) as resp:
                data = await resp.json()
                return int(data.get('result', {}).get('value', {}).get('amount', 0))
        except Exception:
            return None

    async def get_top_holders(self, token_address: str, limit: int = 10) -> Optional[List[Dict]]:
        rpc_url = self.get_rpc_url()
        if not rpc_url or rpc_url == PUBLIC_RPC:
            return None

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenLargestAccounts",
            "params": [token_address]
        }

        try:
            async with self.session.post(rpc_url, json=payload, timeout=15) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()
                if 'error' in data:
                    return None

                token_accounts = data.get('result', {}).get('value', [])
                if not token_accounts:
                    return None

                total_supply = await self.get_token_supply(token_address)
                fetch_limit = min(len(token_accounts), limit + 5)
                potential_holders = []

                for acc in token_accounts[:fetch_limit]:
                    token_acc = acc.get('address')
                    amount_raw = int(acc.get('amount', 0))
                    decimals = int(acc.get('decimals', 9))

                    wallet_owner = await self.get_token_account_owner(token_acc)

                    if wallet_owner:
                        amount_ui = amount_raw / (10 ** decimals)
                        pct = (amount_raw / total_supply * 100) if total_supply else 0

                        potential_holders.append({
                            'address': wallet_owner,
                            'amount': amount_raw,
                            'ui_amount': amount_ui,
                            'percentage': pct,
                        })

                if not potential_holders:
                    return None

                holders = []

                for i, holder in enumerate(potential_holders):
                    is_lp = i < 3 and await self.is_wallet_lp(holder['address'])
                    is_exchange = self.is_exchange_wallet(holder['address'])

                    if is_lp or is_exchange:
                        continue

                    holder['rank'] = len(holders) + 1
                    holders.append(holder)

                    if len(holders) >= limit:
                        break

                return holders

        except Exception:
            return None

    async def get_token_account_owner(self, token_account: str) -> Optional[str]:
        rpc_url = self.get_rpc_url()
        if not rpc_url or rpc_url == PUBLIC_RPC:
            return None

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [token_account, {"encoding": "jsonParsed"}]
        }

        try:
            async with self.session.post(rpc_url, json=payload, timeout=8) as resp:
                if resp.status != 200:
                    return None

                data = await resp.json()
                result = data.get('result', {}).get('value', {})

                if not result:
                    return None

                if result.get('owner') in self.known_lp_programs:
                    return None

                data_field = result.get('data', [])
                parsed = None

                if isinstance(data_field, list) and len(data_field) > 0:
                    parsed = data_field[0] if isinstance(data_field[0], dict) else None
                elif isinstance(data_field, dict):
                    parsed = data_field.get('parsed')

                if isinstance(parsed, dict):
                    info = parsed.get('info', {})
                    if isinstance(info, dict):
                        return info.get('owner')

                return None

        except Exception:
            return None

    def format_amount(self, amt: float) -> str:
        if amt >= 1_000_000_000:
            return f"{amt/1_000_000_000:.2f}B"
        elif amt >= 1_000_000:
            return f"{amt/1_000_000:.2f}M"
        elif amt >= 1_000:
            return f"{amt/1_000:.1f}K"
        return f"{amt:,.2f}"

    def format_value(self, value: float) -> str:
        if value >= 1_000_000_000:
            return f"${value/1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"${value/1_000_000:.2f}M"
        elif value >= 1_000:
            return f"${value/1_000:.1f}K"
        return f"${value:.0f}"

    async def format_holder(self, holder: Dict, symbol: str, exclude_token: str = "",
                           shared_tokens: Dict[str, int] = None) -> str:
        addr = holder['address']
        pct = holder['percentage']
        amt = holder['ui_amount']

        emoji = "🔴" if pct >= 10 else "🟠" if pct >= 5 else "🟡" if pct >= 2 else "🟢"
        amt_str = self.format_amount(amt)

        result = f"{emoji}#{holder['rank']} `{addr}`\n{pct:.2f}% • {amt_str} ${symbol}"

        birdeye_data = await self.get_wallet_holdings(addr, exclude_token)

        if birdeye_data:
            net_worth = birdeye_data.get('net_worth', 0)
            sol_balance = birdeye_data.get('sol_balance', 0)
            holdings = birdeye_data.get('top_holdings', [])
            all_holdings = birdeye_data.get('all_holdings', [])

            result += f"\n   💰 {self.format_value(net_worth)} | ☀️ {sol_balance:.2f} SOL"

            if holdings:
                holdings_str = " | ".join([f"{h['symbol']} {self.format_value(h['value'])}" for h in holdings])
                result += f"\n   💼 {holdings_str}"

            if shared_tokens is not None:
                for token_symbol in all_holdings:
                    shared_tokens[token_symbol] = shared_tokens.get(token_symbol, 0) + 1
        else:
            result += "\n   💰 N/A"

        return result

    async def cmd_top(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("Usage: `/top <token_address>`", parse_mode='Markdown')
            return

        token_address = context.args[0]
        if not SOLANA_ADDRESS.match(token_address):
            await update.message.reply_text("Invalid Solana address")
            return

        loading = await update.message.reply_text("Loading...")

        info = await self.get_token_info(token_address)
        symbol = info['symbol'] if info else "???"

        holders = await self.get_top_holders(token_address, 10)

        if not holders:
            await loading.edit_text("Could not fetch holders")
            return

        shared_tokens: Dict[str, int] = {}

        total = sum(h['percentage'] for h in holders)

        text = f"🏆*{symbol}* Top Holders\n`{token_address}`\n\n"

        for h in holders:
            text += await self.format_holder(h, symbol, token_address, shared_tokens) + "\n\n"

        common_holdings = [(token, count) for token, count in shared_tokens.items() if count >= 2]
        common_holdings.sort(key=lambda x: x[1], reverse=True)

        if common_holdings:
            text += "📊 *Shared Holdings:*\n"
            for token, count in common_holdings[:5]:
                wallet_word = "wallets" if count > 1 else "wallet"
                text += f"• {token}: {count} {wallet_word}\n"
            text += "\n"

        text += f"Top {len(holders)}: {total:.1f}%"

        await loading.edit_text(text, parse_mode='Markdown')

    async def cmd_cross(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cross-analysis command: Finds tokens held by 3+ top holders."""
        if not context.args:
            await update.message.reply_text(
                "Usage: `/cross <token_address>`",
                parse_mode='Markdown'
            )
            return

        token_address = context.args[0]
        if not SOLANA_ADDRESS.match(token_address):
            await update.message.reply_text("Invalid Solana address")
            return

        loading = await update.message.reply_text("🔍 Analyzing...")

        # Get top 20 holders
        holders = await self.get_top_holders(token_address, 20)

        if not holders:
            await loading.edit_text("Could not fetch holders")
            return

        if len(holders) < MIN_CROSS_HOLDERS:
            await loading.edit_text(f"Need at least {MIN_CROSS_HOLDERS} holders for cross-analysis")
            return

        # Collect token holdings from all holders
        token_holders: Dict[str, List[str]] = defaultdict(list)

        for holder in holders:
            wallet = holder['address']

            tokens = await self.get_token_accounts_by_owner(wallet)

            for token in tokens:
                mint = token['mint']
                ui_amount = token['ui_amount']

                if mint == token_address:
                    continue

                if ui_amount < 1:
                    continue

                token_holders[mint].append(wallet)

        # Filter for 3+ holders, get symbols, check liquidity, exclude unnamed
        mutual_tokens = []

        for mint, wallets in token_holders.items():
            if len(wallets) >= MIN_CROSS_HOLDERS:
                symbol = await self.get_token_symbol(mint)

                if symbol == "???":
                    continue

                # Check liquidity via DexScreener
                liquidity = await self.get_token_liquidity(mint)
                if liquidity < MIN_LIQUIDITY_USD:
                    continue

                mutual_tokens.append((mint, symbol, wallets, liquidity))

        # Sort by holder count
        mutual_tokens.sort(key=lambda x: len(x[2]), reverse=True)

        if not mutual_tokens:
            await loading.edit_text("No mutual tokens found (all had <$1000 liquidity).")
            return

        # Build clean response - no headers, no summary
        info = await self.get_token_info(token_address)
        symbol = info['symbol'] if info else "???"

        text = f"🔗*{symbol}* Cross\n`{token_address}`\n\n"

        for mint, symbol, wallets, liquidity in mutual_tokens:
            # Format liquidity
            if liquidity >= 1_000_000:
                liq_str = f"${liquidity/1_000_000:.2f}M"
            elif liquidity >= 1_000:
                liq_str = f"${liquidity/1_000:.1f}K"
            else:
                liq_str = f"${liquidity:.0f}"

            entry = f"*{symbol}* ({liq_str} liq)\n"
            entry += f"`{mint}`\n"
            entry += f"({len(wallets)} holders)\n"

            # List all wallets
            for wallet in wallets:
                entry += f"`{wallet}`\n"

            entry += "\n"

            # Check length
            if len(text) + len(entry) > MAX_TELEGRAM_MESSAGE_LENGTH:
                # Send current and start new
                await loading.edit_text(text, parse_mode='Markdown')
                loading = await update.message.reply_text("...(continued)")
                text = entry
            else:
                text += entry

        # Send final part
        await loading.edit_text(text, parse_mode='Markdown')

    async def get_token_info(self, address: str) -> Optional[Dict]:
        try:
            async with self.session.get(f"{DEXSCREENER_BASE}/tokens/{address}", timeout=10) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                pairs = data.get('pairs', [])
                if not pairs:
                    return None
                p = pairs[0]
                return {'symbol': p.get('baseToken', {}).get('symbol', '???')}
        except:
            return None

    def run(self):
        # Show which RPC is being used
        rpc_url = self.get_rpc_url()
        rpc_name = "Alchemy" if self.alchemy_key else "Helius" if self.helius_key else "Public RPC (limited)"

        print("🌤️ Himmel Bot starting...")
        print(f"   RPC: {rpc_name}")
        print(f"   LP programs: {len(self.known_lp_programs)}")
        print(f"   Exchanges: {len(self.exchange_wallets)}")
        print(f"   Commands: /top, /cross\n")

        app = Application.builder().token(self.token).build()
        app.add_handler(CommandHandler("top", self.cmd_top))
        app.add_handler(CommandHandler("cross", self.cmd_cross))

        async def main():
            async with self:
                await app.initialize()
                await app.start()
                await app.updater.start_polling()
                print("Bot running!")
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    await app.stop()

        asyncio.run(main())


def main():
    if not TELEGRAM_BOT_TOKEN or (not HELIUS_API_KEY and not ALCHEMY_API_KEY):
        print("Missing TELEGRAM_BOT_TOKEN and at least one RPC key (HELIUS_API_KEY or ALCHEMY_API_KEY)")
        return

    HimmelBot(TELEGRAM_BOT_TOKEN, HELIUS_API_KEY, BIRDEYE_API_KEY, ALCHEMY_API_KEY).run()


if __name__ == "__main__":
    main()
