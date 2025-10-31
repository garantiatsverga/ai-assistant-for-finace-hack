"""Анализатор акций и инвестиционных рекомендаций"""
import logging
from typing import Dict, List, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class StockAnalyzer:
    """Анализатор акций для генерации рекомендаций"""
    
    def __init__(self):
        self.stock_profiles = {
            'SBER': {
                'name': 'Сбербанк',
                'sector': 'Финансы',
                'risk': 'Низкий',
                'potential': 'Умеренный',
                'dividend_yield': '8-12%',
                'description': 'Крупнейший банк России, стабильные дивиденды, подходит для консервативных инвесторов'
            },
            'GAZP': {
                'name': 'Газпром', 
                'sector': 'Энергетика',
                'risk': 'Средний',
                'potential': 'Умеренный',
                'dividend_yield': '10-15%',
                'description': 'Газовая монополия, высокие дивиденды, волатильность зависит от цен на газ'
            },
            'LKOH': {
                'name': 'Лукойл',
                'sector': 'Нефть',
                'risk': 'Средний',
                'potential': 'Умеренный', 
                'dividend_yield': '7-10%',
                'description': 'Нефтяная компания, стабильные выплаты, зависит от цен на нефть'
            },
            'ROSN': {
                'name': 'Роснефть',
                'sector': 'Нефть',
                'risk': 'Средний',
                'potential': 'Умеренный',
                'dividend_yield': '6-9%',
                'description': 'Государственная нефтяная компания, стратегический актив'
            },
            'VTBR': {
                'name': 'ВТБ',
                'sector': 'Финансы',
                'risk': 'Высокий',
                'potential': 'Высокий',
                'dividend_yield': '5-8%',
                'description': 'Второй по величине банк, высокая волатильность, потенциал роста'
            },
            'YNDX': {
                'name': 'Яндекс',
                'sector': 'Технологии',
                'risk': 'Высокий',
                'potential': 'Высокий',
                'dividend_yield': '0-2%',
                'description': 'Технологическая компания, высокий риск и потенциал роста'
            },
            'TCSG': {
                'name': 'Тинькофф',
                'sector': 'Финтех',
                'risk': 'Высокий', 
                'potential': 'Высокий',
                'dividend_yield': '3-5%',
                'description': 'Финтех компания, ориентирована на цифровые услуги, высокая волатильность'
            }
        }
        
        self.investment_strategies = {
            'conservative': {
                'name': 'Консервативная',
                'description': 'Сохранение капитала, низкий риск',
                'stocks': ['SBER', 'GAZP'],
                'allocation': '60-70% портфеля'
            },
            'dividend': {
                'name': 'Дивидендная', 
                'description': 'Регулярный доход, стабильные выплаты',
                'stocks': ['GAZP', 'SBER', 'LKOH'],
                'allocation': '40-60% портфеля'
            },
            'growth': {
                'name': 'Роста',
                'description': 'Потенциал роста, высокий риск',
                'stocks': ['YNDX', 'TCSG', 'VTBR'],
                'allocation': '20-40% портфеля'
            },
            'balanced': {
                'name': 'Сбалансированная',
                'description': 'Баланс роста и дохода',
                'stocks': ['SBER', 'GAZP', 'YNDX'],
                'allocation': 'Равное распределение'
            }
        }

    async def analyze_investment_query(self, question: str, market_data: Dict) -> Dict[str, Any]:
        """Анализ инвестиционного запроса и генерация рекомендаций"""
        question_lower = question.lower()
        
        # Определяем тип запроса
        if any(word in question_lower for word in ['консерватив', 'сохран', 'надежн']):
            strategy_type = 'conservative'
        elif any(word in question_lower for word in ['дивидент', 'доход', 'выплат']):
            strategy_type = 'dividend' 
        elif any(word in question_lower for word in ['агрессив', 'рост', 'потенциал']):
            strategy_type = 'growth'
        elif any(word in question_lower for word in ['начать', 'начал', 'новычок']):
            strategy_type = 'balanced'
        else:
            strategy_type = 'balanced'
        
        return await self._generate_strategy_recommendation(strategy_type, market_data)

    async def analyze_single_stock(self, symbol: str, market_data: Dict) -> Dict[str, Any]:
        """Анализ конкретной акции"""
        if symbol not in market_data:
            return {'error': f'Нет данных по акции {symbol}'}
        
        data = market_data[symbol]
        profile = self.stock_profiles.get(symbol, {})
        
        # Анализ динамики
        change = data.get('change', 0)
        change_percent = data.get('change_percent', 0)
        
        # Формируем рекомендацию
        if change > 0:
            trend = "восходящий"
            recommendation = "Возможность для покупки на коррекциях"
            sentiment = "positive"
        elif change < 0:
            trend = "нисходящий" 
            recommendation = "Возможность для покупки при стабилизации"
            sentiment = "cautious"
        else:
            trend = "боковой"
            recommendation = "Мониторить ценовые уровни"
            sentiment = "neutral"
        
        return {
            'symbol': symbol,
            'name': profile.get('name', symbol),
            'current_price': data.get('last_price'),
            'change': change,
            'change_percent': change_percent,
            'trend': trend,
            'sector': profile.get('sector'),
            'risk': profile.get('risk'),
            'potential': profile.get('potential'),
            'dividend_yield': profile.get('dividend_yield'),
            'recommendation': recommendation,
            'sentiment': sentiment,
            'description': profile.get('description')
        }

    async def _generate_strategy(self, strategy_type: str, market_data: Dict) -> Dict[str, Any]:
        """Генерация рекомендаций по стратегии"""
        strategy = self.investment_strategies[strategy_type]
        stocks = []
        
        for symbol in strategy['stocks']:
            if symbol in market_data:
                data = market_data[symbol]
                profile = self.stock_profiles.get(symbol, {})
                stocks.append({
                    'symbol': symbol, 
                    'name': profile.get('name', symbol),
                    'price': data.get('last_price'), 
                    'risk': profile.get('risk'),
                    'dividend_yield': profile.get('dividend_yield'),
                    'description': profile.get('description', '')
                })
        
        return {
            'strategy_name': strategy['name'],
            'strategy_description': strategy['description'],
            'recommended_allocation': strategy['allocation'],
            'stocks': stocks
        }

    def get_available_strategies(self) -> Dict[str, Any]:
        """Получение информации о доступных стратегиях"""
        return self.investment_strategies.copy()