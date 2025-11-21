"""
Главный API-сервис рекомендательной системы.

Объединяет офлайн и онлайн рекомендации для пользователей.
"""
import pandas as pd
import requests
from fastapi import FastAPI
from contextlib import asynccontextmanager


# Конфигурация
SIMILARITY_SERVICE_URL = "http://127.0.0.1:8010"
EVENT_SERVICE_URL = "http://127.0.0.1:8020"


class MusicRecommender:
    """Класс для работы с музыкальными рекомендациями."""
    
    def __init__(self):
        self.personal_recs = None
        self.popular_recs = None
        self.request_stats = {"personal": 0, "popular": 0}
    
    def load_recommendations(self, personal_path, popular_path):
        """Загрузка рекомендаций из parquet файлов.
        
        Формат данных в файлах:
        - personal_path (recommendations.parquet): ["user_id", "track_id", "score", "rank"]
          Загружаются только ["user_id", "track_id", "rank"] для экономии памяти
        - popular_path (top_popular.parquet): ["track_id", "rank", "tracks_played"]
          Загружаются только ["track_id", "rank"]
        """
        print("Загрузка персональных рекомендаций...")
        self.personal_recs = pd.read_parquet(
            personal_path, 
            columns=["user_id", "track_id", "rank"]
        )
        # Сортируем по rank для корректного порядка рекомендаций
        self.personal_recs = self.personal_recs.sort_values(
            by=["user_id", "rank"], ascending=[True, True]
        ).set_index("user_id")
        
        print("Загрузка популярных рекомендаций...")
        self.popular_recs = pd.read_parquet(
            popular_path,
            columns=["track_id", "rank"]
        )
        # Сортируем по rank для корректного порядка
        self.popular_recs = self.popular_recs.sort_values(
            by="rank", ascending=True
        )
        
        print(f"✓ Загружено {len(self.personal_recs)} персональных рекомендаций")
        print(f"✓ Загружено {len(self.popular_recs)} популярных треков")
    
    def get_user_recommendations(self, user_id: int, k: int = 100):
        """
        Получение рекомендаций для пользователя.
        Возвращает персональные или популярные (fallback).
        Рекомендации уже отсортированы по rank при загрузке.
        """
        try:
            user_recs = self.personal_recs.loc[user_id]
            # Если несколько строк - берем первые k по rank
            if isinstance(user_recs, pd.Series):
                recs = [user_recs["track_id"]]
            else:
                recs = user_recs["track_id"].tolist()[:k]
            self.request_stats["personal"] += 1
            return recs
        except KeyError:
            # Пользователь не найден - возвращаем популярные
            recs = self.popular_recs["track_id"].tolist()[:k]
            self.request_stats["popular"] += 1
            return recs
    
    def print_stats(self):
        """Вывод статистики запросов."""
        print("\n=== Статистика запросов ===")
        print(f"Персональные: {self.request_stats['personal']}")
        print(f"Популярные (fallback): {self.request_stats['popular']}")


# Глобальный объект рекомендера
music_rec = MusicRecommender()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Загрузка при старте
    music_rec.load_recommendations(
        "recsys/recommendations/recommendations.parquet",
        "recsys/recommendations/top_popular.parquet"
    )
    print("✓ API-сервис запущен")
    
    yield
    
    # Статистика при остановке
    music_rec.print_stats()
    print("✓ API-сервис остановлен")


# Создание FastAPI приложения
app = FastAPI(title="Music Recommendation API", lifespan=lifespan)


def merge_recommendations(online_recs, offline_recs, k: int = 100):
    """
    Объединение онлайн и офлайн рекомендаций с чередованием.
    Удаляет дубликаты с сохранением порядка.
    """
    merged = []
    min_len = min(len(online_recs), len(offline_recs))
    
    # Чередование (векторная операция через zip)
    for online_item, offline_item in zip(online_recs[:min_len], 
                                          offline_recs[:min_len]):
        merged.append(online_item)
        merged.append(offline_item)
    
    # Добавляем остатки
    merged.extend(online_recs[min_len:])
    merged.extend(offline_recs[min_len:])
    
    # Удаление дубликатов с сохранением порядка (векторная операция)
    seen = set()
    unique_recs = []
    for item in merged:
        if item not in seen:
            seen.add(item)
            unique_recs.append(item)
    
    return unique_recs[:k]


@app.get("/health")
async def health_check():
    """Проверка состояния сервиса."""
    return {"status": "healthy", "service": "api_main"}


@app.post("/recommendations_offline")
async def get_offline_recommendations(user_id: int, k: int = 100):
    """
    Получение офлайн рекомендаций для пользователя.
    
    Args:
        user_id: Идентификатор пользователя
        k: Количество рекомендаций
    
    Returns:
        Список ID треков
    """
    recs = music_rec.get_user_recommendations(user_id, k)
    return {"recs": recs}


@app.post("/recommendations_online")
async def get_online_recommendations(user_id: int, k: int = 100):
    """
    Получение онлайн рекомендаций на основе последних событий.
    
    Args:
        user_id: Идентификатор пользователя
        k: Количество рекомендаций
    
    Returns:
        Список ID треков
    """
    # Получаем последние события пользователя
    try:
        response = requests.post(
            f"{EVENT_SERVICE_URL}/get_events",
            params={"user_id": user_id, "k": 5},
            timeout=2
        )
        events = response.json()["events"]
    except Exception:
        # Если сервис недоступен - возвращаем пустой список
        return {"recs": []}
    
    if not events:
        return {"recs": []}
    
    # Для каждого события получаем похожие треки
    all_tracks = []
    all_scores = []
    
    for track_id in events:
        try:
            response = requests.post(
                f"{SIMILARITY_SERVICE_URL}/similar_tracks",
                params={"track_id": track_id, "k": k},
                timeout=2
            )
            result = response.json()
            # Формат ответа: {"track_id_2": [...], "score": [...]}
            all_tracks.extend(result.get("track_id_2", []))
            all_scores.extend(result.get("score", []))
        except Exception:
            continue
    
    # Сортировка по score (векторная операция через zip + sorted)
    if all_tracks:
        sorted_pairs = sorted(
            zip(all_tracks, all_scores),
            key=lambda x: x[1],
            reverse=True
        )
        # Удаление дубликатов
        seen = set()
        unique_tracks = []
        for track_id, _ in sorted_pairs:
            if track_id not in seen:
                seen.add(track_id)
                unique_tracks.append(track_id)
        
        return {"recs": unique_tracks[:k]}
    
    return {"recs": []}


@app.post("/recommendations")
async def get_recommendations(user_id: int, k: int = 100):
    """
    Получение комбинированных рекомендаций (онлайн + офлайн).
    
    Args:
        user_id: Идентификатор пользователя
        k: Количество рекомендаций
    
    Returns:
        Список ID треков
    """
    # Получаем оба типа рекомендаций
    offline_result = await get_offline_recommendations(user_id, k)
    online_result = await get_online_recommendations(user_id, k)
    
    offline_recs = offline_result["recs"]
    online_recs = online_result["recs"]
    
    # Если нет онлайн истории - возвращаем только офлайн
    if not online_recs:
        return {"recs": offline_recs}
    
    # Объединяем рекомендации
    merged_recs = merge_recommendations(online_recs, offline_recs, k)
    
    return {"recs": merged_recs}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

