# Meducation (My Education)

Простой учебный сайт для учеников школ, ВУЗов, колледжей и т.п с учетными записями и уровнями на основе команд Python-стиля. Данный проект является *форком* другого проекта [CodeStars](https://github.com/KOPYTEL/-)

# Технологии
- Flask
- sqlalchemy

# Запуск

## Для UNIX-подобных систем
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
## Для Windows
```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
python app.py
```

# Добавление нового уровня

Откройте `app.py` и добавьте словарь в список `LEVELS` с параметрами:

- `id`, `name`, `description` 
- `width`, `height`
- `start`, `finish`
- `obstacles`
- `allowed_commands`
- `time_target_ms`
- `optimal_commands`

Уровни автоматически отображаются на главной странице.
