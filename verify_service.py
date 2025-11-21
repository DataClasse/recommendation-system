"""
Скрипт проверки работы API-сервиса рекомендаций.

Тестирует все эндпоинты и сохраняет результаты в лог-файл.
"""
import requests
import logging
import time
from datetime import datetime


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('service_test.log', mode='w'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# URL сервисов
API_MAIN_URL = "http://127.0.0.1:8000"
SIMILARITY_URL = "http://127.0.0.1:8010"
EVENT_URL = "http://127.0.0.1:8020"


def check_service_health(name, url):
    """Проверка работоспособности сервиса."""
    try:
        response = requests.get(f"{url}/health", timeout=2)
        if response.status_code == 200:
            logger.info(f"✓ {name}: Сервис работает")
            return True
        else:
            logger.error(f"✗ {name}: Ошибка {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ {name}: Недоступен - {e}")
        return False


def test_offline_recommendations():
    """Тест офлайн рекомендаций."""
    logger.info("\n=== Тест офлайн рекомендаций ===")
    
    test_user_id = 123456
    k = 10
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_MAIN_URL}/recommendations_offline",
            params={"user_id": test_user_id, "k": k},
            timeout=5
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            recs = data.get("recs", [])
            logger.info(f"✓ Получено {len(recs)} рекомендаций за {elapsed:.3f}с")
            logger.info(f"  Первые 5 треков: {recs[:5]}")
            return True
        else:
            logger.error(f"✗ Ошибка: {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"✗ Исключение: {e}")
        return False


def test_online_recommendations():
    """Тест онлайн рекомендаций."""
    logger.info("\n=== Тест онлайн рекомендаций ===")
    
    test_user_id = 789012
    test_tracks = [100, 200, 300]
    
    # Добавляем события
    logger.info("Добавление тестовых событий...")
    for track_id in test_tracks:
        try:
            response = requests.post(
                f"{EVENT_URL}/add_event",
                params={"user_id": test_user_id, "track_id": track_id},
                timeout=2
            )
            if response.status_code == 200:
                logger.info(f"  ✓ Добавлено событие: track_id={track_id}")
        except Exception as e:
            logger.warning(f"  ✗ Ошибка добавления: {e}")
    
    # Получаем онлайн рекомендации
    time.sleep(0.5)  # Небольшая задержка
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_MAIN_URL}/recommendations_online",
            params={"user_id": test_user_id, "k": 10},
            timeout=5
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            recs = data.get("recs", [])
            logger.info(f"✓ Получено {len(recs)} онлайн рекомендаций за {elapsed:.3f}с")
            logger.info(f"  Первые 5 треков: {recs[:5]}")
            return True
        else:
            logger.error(f"✗ Ошибка: {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"✗ Исключение: {e}")
        return False


def test_combined_recommendations():
    """Тест комбинированных рекомендаций."""
    logger.info("\n=== Тест комбинированных рекомендаций ===")
    
    test_user_id = 111222
    k = 20
    
    # Добавляем несколько событий для пользователя
    test_tracks = [1001, 2002, 3003]
    for track_id in test_tracks:
        try:
            requests.post(
                f"{EVENT_URL}/add_event",
                params={"user_id": test_user_id, "track_id": track_id},
                timeout=2
            )
        except Exception:
            pass
    
    time.sleep(0.5)
    
    try:
        start = time.time()
        response = requests.post(
            f"{API_MAIN_URL}/recommendations",
            params={"user_id": test_user_id, "k": k},
            timeout=5
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            recs = data.get("recs", [])
            logger.info(f"✓ Получено {len(recs)} комбинированных рекомендаций за {elapsed:.3f}с")
            logger.info(f"  Первые 10 треков: {recs[:10]}")
            
            # Проверяем отсутствие дубликатов
            unique_recs = len(set(recs))
            if unique_recs == len(recs):
                logger.info(f"✓ Дубликаты отсутствуют")
            else:
                logger.warning(f"⚠ Найдено дубликатов: {len(recs) - unique_recs}")
            
            return True
        else:
            logger.error(f"✗ Ошибка: {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"✗ Исключение: {e}")
        return False


def test_similar_tracks():
    """Тест сервиса похожих треков."""
    logger.info("\n=== Тест сервиса похожих треков ===")
    
    test_track_id = 1000
    k = 5
    
    try:
        start = time.time()
        response = requests.post(
            f"{SIMILARITY_URL}/similar_tracks",
            params={"track_id": test_track_id, "k": k},
            timeout=5
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            # Исправлено: similarity_store возвращает track_id_2 и score
            track_ids = data.get("track_id_2", [])
            scores = data.get("score", [])
            
            logger.info(f"✓ Найдено {len(track_ids)} похожих треков за {elapsed:.3f}с")
            for i, (tid, score) in enumerate(zip(track_ids, scores), 1):
                logger.info(f"  {i}. Track {tid}: score={score:.4f}")
            
            return True
        else:
            logger.error(f"✗ Ошибка: {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"✗ Исключение: {e}")
        return False


def test_event_storage():
    """Тест сервиса хранения событий."""
    logger.info("\n=== Тест сервиса хранения событий ===")
    
    test_user_id = 999888
    test_tracks = [10, 20, 30, 40, 50]
    
    # Добавляем события
    for track_id in test_tracks:
        try:
            requests.post(
                f"{EVENT_URL}/add_event",
                params={"user_id": test_user_id, "track_id": track_id},
                timeout=2
            )
        except Exception:
            pass
    
    time.sleep(0.3)
    
    # Получаем события
    try:
        response = requests.post(
            f"{EVENT_URL}/get_events",
            params={"user_id": test_user_id, "k": 5},
            timeout=2
        )
        
        if response.status_code == 200:
            data = response.json()
            events = data.get("events", [])
            logger.info(f"✓ Получено {len(events)} событий")
            logger.info(f"  События: {events}")
            
            # Проверяем порядок (последние должны быть в начале)
            if events == test_tracks[::-1]:
                logger.info("✓ Порядок событий корректный (обратный хронологический)")
            
            return True
        else:
            logger.error(f"✗ Ошибка: {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"✗ Исключение: {e}")
        return False


def run_all_tests():
    """Запуск всех тестов."""
    logger.info("="*60)
    logger.info(f"НАЧАЛО ТЕСТИРОВАНИЯ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    # Проверка доступности сервисов
    logger.info("\n### Проверка доступности сервисов ###")
    services = [
        ("API Main", API_MAIN_URL),
        ("Similarity Store", SIMILARITY_URL),
        ("Event Storage", EVENT_URL)
    ]
    
    all_healthy = all(check_service_health(name, url) for name, url in services)
    
    if not all_healthy:
        logger.error("\n✗ Не все сервисы доступны. Проверьте запуск сервисов.")
        logger.error("Убедитесь, что запущены все 3 сервиса:")
        logger.error("  1. uvicorn similarity_store:app --port 8010")
        logger.error("  2. uvicorn event_storage:app --port 8020")
        logger.error("  3. uvicorn api_main:app --port 8000")
        return
    
    # Запуск функциональных тестов
    logger.info("\n### Функциональные тесты ###")
    
    tests = [
        ("Сервис похожих треков", test_similar_tracks),
        ("Хранилище событий", test_event_storage),
        ("Офлайн рекомендации", test_offline_recommendations),
        ("Онлайн рекомендации", test_online_recommendations),
        ("Комбинированные рекомендации", test_combined_recommendations)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\nЗапуск теста: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"✗ Критическая ошибка в тесте: {e}")
            results.append((test_name, False))
    
    # Итоговая статистика
    logger.info("\n" + "="*60)
    logger.info("ИТОГИ ТЕСТИРОВАНИЯ")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nВсего тестов: {total}")
    logger.info(f"Успешно: {passed}")
    logger.info(f"Провалено: {total - passed}")
    logger.info(f"Процент успеха: {passed/total*100:.1f}%")
    
    logger.info("\n" + "="*60)
    logger.info(f"ЗАВЕРШЕНО: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    logger.info(f"\nЛог сохранён в файл: service_test.log")


if __name__ == "__main__":
    run_all_tests()

