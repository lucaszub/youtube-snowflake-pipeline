"""
Extraction des données Binance en temps réel
"""
import requests
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any
import time
import json


class BinanceExtractor:
    """
    Extracteur de données Binance via l'API publique REST

    Endpoints utilisés:
    - /api/v3/ticker/24hr : Prix, variation 24h, volume, high/low
    - /api/v3/depth : Order book (bid/ask pour spread)
    - /api/v3/trades : Trades récents
    """

    BASE_URL = "https://api.binance.com"

    def __init__(self, symbols: List[str] = None):
        """
        Args:
            symbols: Liste des paires de trading (ex: ["BTCUSDT", "ETHUSDT"])
                    Par défaut: BTC, ETH, BNB vs USDT
        """
        self.symbols = symbols or ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

    def get_24h_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Récupère les statistiques 24h pour un symbole

        Returns:
            Dict avec: symbol, price, priceChange, priceChangePercent,
                      volume, high, low, etc.
        """
        endpoint = f"{self.BASE_URL}/api/v3/ticker/24hr"
        params = {"symbol": symbol}

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            print("test lukus :", json.dumps(data, indent=2))
            return data
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching 24h ticker for {symbol}: {e}")
            return {}

    def get_order_book(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """
        Récupère le carnet d'ordres (order book)

        Args:
            symbol: Paire de trading
            limit: Nombre de niveaux à récupérer (default: 5 pour avoir best bid/ask)

        Returns:
            Dict avec: bids (liste [[prix, quantité]]), asks (liste [[prix, quantité]])
        """
        endpoint = f"{self.BASE_URL}/api/v3/depth"
        params = {"symbol": symbol, "limit": limit}

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extraire best bid/ask
            best_bid = float(data['bids'][0][0]) if data['bids'] else 0
            best_ask = float(data['asks'][0][0]) if data['asks'] else 0
            spread = best_ask - best_bid if (best_bid and best_ask) else 0
            spread_percent = (spread / best_bid * 100) if best_bid else 0

            return {
                'best_bid': best_bid,
                'best_ask': best_ask,
                'spread': spread,
                'spread_percent': spread_percent,
                'bid_quantity': float(data['bids'][0][1]) if data['bids'] else 0,
                'ask_quantity': float(data['asks'][0][1]) if data['asks'] else 0
            }
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching order book for {symbol}: {e}")
            return {}

    def get_recent_trades(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Récupère les trades récents

        Args:
            symbol: Paire de trading
            limit: Nombre de trades à récupérer (default: 10)

        Returns:
            Liste de trades avec: id, price, qty, time, isBuyerMaker
        """
        endpoint = f"{self.BASE_URL}/api/v3/trades"
        params = {"symbol": symbol, "limit": limit}

        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching recent trades for {symbol}: {e}")
            return []

    def extract_all_data(self) -> pd.DataFrame:
        """
        Extrait toutes les données pour tous les symboles configurés

        Returns:
            DataFrame avec toutes les métriques consolidées
        """
        all_data = []
        timestamp = datetime.now()

        print(f"\n🔄 Extracting Binance data for {len(self.symbols)} symbols...")
        print("=" * 80)

        for symbol in self.symbols:
            print(f"\n📊 Processing {symbol}...")

            # 1. Ticker 24h
            ticker = self.get_24h_ticker(symbol)
            if not ticker:
                continue

            # 2. Order Book (bid/ask)
            order_book = self.get_order_book(symbol)

            # 3. Recent Trades
            recent_trades = self.get_recent_trades(symbol, limit=5)

            # Calculer le prix moyen des 5 derniers trades
            avg_recent_price = 0
            total_volume = 0
            if recent_trades:
                avg_recent_price = sum(float(t['price']) for t in recent_trades) / len(recent_trades)
                total_volume = sum(float(t['qty']) for t in recent_trades)

            # Consolider les données
            data = {
                'symbol': symbol,
                'timestamp': timestamp.isoformat(),
                'unix_timestamp': int(timestamp.timestamp() * 1000),

                # Prix
                'last_price': float(ticker.get('lastPrice', 0)),
                'price_change_24h': float(ticker.get('priceChange', 0)),
                'price_change_percent_24h': float(ticker.get('priceChangePercent', 0)),

                # High/Low
                'high_24h': float(ticker.get('highPrice', 0)),
                'low_24h': float(ticker.get('lowPrice', 0)),
                'open_price': float(ticker.get('openPrice', 0)),

                # Volume
                'volume_24h': float(ticker.get('volume', 0)),
                'quote_volume_24h': float(ticker.get('quoteVolume', 0)),
                'weighted_avg_price': float(ticker.get('weightedAvgPrice', 0)),

                # Order Book (Spread)
                'best_bid': order_book.get('best_bid', 0),
                'best_ask': order_book.get('best_ask', 0),
                'spread': order_book.get('spread', 0),
                'spread_percent': order_book.get('spread_percent', 0),
                'bid_quantity': order_book.get('bid_quantity', 0),
                'ask_quantity': order_book.get('ask_quantity', 0),

                # Recent Trades
                'avg_recent_trade_price': avg_recent_price,
                'recent_trades_volume': total_volume,
                'trade_count_24h': int(ticker.get('count', 0))
            }

            all_data.append(data)

            # Affichage formaté
            print(f"  💰 Price: ${data['last_price']:,.2f} ({data['price_change_percent_24h']:+.2f}%)")
            print(f"  📈 24h High: ${data['high_24h']:,.2f} | Low: ${data['low_24h']:,.2f}")
            print(f"  📊 Volume: {data['volume_24h']:,.2f} {symbol[:3]} (${data['quote_volume_24h']:,.0f})")
            print(f"  💱 Spread: ${data['spread']:.2f} ({data['spread_percent']:.3f}%)")
            print(f"  🔄 Recent trades avg: ${data['avg_recent_trade_price']:,.2f}")

            # Rate limiting (éviter de surcharger l'API)
            time.sleep(0.2)

        if not all_data:
            raise Exception("No data extracted from Binance API")

        df = pd.DataFrame(all_data)

        print("\n" + "=" * 80)
        print(f"✅ Successfully extracted data for {len(df)} symbols")
        print(f"📅 Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        return df


def get_binance_data(symbols: List[str] = None) -> pd.DataFrame:
    """
    Fonction principale pour extraire les données Binance

    Args:
        symbols: Liste des paires à tracker (default: ["BTCUSDT", "ETHUSDT", "BNBUSDT"])

    Returns:
        DataFrame avec toutes les métriques
    """
    extractor = BinanceExtractor(symbols)
    return extractor.extract_all_data()


if __name__ == "__main__":
    # Test direct
    print("🚀 Testing Binance Extractor...")
    df = get_binance_data()

    print("\n📋 DataFrame Info:")
    print(df.info())

    print("\n📊 Sample Data:")
    print(df[['symbol', 'timestamp', 'unix_timestamp','last_price', 'price_change_percent_24h', 'volume_24h', 'spread_percent']].to_string())
