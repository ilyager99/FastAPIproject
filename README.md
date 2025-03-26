# FastAPIproject

Данный проект был выполнен при помощи FastAPI и деплой произовдился на render.

Малый сервис для сокращения ссылок с аутентификацией. Были реализованы несколько ручек, также работает система авторизации пользователя.

## Основные возможности
- Создание коротких ссылок
- Кастомные алиасы
- Кеширование в Redis
- Автоочистка старых ссылок

## Запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера
uvicorn main:app --reload
```

## После запуска доступна:

Swagger UI: http://localhost:8000/docs

## Ручки сервиса 

* POST /auth/register - регистрация пользователя 
* POST /auth/token - получение токена
* POST /links/shorten - создание короткой ссылки
* GET /links/myalias - переход по ссылки
* DELETE /links/myalias - удаление вашей ссылки

## Прикрепляю скрины

![аторизация](https://github.com/user-attachments/assets/2a96411e-3296-4d16-8315-e3b1c8d857a2)
![ручка1](https://github.com/user-attachments/assets/1deced13-ec8b-4ff6-b565-afb16c6dc44e)
![ручка2](https://github.com/user-attachments/assets/57ad82f5-6c30-4340-a68c-fc55b896b92f)
![ручка3](https://github.com/user-attachments/assets/de481ba6-d16a-4cca-9fc4-eb43d626b2cc)
![ручка 5](https://github.com/user-attachments/assets/95e501e4-4542-43db-8e75-8c35712dfe75)
![ручка6](https://github.com/user-attachments/assets/d9f73eb6-bfa4-47b4-9a95-2a3da3a3324a)

![рендер](https://github.com/user-attachments/assets/1a65b416-3bc8-4bec-8fa4-7dbae5afa896)
