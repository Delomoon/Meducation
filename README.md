# CodeStars

Простой учебный сайт для школьников: регистрация, авторизация, уровни с управлением персонажем через команды Python-стиля.

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Откройте: `http://localhost:5000`

## Добавление нового уровня

Откройте `app.py` и добавьте словарь в список `LEVELS` с параметрами:

- `id`, `name`, `description`
- `width`, `height`
- `start`, `finish`
- `obstacles`
- `allowed_commands`
- `time_target_ms`
- `optimal_commands`

Уровни автоматически отображаются на главной странице.
