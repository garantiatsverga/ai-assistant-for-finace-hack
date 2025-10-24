# 🚀 ПРОДВИНУТАЯ RAG СИСТЕМА С AI-ФИЧАМИ

import re
import time
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
import json
from functools import lru_cache
import subprocess
import os

# ==================== 
# 1. MULTI-AGENT АРХИТЕКТУРА
# ====================
class SpecializedAgents:
    def __init__(self, base_rag):
        self.base_rag = base_rag
        self.agents = {
            'credit': self._create_credit_agent(),
            'cards': self._create_cards_agent(), 
            'deposit': self._create_deposit_agent(),
            'insurance': self._create_insurance_agent()
        }
    
    def _create_credit_agent(self):
        return {
            "system_prompt": "Ты - эксперт по кредитным продуктам. Дай развернутый ответ с расчетами.",
            "specialization": ["кредит", "ипотека", "заем", "ссуда"],
            "context_boost": 2  # Ищем больше документов по теме
        }
    
    def _create_cards_agent(self):
        return {
            "system_prompt": "Ты - специалист по карточным продуктам. Удели внимание кэшбэку и лимитам.",
            "specialization": ["карта", "кэшбэк", "лимит", "платеж"],
            "context_boost": 1
        }
    
    def _create_deposit_agent(self):
        return {
            "system_prompt": "Ты - консультант по вкладам. Рассчитай доходность и сроки.",
            "specialization": ["вклад", "депозит", "процент", "накопление"],
            "context_boost": 1
        }
    
    def _create_insurance_agent(self):
        return {
            "system_prompt": "Ты - страховой агент. Объясни условия и выплаты.",
            "specialization": ["страхование", "страховка", "каско", "осаго"],
            "context_boost": 1
        }
    
    def route_question(self, question: str) -> Dict:
        """Маршрутизация вопроса к специализированному агенту"""
        question_lower = question.lower()
        
        for agent_name, agent_config in self.agents.items():
            if any(keyword in question_lower for keyword in agent_config["specialization"]):
                return {
                    "agent": agent_name,
                    "config": agent_config,
                    "confidence": self._calculate_confidence(question_lower, agent_config)
                }
        
        return {"agent": "general", "config": None, "confidence": 1.0}
    
    def _calculate_confidence(self, question: str, agent_config: Dict) -> float:
        """Расчет уверенности в принадлежности к агенту"""
        matches = sum(1 for keyword in agent_config["specialization"] if keyword in question)
        return min(1.0, matches / len(agent_config["specialization"]))

# ==================== 
# 2. METRICS & QUALITY MONITORING
# ====================
class AdvancedMetrics:
    def __init__(self):
        self.metrics = {
            "response_times": [],
            "cache_performance": {"hits": 0, "misses": 0},
            "agent_usage": {},
            "quality_scores": [],
            "security_events": []
        }
    
    def log_response_time(self, start_time: float):
        time_taken = time.time() - start_time
        self.metrics["response_times"].append(time_taken)
    
    def log_cache_hit(self):
        self.metrics["cache_performance"]["hits"] += 1
    
    def log_cache_miss(self):
        self.metrics["cache_performance"]["misses"] += 1
    
    def log_agent_usage(self, agent_name: str):
        self.metrics["agent_usage"][agent_name] = self.metrics["agent_usage"].get(agent_name, 0) + 1
    
    def calculate_quality_score(self, question: str, answer: str, context: List) -> float:
        """Расчет комплексной оценки качества ответа"""
        scores = []
        
        # Оценка релевантности
        relevance_score = self._calculate_relevance(question, answer)
        scores.append(relevance_score)
        
        # Оценка полноты
        completeness_score = self._calculate_completeness(answer)
        scores.append(completeness_score)
        
        # Оценка использования контекста
        context_score = self._calculate_context_usage(answer, context)
        scores.append(context_score)
        
        return sum(scores) / len(scores)
    
    def _calculate_relevance(self, question: str, answer: str) -> float:
        """Оценка релевантности ответа вопросу"""
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        
        if not question_words:
            return 0.0
            
        overlap = len(question_words.intersection(answer_words))
        return overlap / len(question_words)
    
    def _calculate_completeness(self, answer: str) -> float:
        """Оценка полноты ответа"""
        ideal_length = 50  # Оптимальная длина ответа
        length = len(answer)
        
        if length < 10:
            return 0.1
        elif length > 500:
            return 0.7
        else:
            return min(1.0, length / ideal_length)
    
    def _calculate_context_usage(self, answer: str, context: List) -> float:
        """Оценка использования контекста"""
        if not context:
            return 0.0
            
        context_text = " ".join([doc.page_content for doc in context])
        context_words = set(context_text.lower().split())
        answer_words = set(answer.lower().split())
        
        if not context_words:
            return 0.0
            
        overlap = len(context_words.intersection(answer_words))
        return overlap / len(context_words)
    
    def generate_quality_report(self) -> str:
        """Генерация комплексного отчета"""
        avg_time = np.mean(self.metrics["response_times"]) if self.metrics["response_times"] else 0
        cache_hits = self.metrics["cache_performance"]["hits"]
        cache_misses = self.metrics["cache_performance"]["misses"]
        total_requests = cache_hits + cache_misses
        cache_hit_rate = cache_hits / total_requests if total_requests > 0 else 0
        
        quality_avg = np.mean(self.metrics["quality_scores"]) if self.metrics["quality_scores"] else 0
        
        report = f"""
📊 РАСШИРЕННЫЙ ОТЧЕТ О КАЧЕСТВЕ
{'='*50}
⏱️  Производительность:
   • Среднее время ответа: {avg_time:.2f} сек
   • Всего запросов: {total_requests}
   • Hit-rate кэша: {cache_hit_rate:.1%}

🎯  Качество ответов:
   • Средняя оценка качества: {quality_avg:.1%}
   • Кол-во оцененных ответов: {len(self.metrics['quality_scores'])}

🤖  Использование агентов:
"""
        for agent, count in self.metrics["agent_usage"].items():
            report += f"   • {agent}: {count} запросов\n"
            
        report += f"\n🔒  События безопасности: {len(self.metrics['security_events'])}"
        
        return report

# ==================== 
# 3. CONTEXT-AWARE PROMPT ENGINE
# ====================
class AdaptivePromptEngine:
    def __init__(self):
        self.conversation_history = []
        self.user_profile = {}
    
    def create_dynamic_prompt(self, question: str, context: List, agent_info: Dict = None) -> str:
        """Создание адаптивного промпта на основе контекста"""
        
        # Анализ сложности вопроса
        complexity = self._analyze_complexity(question)
        
        # Анализ тональности
        tone = self._analyze_tone(question)
        
        # Анализ срочности
        urgency = self._detect_urgency(question)
        
        base_template = self._select_base_template(complexity, tone, urgency)
        
        # Добавление специализации агента
        if agent_info and agent_info.get("agent") != "general":
            specialization = agent_info["config"]["system_prompt"]
            base_template = specialization + "\n\n" + base_template
        
        # Добавление истории контекста
        history_context = self._get_conversation_context()
        
        prompt = base_template.format(
            context="\n".join([doc.page_content for doc in context]),
            question=question,
            history=history_context,
            tone=self._get_tone_instruction(tone),
            urgency=self._get_urgency_instruction(urgency)
        )
        
        return prompt
    
    def _analyze_complexity(self, question: str) -> str:
        """Анализ сложности вопроса"""
        word_count = len(question.split())
        complex_indicators = ['расчет', 'сравнение', 'условия', 'требования']
        
        if word_count > 10 or any(indicator in question.lower() for indicator in complex_indicators):
            return "complex"
        return "simple"
    
    def _analyze_tone(self, question: str) -> str:
        """Анализ тональности вопроса"""
        positive_words = ['спасибо', 'помогите', 'пожалуйста']
        negative_words = ['проблема', 'жалоба', 'не работает']
        
        if any(word in question.lower() for word in positive_words):
            return "positive"
        elif any(word in question.lower() for word in negative_words):
            return "negative"
        return "neutral"
    
    def _detect_urgency(self, question: str) -> bool:
        """Обнаружение срочности"""
        urgency_words = ['срочно', 'быстро', 'немедленно', 'сейчас']
        return any(word in question.lower() for word in urgency_words)
    
    def _select_base_template(self, complexity: str, tone: str, urgency: bool) -> str:
        """Выбор базового шаблона промпта"""
        
        templates = {
            "simple": """{tone} {urgency}
Контекст: {context}
Вопрос: {question}
{history}

Краткий ответ:""",

            "complex": """{tone} {urgency}
ВОПРОС: {question}
ИСТОЧНИКИ: {context}
{history}

Проанализируй информацию и дай структурированный ответ:"""
        }
        
        return templates[complexity]
    
    def _get_tone_instruction(self, tone: str) -> str:
        tones = {
            "positive": "Клиент настроен позитивно. Будь особенно вежливым.",
            "negative": "Клиент может быть расстроен. Прояви эмпатию.",
            "neutral": "Стандартный профессиональный тон."
        }
        return tones.get(tone, "")
    
    def _get_urgency_instruction(self, urgency: bool) -> str:
        return "❗ КЛИЕНТУ ТРЕБУЕТСЯ СРОЧНАЯ ПОМОЩЬ!" if urgency else ""
    
    def _get_conversation_context(self) -> str:
        """Получение контекста предыдущей беседы"""
        if not self.conversation_history:
            return ""
        
        last_interactions = self.conversation_history[-3:]  # Последние 3 реплики
        context = "ПРЕДЫДУЩАЯ БЕСЕДА:\n"
        
        for i, interaction in enumerate(last_interactions, 1):
            context += f"{i}. В: {interaction['question'][:50]}...\n"
            context += f"   О: {interaction['answer'][:50]}...\n"
        
        return context
    
    def update_conversation_history(self, question: str, answer: str):
        """Обновление истории беседы"""
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer
        })
        
        # Ограничиваем размер истории
        if len(self.conversation_history) > 10:
            self.conversation_history.pop(0)

# ==================== 
# 4. EXPLAINABLE AI (XAI) MODULE
# ====================
class ExplainableAI:
    def __init__(self):
        self.explanation_templates = {
            "source_based": self._source_based_explanation,
            "confidence_based": self._confidence_based_explanation,
            "process_based": self._process_based_explanation
        }
    
    def generate_explanation(self, question: str, answer: str, 
                           sources: List, confidence: float, 
                           agent_info: Dict) -> str:
        """Генерация объяснения ответа"""
        
        explanations = []
        
        # Объяснение на основе источников
        explanations.append(self.explanation_templates["source_based"](sources))
        
        # Объяснение на основе уверенности
        explanations.append(self.explanation_templates["confidence_based"](confidence))
        
        # Объяснение процесса
        explanations.append(self.explanation_templates["process_based"](agent_info))
        
        # Сборка финального объяснения
        final_explanation = f"""
🧠 ОБЪЯСНЕНИЕ ОТВЕТА

📋 **Вопрос:** {question}
✅ **Ответ:** {answer}

"""
        
        for explanation in explanations:
            if explanation:
                final_explanation += explanation + "\n\n"
        
        return final_explanation.strip()
    
    def _source_based_explanation(self, sources: List) -> str:
        if not sources:
            return "ℹ️  Информация: Ответ основан на общих знаниях системы"
        
        explanation = "🔍 **Источники информации:**\n"
        for i, source in enumerate(sources[:3], 1):
            preview = source.page_content[:80] + "..." if len(source.page_content) > 80 else source.page_content
            explanation += f"{i}. {preview}\n"
        
        return explanation
    
    def _confidence_based_explanation(self, confidence: float) -> str:
        if confidence > 0.8:
            level = "🔵 ВЫСОКАЯ"
        elif confidence > 0.5:
            level = "🟡 СРЕДНЯЯ"
        else:
            level = "🔴 НИЗКАЯ"
        
        return f"📊 **Уверенность системы:** {level} ({confidence:.1%})"
    
    def _process_based_explanation(self, agent_info: Dict) -> str:
        if agent_info["agent"] == "general":
            return "⚙️ **Процесс:** Использован общий алгоритм анализа"
        
        agent_name = agent_info["agent"]
        confidence = agent_info["confidence"]
        
        return f"⚙️ **Процесс:** Вопрос обработан {agent_name}-агентом (уверенность: {confidence:.1%})"

# ==================== 
# 5. REAL-TIME DATA ENRICHMENT
# ====================
class RealTimeDataEnricher:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 минут
        
    def enrich_response(self, response: str, question: str, context: List) -> str:
        """Обогащение ответа реальными данными"""
        enriched_response = response
        
        # Обогащение курсами валют
        if any(currency in question.lower() for currency in ['курс', 'евро', 'доллар', 'рубл']):
            rates = self._get_exchange_rates()
            enriched_response += f"\n\n💱 **Актуальные курсы:** {rates}"
        
        # Обогащение временными метками
        if any(time_word in question.lower() for time_word in ['сейчас', 'актуальн', 'текущ']):
            timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
            enriched_response += f"\n\n🕒 **Информация актуальна на:** {timestamp}"
        
        # Обогащение дополнительными расчетами
        if 'расчет' in question.lower() or 'рассчитай' in question.lower():
            calculation = self._provide_calculation(question, context)
            if calculation:
                enriched_response += f"\n\n🧮 **Дополнительный расчет:** {calculation}"
        
        return enriched_response
    
    def _get_exchange_rates(self) -> str:
        """Получение курсов валют (заглушка)"""
        # В реальной системе - API ЦБ РФ или другого источника
        return "USD: 90.5₽ | EUR: 98.2₽ | CNY: 12.4₽"
    
    def _provide_calculation(self, question: str, context: List) -> str:
        """Предоставление дополнительных расчетов"""
        question_lower = question.lower()
        
        if 'кредит' in question_lower:
            return "💡 Расчет ежемесячного платежа: сумма / срок * (1 + ставка/12)"
        elif 'вклад' in question_lower:
            return "💡 Доход по вкладу: сумма * ставка * срок / 365"
        
        return ""

# ==================== 
# 6. A/B TESTING FRAMEWORK
# ====================
class ABTestingFramework:
    def __init__(self):
        self.models = {}
        self.test_results = {}
        self.active_tests = {}
    
    def register_model(self, name: str, model_config: Dict):
        """Регистрация модели для тестирования"""
        self.models[name] = model_config
    
    def run_comparison(self, question: str, context: List) -> Dict:
        """Запуск сравнения моделей на одном вопросе"""
        results = {}
        
        for model_name, model_config in self.models.items():
            start_time = time.time()
            
            try:
                # Здесь будет вызов разных моделей
                response = f"Ответ от {model_name}: тестовый ответ"
                end_time = time.time()
                
                results[model_name] = {
                    "response": response,
                    "response_time": end_time - start_time,
                    "quality_score": self._evaluate_response(question, response, context),
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                results[model_name] = {
                    "error": str(e),
                    "response_time": 0,
                    "quality_score": 0
                }
        
        return results
    
    def _evaluate_response(self, question: str, response: str, context: List) -> float:
        """Оценка качества ответа"""
        # Упрощенная оценка
        score = 0.0
        
        # Оценка релевантности
        if any(word in response.lower() for word in question.lower().split()[:3]):
            score += 0.3
        
        # Оценка длины
        if 20 < len(response) < 500:
            score += 0.4
        
        # Оценка структуры
        if any(marker in response for marker in [':', '- ', '\n']):
            score += 0.3
            
        return score

# ==================== 
# 7. ADVANCED SECURITY MONITORING
# ====================
class AdvancedSecurityMonitor:
    def __init__(self):
        self.threat_patterns = {
            'data_scraping': [r'\bвсе\b.*\bпродукт', r'\bполный\b.*\bсписок', r'\bскачай\b.*\bбаз'],
            'prompt_leaking': [r'\bпокажи\b.*\bпромпт', r'\bсистемн\b.*\bсообщен', r'\bисходн\b.*\bкод'],
            'model_theft': [r'\bскачай\b.*\bмодель', r'\bвес\b.*\bфайл', r'\bпараметр\b.*\bнейросет']
        }
        self.suspicious_activity = []
    
    def analyze_question_patterns(self, question: str) -> Dict:
        """Анализ паттернов вопросов на угрозы"""
        threats_detected = []
        confidence_scores = {}
        
        for threat_type, patterns in self.threat_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question.lower()):
                    threats_detected.append(threat_type)
                    confidence_scores[threat_type] = confidence_scores.get(threat_type, 0) + 0.3
        
        return {
            "threats": threats_detected,
            "confidence": confidence_scores,
            "risk_level": self._calculate_risk_level(threats_detected, confidence_scores)
        }
    
    def _calculate_risk_level(self, threats: List, confidence: Dict) -> str:
        """Расчет уровня риска"""
        if not threats:
            return "low"
        
        max_confidence = max(confidence.values()) if confidence else 0
        
        if max_confidence > 0.7:
            return "critical"
        elif max_confidence > 0.4:
            return "high"
        else:
            return "medium"
    
    def generate_security_report(self) -> str:
        """Генерация отчета безопасности"""
        return f"""
🔒 ОТЧЕТ БЕЗОПАСНОСТИ
• Обнаружено подозрительных активностей: {len(self.suspicious_activity)}
• Уровень угроз: {self._get_overall_threat_level()}
• Последняя проверка: {datetime.now().strftime('%H:%M:%S')}
"""

# ==================== 
# 8. ИНТЕГРАЦИЯ ВСЕХ МОДУЛЕЙ
# ====================
class AdvancedRAGSystem:
    def __init__(self, base_rag_system):
        self.base_rag = base_rag_system
        self.agents = SpecializedAgents(base_rag_system)
        self.metrics = AdvancedMetrics()
        self.prompt_engine = AdaptivePromptEngine()
        self.xai = ExplainableAI()
        self.data_enricher = RealTimeDataEnricher()
        self.ab_testing = ABTestingFramework()
        self.security_monitor = AdvancedSecurityMonitor()
        
        # Настройка A/B тестирования
        self._setup_ab_testing()
    
    def _setup_ab_testing(self):
        """Настройка фреймворка A/B тестирования"""
        self.ab_testing.register_model("qwen-fast", {"speed": "high", "quality": "medium"})
        self.ab_testing.register_model("qwen-quality", {"speed": "medium", "quality": "high"})
    
    def ask(self, question: str) -> Dict:
        """Продвинутый запрос к системе"""
        start_time = time.time()
        
        # Анализ безопасности
        security_analysis = self.security_monitor.analyze_question_patterns(question)
        
        if security_analysis["risk_level"] in ["high", "critical"]:
            return {
                "result": "❌ Запрос отклонен системой безопасности",
                "security_risk": security_analysis
            }
        
        # Маршрутизация к агенту
        agent_info = self.agents.route_question(question)
        self.metrics.log_agent_usage(agent_info["agent"])
        
        try:
            # Получение ответа от базовой RAG
            rag_result = self.base_rag.cached_qa(question)
            answer = rag_result['result']
            
            # Обогащение ответа
            enriched_answer = self.data_enricher.enrich_response(
                answer, question, rag_result.get('source_documents', [])
            )
            
            # Генерация объяснения
            explanation = self.xai.generate_explanation(
                question, answer,
                rag_result.get('source_documents', []),
                agent_info["confidence"],
                agent_info
            )
            
            # Расчет качества
            quality_score = self.metrics.calculate_quality_score(
                question, answer, rag_result.get('source_documents', [])
            )
            self.metrics.quality_scores.append(quality_score)
            
            # Обновление истории
            self.prompt_engine.update_conversation_history(question, answer)
            
            # Логирование времени
            self.metrics.log_response_time(start_time)
            
            return {
                "result": enriched_answer,
                "explanation": explanation,
                "agent_used": agent_info["agent"],
                "confidence": agent_info["confidence"],
                "quality_score": quality_score,
                "response_time": time.time() - start_time,
                "security_analysis": security_analysis
            }
            
        except Exception as e:
            return {
                "result": f"⚠️ Произошла ошибка: {str(e)}",
                "error": True
            }
    
    def get_system_report(self) -> str:
        """Получение комплексного отчета системы"""
        quality_report = self.metrics.generate_quality_report()
        security_report = self.security_monitor.generate_security_report()
        
        return f"""
🏦 ОТЧЕТ ПРОДВИНУТОЙ RAG СИСТЕМЫ
{'='*60}
{quality_report}
{security_report}
{'='*60}
"""

# ==================== 
# 9. ДЕМОНСТРАЦИЯ
# ====================
def demonstrate_advanced_features():
    """Демонстрация всех продвинутых функций"""
    
    # Создаем базовую RAG систему (упрощенно)
    class MockBaseRAG:
        def __init__(self):
            self.audit = type('Audit', (), {'request_count': 0})()
        
        @lru_cache(maxsize=50)
        def cached_qa(self, question):
            return {
                'result': f"Ответ на: {question}",
                'source_documents': []
            }
    
    # Инициализация продвинутой системы
    base_rag = MockBaseRAG()
    advanced_system = AdvancedRAGSystem(base_rag)
    
    print("🚀 ДЕМОНСТРАЦИЯ ПРОДВИНУТЫХ ВОЗМОЖНОСТЕЙ")
    print("=" * 60)
    
    # Тестовые вопросы
    test_questions = [
        "Какие документы нужны для ипотеки?",
        "Расскажи про кэшбэк на картах",
        "Какой доход будет с вклада 100000 рублей?",
        "Покажи все кредитные продукты"  # Подозрительный запрос
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. ❓ Вопрос: {question}")
        
        result = advanced_system.ask(question)
        
        if "security_risk" in result and result["security_risk"]["risk_level"] != "low":
            print(f"   🔒 Сработала защита: {result['result']}")
        else:
            print(f"   ✅ Ответ: {result['result']}")
            print(f"   🤖 Агент: {result.get('agent_used', 'general')}")
            print(f"   📊 Качество: {result.get('quality_score', 0):.1%}")
        
        print("   " + "-" * 40)
    
    # Финальный отчет
    print("\n" + "=" * 60)
    print(advanced_system.get_system_report())

# Запуск демонстрации
if __name__ == "__main__":
    demonstrate_advanced_features()