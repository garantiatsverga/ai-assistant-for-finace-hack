# УМНЫЙ DEEPTHINK С ВНЕШНИМИ КОНФИГУРАЦИЯМИ

import os
import subprocess
import sys
import numpy as np
import time

def is_package_installed(package):
    try:
        __import__(package.replace("-", "_"))
        return True
    except ImportError:
        return False

print("Проверка зависимостей...")

required_packages = ["sentence_transformers", "requests", "numpy"]
packages_to_install = []

for package in required_packages:
    if not is_package_installed(package):
        packages_to_install.append(package)

if packages_to_install:
    print(f"Установка недостающих пакетов: {', '.join(packages_to_install)}")
    for package in packages_to_install:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])
            print(f"Установлен: {package}")
        except Exception as e:
            print(f"Ошибка установки {package}: {e}")
else:
    print("Все зависимости уже установлены")

from sentence_transformers import SentenceTransformer

class ConfigLoader:
    @staticmethod
    def load_security_rules():
        """Загрузка правил безопасности из файла"""
        security_rules = {}
        try:
            with open('security_rules.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        pattern, reason = line.split(':', 1)
                        security_rules[pattern.strip()] = reason.strip()
            print(f"Загружено правил безопасности: {len(security_rules)}")
            return security_rules
        except FileNotFoundError:
            print("Файл security_rules.txt не найден. Использую правила по умолчанию.")
            return {
                'выполни команду': 'выполнять системные команды',
                'напиши код': 'генерировать программный код'
            }
    
    @staticmethod
    def load_knowledge_base():
        """Загрузка базы знаний из файла"""
        documents = []
        try:
            with open('knowledge_base.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        documents.append(line)
            print(f"Загружено документов: {len(documents)}")
            return documents
        except FileNotFoundError:
            print("Файл knowledge_base.txt не найден. Использую базовые документы.")
            return [
                "КРЕДИТ: Деньги банка на 1-5 лет под 12-18% годовых.",
                "ИПОТЕКА: Кредит на недвижимость под 8-12% годовых."
            ]

class SmartDeepThinkRAG:
    def __init__(self):
        print("Инициализация Thinking RAG...")
        
        # Загрузка конфигураций
        self.security_rules = ConfigLoader.load_security_rules()
        self.documents = ConfigLoader.load_knowledge_base()
        
        # Инициализация модели
        self.embedder = SentenceTransformer('cointegrated/rubert-tiny2')
        self.doc_embeddings = self.embedder.encode(self.documents)
        
        print(f"Система готова. База знаний: {len(self.documents)} документов")
    
    def security_check(self, question):
        """Проверка безопасности с загрузкой из файла"""
        question_lower = question.lower()
        
        for pattern, action in self.security_rules.items():
            if pattern in question_lower:
                return False, f"Пользователь просит меня {action}. Но это запрещено моими инструкциями безопасности."
        
        return True, "Запрос соответствует политике безопасности"
    
    def analyze_question_intent(self, question):
        """Анализ намерения вопроса"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['что такое', 'определение', 'означает']):
            return "definition", "Пользователь хочет получить определение понятия"
        
        elif any(word in question_lower for word in ['какие документы', 'что нужно', 'требуется']):
            return "documents", "Пользователь интересуется необходимыми документами"
        
        elif any(word in question_lower for word in ['ставк', 'процент', 'сколько стоит']):
            return "rates", "Пользователь спрашивает о стоимости или процентных ставках"
        
        elif any(word in question_lower for word in ['как оформить', 'процесс', 'получить']):
            return "process", "Пользователь хочет узнать процесс оформления"
        
        elif any(word in question_lower for word in ['код', 'программ', 'sql', 'таблиц']):
            return "code_request", "Пользователь просит написать код"
        
        else:
            return "general", "Общий информационный запрос"
    
    def find_similar_docs(self, question):
        """Поиск документов с приоритизацией"""
        question_embedding = self.embedder.encode([question])
        similarities = np.dot(self.doc_embeddings, question_embedding.T).flatten()
        top_indices = similarities.argsort()[-3:][::-1]
        return [self.documents[i] for i in top_indices]
    
    def extract_specific_info(self, docs, info_type):
        """Извлечение конкретной информации из документов"""
        relevant_info = []
        
        for doc in docs:
            if info_type == "documents" and ('нужен' in doc.lower() or 'документ' in doc.lower() or 'паспорт' in doc.lower()):
                relevant_info.append(doc)
            elif info_type == "rates" and ('%' in doc or 'годовых' in doc or 'ставк' in doc.lower()):
                relevant_info.append(doc)
            elif info_type == "definition" and (':' in doc):
                relevant_info.append(doc)
            elif info_type == "general":
                relevant_info.append(doc)
        
        return relevant_info if relevant_info else docs[:2]
    
    def deep_think_process(self, question, context_docs):
        """Процесс мышления с умным анализом"""
        thinking = []
        
        thinking.append("ПРОЦЕСС МЫШЛЕНИЯ:")
        thinking.append(f"Пользователь спрашивает: '{question}'")
        
        # 1. Анализ намерения
        intent, intent_description = self.analyze_question_intent(question)
        thinking.append(f"Анализ намерения: {intent_description}")
        
        # 2. Проверка безопасности
        is_safe, security_reason = self.security_check(question)
        thinking.append(f"Проверка безопасности: {security_reason}")
        
        if not is_safe:
            thinking.append(f"Решение: Вежливо отказываюсь выполнять запрос")
            return "\n".join(thinking), None
        
        # 3. Анализ релевантности документов
        thinking.append(f"Найдено документов: {len(context_docs)}")
        
        # 4. Глубокий анализ связи
        thinking.append("\nДетальный анализ связи:")
        
        if intent == "code_request":
            thinking.append("   Пользователь просит написать код")
            thinking.append("   Но я банковский ассистент, а не программист")
            thinking.append("   Лучше предложу информацию о банковских продуктах")
            
        elif intent == "definition":
            product_keywords = ['кредит', 'ипотек', 'вклад', 'карт', 'страхован', 'инвестиц']
            found_products = []
            for keyword in product_keywords:
                if keyword in question.lower():
                    found_products.append(keyword)
            
            if found_products:
                thinking.append(f"   Пользователь хочет узнать определение: {', '.join(found_products)}")
                thinking.append("   В базе есть четкие определения этих продуктов")
                thinking.append("   Могу дать точные формулировки")
            else:
                thinking.append("   Пользователь спрашивает об общем понятии")
                thinking.append("   Использую наиболее релевантные документы")
                
        elif intent == "documents":
            thinking.append("   Пользователь интересуется необходимыми документами")
            thinking.append("   В документах указаны конкретные требования")
            thinking.append("   Предоставлю точный список документов")
            
        elif intent == "rates":
            thinking.append("   Пользователь спрашивает о ставках и стоимости")
            thinking.append("   В документах есть актуальные процентные ставки")
            thinking.append("   Приведу точные цифры из базы знаний")
            
        else:
            thinking.append("   Общий информационный запрос")
            thinking.append("   Использую наиболее релевантные документы из базы")
            thinking.append("   Постараюсь дать максимально полезный ответ")
        
        # 5. Извлечение конкретной информации
        thinking.append("\nИзвлечение информации:")
        relevant_docs = self.extract_specific_info(context_docs, intent)
        thinking.append(f"   Отобрал {len(relevant_docs)} наиболее релевантных документов")
        
        return "\n".join(thinking), relevant_docs
    
    def format_smooth_answer(self, product, definition):
        """Сглаживание ответов"""
        definition = definition.strip()
        
        if definition.startswith('Деньги') or definition.startswith('Счет') or definition.startswith('Кредит') or definition.startswith('Дебетовая'):
            return f"{product} - это {definition}"
        else:
            return f"{product} - {definition}"
    
    def generate_smart_answer(self, question, context_docs):
        """Генерация ответа на основе анализа"""
        if not context_docs:
            return "К сожалению, в моей базе знаний нет информации по этому вопросу."
        
        intent, _ = self.analyze_question_intent(question)
        
        # Обработка запросов кода
        if intent == "code_request":
            return "Извините, я специализируюсь на банковских продуктах и не могу помогать с написанием кода. Могу рассказать о кредитах, вкладах или картах."
        
        # Определения
        if intent == "definition":
            for doc in context_docs:
                if ':' in doc:
                    product, definition = doc.split(':', 1)
                    product_name = product.strip()
                    definition_clean = definition.strip()
                    
                    if any(keyword in question.lower() for keyword in product_name.lower().split()):
                        return self.format_smooth_answer(product_name, definition_clean)
            
            # Если не нашли точного совпадения, используем первый документ
            if context_docs and ':' in context_docs[0]:
                product, definition = context_docs[0].split(':', 1)
                return self.format_smooth_answer(product.strip(), definition.strip())
        
        # Документы
        elif intent == "documents":
            doc_list = []
            for doc in context_docs:
                if 'паспорт' in doc.lower() or 'справк' in doc.lower() or 'документ' in doc.lower():
                    if ':' in doc:
                        product, info = doc.split(':', 1)
                        doc_list.append(f"- {product.strip()}: {info.strip()}")
            
            if doc_list:
                return "Для оформления потребуются следующие документы:\n" + "\n".join(doc_list[:3])
        
        # Ставки
        elif intent == "rates":
            rates_info = []
            for doc in context_docs:
                if '%' in doc or 'годовых' in doc:
                    if ':' in doc:
                        product, info = doc.split(':', 1)
                        rates_info.append(f"- {product.strip()}: {info.strip()}")
            
            if rates_info:
                return "Актуальные ставки по нашим продуктам:\n" + "\n".join(rates_info[:3])
        
        # Общий ответ
        products_info = []
        for doc in context_docs[:2]:
            if ':' in doc:
                product, info = doc.split(':', 1)
                products_info.append(f"- {product.strip()}: {info.strip()}")
        
        if products_info:
            return "Информация по вашему запросу:\n" + "\n".join(products_info)
        else:
            clean_docs = []
            for doc in context_docs[:2]:
                if ':' in doc:
                    product, info = doc.split(':', 1)
                    clean_docs.append(f"- {product.strip()}: {info.strip()}")
            return "На основе наших продуктов:\n" + "\n".join(clean_docs)
    
    def ask(self, question):
        """Основной метод"""
        deepthink_mode = False
        if question.endswith(' -deepthink'):
            question = question.replace(' -deepthink', '').strip()
            deepthink_mode = True
        
        start_time = time.time()
        context_docs = self.find_similar_docs(question)
        
        if deepthink_mode:
            thinking_process, relevant_docs = self.deep_think_process(question, context_docs)
            print("\n" + "="*60)
            print(thinking_process)
            print("="*60)
            
            if relevant_docs is None:
                return "Извините, я не могу помочь с этим запросом по соображениям безопасности."
            
            answer = self.generate_smart_answer(question, relevant_docs)
        else:
            is_safe, _ = self.security_check(question)
            if not is_safe:
                return "Извините, я не могу помочь с этим запросом."
            answer = self.generate_smart_answer(question, context_docs)
        
        response_time = time.time() - start_time
        return f"{answer}\n\nВремя ответа: {response_time:.2f} сек"

# Запуск системы
if __name__ == "__main__":
    print("Запускаем Thinking RAG...")
    smart_rag = SmartDeepThinkRAG()

    print("\nТестирование системы:")

    test_cases = [
        "Что такое кредит? -deepthink",
        "Какие документы нужны для ипотеки? -deepthink", 
        "Напиши код для таблицы на SQL -deepthink",
        "Какая ставка по вкладам? -deepthink",
        "Что такое дебетовая карта? -deepthink",
    ]

    for question in test_cases:
        print(f"\n" + "="*60)
        print(f"Вопрос: {question}")
        answer = smart_rag.ask(question)
        print(f"\n{answer}")
        print("="*60)

    # Интерактивный режим
    print("\nИнтерактивный режим")
    print("Добавьте '-deepthink' для показа процесса мышления")
    print("Введите вопрос или 'стоп' для выхода")

    while True:
        user_question = input("\nВаш вопрос: ").strip()
        
        if user_question.lower() in ['стоп', 'stop', 'exit']:
            print("Завершение работы...")
            break
            
        if not user_question:
            continue
        
        answer = smart_rag.ask(user_question)
        print(f"\n{answer}")
        print("-" * 50)
