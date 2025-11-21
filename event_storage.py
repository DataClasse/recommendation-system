"""
Сервис хранения истории событий пользователей.

Хранит последние N прослушанных треков для каждого пользователя в памяти.
"""
from collections import defaultdict, deque
from fastapi import FastAPI


# Хранилище событий (в памяти)
MAX_EVENTS_PER_USER = 20

class EventHistory:
    """Класс для управления историей событий пользователей."""
    
    def __init__(self, max_events=MAX_EVENTS_PER_USER):
        # Используем defaultdict с deque для эффективного хранения
        self.user_events = defaultdict(lambda: deque(maxlen=max_events))
        self.stats = {"total_events": 0, "unique_users": 0}
    
    def add_event(self, user_id: int, track_id: int):
        """
        Добавление события прослушивания трека.
        
        Args:
            user_id: Идентификатор пользователя
            track_id: Идентификатор трека
        """
        # deque автоматически удаляет старые события
        self.user_events[user_id].append(track_id)
        self.stats["total_events"] += 1
        self.stats["unique_users"] = len(self.user_events)
    
    def get_recent_events(self, user_id: int, k: int = 5):
        """
        Получение последних K событий пользователя.
        
        Args:
            user_id: Идентификатор пользователя
            k: Количество последних событий
        
        Returns:
            Список track_id в обратном хронологическом порядке
        """
        events = list(self.user_events[user_id])
        # Возвращаем последние k событий
        return events[-k:][::-1] if events else []
    
    def get_stats(self):
        """Получение статистики."""
        return self.stats


# Глобальное хранилище
event_store = EventHistory()

# FastAPI приложение
app = FastAPI(title="Event Storage Service")


@app.get("/health")
async def health_check():
    """Проверка состояния сервиса."""
    return {"status": "healthy", "service": "event_storage"}


@app.post("/add_event")
async def add_event(user_id: int, track_id: int):
    """
    Добавление события прослушивания трека.
    
    Args:
        user_id: Идентификатор пользователя
        track_id: Идентификатор трека
    
    Returns:
        Статус операции
    """
    event_store.add_event(user_id, track_id)
    return {"status": "success", "user_id": user_id, "track_id": track_id}


@app.post("/get_events")
async def get_events(user_id: int, k: int = 5):
    """
    Получение последних событий пользователя.
    
    Args:
        user_id: Идентификатор пользователя
        k: Количество последних событий (по умолчанию 5)
    
    Returns:
        Список ID треков в обратном хронологическом порядке
    """
    events = event_store.get_recent_events(user_id, k)
    return {"events": events, "count": len(events)}


@app.get("/stats")
async def get_statistics():
    """Получение статистики сервиса."""
    return event_store.get_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)

