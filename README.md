# Музыкальная рекомендательная система

## Описание проекта

Прототип системы персональных музыкальных рекомендаций для стримингового сервиса.
Проект включает анализ данных, обучение моделей и API-сервис для выдачи рекомендаций.

**Гибридная рекомендательная система (ALS + CatBoost):** офлайн-пайплайн, REST API, три микросервиса, стратегия для холодных пользователей. Архитектура пригодна к переносу в прод.

## Клонирование репозитория

```bash
git clone https://github.com/DataClasse/recommendation-system.git
cd recommendation-system
```

Репозиторий: [https://github.com/DataClasse/recommendation-system](https://github.com/DataClasse/recommendation-system)

## Структура проекта

```
mle-project-sprint-4-v001/
├── data/                          # Исходные данные
│   ├── tracks.parquet
│   ├── catalog_names.parquet
│   └── interactions.parquet
├── recsys/
│   ├── data/                      # Подготовленные данные
│   │   ├── items.parquet
│   │   └── events.parquet
│   ├── model/                     # Сохранённые модели
│   │   ├── als_model.pkl
│   │   ├── user_encoder.pkl
│   │   ├── item_encoder.pkl
│   │   └── catboost_ranker.pkl
│   ├── recommendations/           # Рекомендации
│   │   ├── top_popular.parquet
│   │   ├── personal_als.parquet
│   │   ├── similar.parquet
│   │   └── recommendations.parquet
│   └── pictures/                  # Графики EDA
│       ├── user_activity.png
│       ├── top_tracks.png
│       └── top_genres.png
├── execution_log.txt              # Лог выполнения ноутбука
├── recommendations.ipynb          # Основной ноутбук с офлайн-пайплайном
├── api_main.py                    # Главный API-сервис
├── event_storage.py               # Хранилище истории пользователя
├── similarity_store.py            # Сервис похожих треков
├── verify_service.py              # Скрипт проверки
├── requirements.txt               # Зависимости
└── README.md                      # Этот файл
```

## Загрузка данных

Если данные отсутствуют, загрузите их:

```bash
wget https://storage.yandexcloud.net/mle-data/ym/tracks.parquet -P data
wget https://storage.yandexcloud.net/mle-data/ym/catalog_names.parquet -P data
wget https://storage.yandexcloud.net/mle-data/ym/interactions.parquet -P data
```

## Установка и настройка

### 1. Создание виртуального окружения

```bash
python3 -m venv venv_music_recs
source venv_music_recs/bin/activate
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Создайте файл `.env` в корне проекта со следующим содержимым:

```env
S3_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
S3_ENDPOINT_URL=https://storage.yandexcloud.net  # Опционально, для Yandex Object Storage
```

### 4. Проверка данных

Убедитесь, что в директории `data/` находятся три файла:
- tracks.parquet
- catalog_names.parquet
- interactions.parquet

## Запуск проекта

### Этап 1-3: Офлайн-пайплайн

Ноутбук `recommendations.ipynb` содержит весь офлайн-процесс (подготовка данных, обучение ALS/CatBoost, генерация рекомендаций). Все параметры конфигурации находятся в начале ноутбука в секции "КОНФИГУРАЦИЯ".

**Запуск в Jupyter Lab:**

```bash
jupyter lab recommendations.ipynb
```

Затем выполните все ячейки ноутбука последовательно (Cell → Run All).

**Основные параметры** (доля пользователей, гиперпараметры ALS/CatBoost, пути до артефактов) задаются в начале ноутбука. Ноутбук автоматически:

- использует кэш подготовленных данных (`recsys/data/items.parquet`, `recsys/data/events.parquet`);
- переиспользует сохранённые модели и рекомендации при неизменных данных (`recsys/model/*.pkl`, `recsys/recommendations/*.parquet`);
- логирует прогресс выполнения в `execution_log.txt`;
- выводит метрики качества в конце выполнения (Precision@5, Recall@5, Coverage, Novelty@5).

### Быстрая проверка

1. При необходимости измените параметры в начале ноутбука `recommendations.ipynb` (например, `USERS_SAMPLE_RATE` для уменьшения выборки пользователей).
2. Запустите все ячейки ноутбука и убедитесь, что:
   - в `execution_log.txt` появились логи выполнения;
   - обновились артефакты в `recsys/model/` и `recsys/recommendations/`.
3. Просмотрите метрики в конце ноутбука или в `execution_log.txt`.

### Выгрузка результатов в S3

Выгрузка в S3 интегрирована в ноутбук и **включена по умолчанию**. Выполняется автоматически после завершения всех этапов (ЭТАП 5 в ноутбуке).

**Пути сохранения в S3:**

- Данные: `recsys/data/` → `items.parquet`, `events.parquet`
- Рекомендации: `recsys/recommendations/` → `top_popular.parquet`, `personal_als.parquet`, `similar.parquet`, `recommendations.parquet`
- Модели: `recsys/model/` → `als_model.pkl`, `user_encoder.pkl`, `item_encoder.pkl`, `catboost_ranker.pkl`
- Графики: `recsys/pictures/` → `user_activity.png`, `top_tracks.png`, `top_genres.png`

**Отключение выгрузки:**

Если нужно отключить выгрузку, не устанавливайте переменную окружения `S3_BUCKET_NAME` или установите её в пустую строку. Ноутбук автоматически пропустит выгрузку, если S3 не настроен.

### Этап 4: Запуск API-сервиса

Откройте **три терминала** и запустите сервисы:

**Терминал 1: Сервис похожих треков**
```bash
uvicorn similarity_store:app --host 0.0.0.0 --port 8010
```

**Терминал 2: Хранилище событий**
```bash
uvicorn event_storage:app --host 0.0.0.0 --port 8020
```

**Терминал 3: Главный API**
```bash
uvicorn api_main:app --host 0.0.0.0 --port 8000
```

### Проверка работы сервиса

В **четвёртом терминале** выполните:

```bash
python verify_service.py
```

Результаты сохранятся в `service_test.log`.

## Архитектура системы

### Микросервисы

1. **api_main.py** (порт 8000) - главный сервис рекомендаций:
   - `/recommendations` - комбинированные рекомендации
   - `/recommendations_offline` - офлайн рекомендации
   - `/recommendations_online` - онлайн рекомендации

2. **similarity_store.py** (порт 8010) - сервис похожих треков:
   - `/similar_tracks` - получение похожих треков

3. **event_storage.py** (порт 8020) - история пользователя:
   - `/add_event` - добавление события
   - `/get_events` - получение последних событий

### Стратегия смешивания рекомендаций

Система комбинирует офлайн и онлайн рекомендации:
- **Офлайн**: персональные рекомендации на основе ALS + ранжирование
- **Онлайн**: рекомендации на основе последних прослушанных треков

Если у пользователя есть онлайн-история, рекомендации чередуются:
```
[online[0], offline[0], online[1], offline[1], ...]
```

Дубликаты удаляются с сохранением порядка.

## Технические детали

### Используемые модели

- **ALS** (Alternating Least Squares) - коллаборативная фильтрация для персональных рекомендаций
- **CatBoost** - ранжирующая модель с признаками:
  - `als_score` - оценка релевантности от модели ALS
  - `genre_name` - жанр трека (категориальный признак)
  - `genre_share` - доля жанра в обучающих взаимодействиях

### Метрики качества

- Precision@5 - доля релевантных рекомендаций среди топ-5
- Recall@5 - доля найденных релевантных треков среди всех релевантных
- Coverage - доля уникальных треков в рекомендациях от общего каталога
- Novelty@5 - средняя доля новых (непрослушанных ранее) треков в топ-5 рекомендациях

## Примеры API-запросов

### Получить рекомендации для пользователя

```bash
curl -X POST "http://localhost:8000/recommendations?user_id=123&k=10"
```

### Получить похожие треки

```bash
curl -X POST "http://localhost:8010/similar_tracks?track_id=456&k=5"
```

### Добавить событие прослушивания

```bash
curl -X POST "http://localhost:8020/add_event?user_id=123&track_id=789"
```

## Автор

Щербаков Дмитрий
