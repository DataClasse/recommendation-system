"""
Сервис хранения похожих треков.

Предоставляет быстрый доступ к похожим трекам для онлайн-рекомендаций.
"""
import pandas as pd
from fastapi import FastAPI
from contextlib import asynccontextmanager


class TrackSimilarity:
    """Класс для работы с похожими треками."""
    
    def __init__(self):
        self.similarities = None
        self.request_count = 0
    
    def load_similarities(self, path):
        """
        Загрузка похожих треков из parquet файла.
        
        Формат данных: ["track_id_1", "track_id_2", "score"]
        
        Args:
            path: Путь к файлу similar.parquet
        """
        print("Загрузка похожих треков...")
        self.similarities = pd.read_parquet(path)
        
        # Фильтруем самоподобие (track_id_1 == track_id_2)
        before_count = len(self.similarities)
        self.similarities = self.similarities[
            self.similarities['track_id_1'] != self.similarities['track_id_2']
        ]
        filtered_count = before_count - len(self.similarities)
        if filtered_count > 0:
            print(f"  Отфильтровано пар самоподобия: {filtered_count}")
        
        self.similarities = self.similarities.set_index('track_id_1')
        self.track_col = 'track_id_2'
        self.score_col = 'score'
        
        print(f"✓ Загружено {len(self.similarities)} связей похожести")
    
    def get_similar_tracks(self, track_id: int, k: int = 10):
        """
        Получение похожих треков для заданного трека.
        
        Args:
            track_id: Идентификатор трека
            k: Количество похожих треков
        
        Returns:
            Списки ID треков и их scores
        """
        self.request_count += 1
        
        try:
            # Получаем похожие треки (векторная операция)
            similar = self.similarities.loc[track_id]
            
            # Если несколько записей - берём топ k
            if isinstance(similar, pd.DataFrame):
                similar = similar.nlargest(k, self.score_col)
                track_ids = similar[self.track_col].tolist()
                scores = similar[self.score_col].tolist()
            else:
                # Одна запись
                track_ids = [similar[self.track_col]]
                scores = [similar[self.score_col]]
            
            return track_ids[:k], scores[:k]
        
        except KeyError:
            # Трек не найден в базе похожих
            return [], []
    
    def get_stats(self):
        """Получение статистики."""
        return {
            "total_similarities": len(self.similarities),
            "requests_count": self.request_count
        }


# Глобальный объект
similarity_store = TrackSimilarity()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Загрузка при старте
    similarity_store.load_similarities("recsys/recommendations/similar.parquet")
    print("✓ Сервис похожих треков запущен")
    
    yield
    
    # Статистика при остановке
    stats = similarity_store.get_stats()
    print(f"\n=== Статистика ===")
    print(f"Обработано запросов: {stats['requests_count']}")
    print("✓ Сервис похожих треков остановлен")


# FastAPI приложение
app = FastAPI(title="Track Similarity Service", lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Проверка состояния сервиса."""
    return {"status": "healthy", "service": "similarity_store"}


@app.post("/similar_tracks")
async def get_similar_tracks(track_id: int, k: int = 10):
    """
    Получение похожих треков.
    
    Args:
        track_id: Идентификатор трека
        k: Количество похожих треков
    
    Returns:
        Списки похожих треков и их scores
    """
    track_ids, scores = similarity_store.get_similar_tracks(track_id, k)
    
    # Формат ответа совместим с референсным решением
    # Референс использует: {"track_id_2": [...], "score": [...]}
    return {
        "track_id_2": track_ids,
        "score": scores
    }


@app.get("/stats")
async def get_statistics():
    """Получение статистики сервиса."""
    return similarity_store.get_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)

