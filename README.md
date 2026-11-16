# Связка VPN: Россия + Зарубеж

Проект **настраивает два VPS** в связку: российский трафик — напрямую, остальное — через зарубежный сервер.

Конечный клиент будет подключаться к российскому серверу, а тот в свою очередь проксирует нужное на зарубежный. После первичного сетапа доступны два протокола: vless и wireguard

Нужны:

- **Docker** на вашем компьютере
- **Два VPS** (тестировалось на голой Ubuntu 26.04) - для 5 клиентов достаточно по 1GB RAM, 10GB Disk, 1 CPU:
  - У российского хостера с российским IP (например, tiмеwеb)
  - У зарубежного хостера (к примеру, webdock) - брать зарубежный сервер у российских хостеров можно, но не рекомендуется. Если есть возможность взять полностью зарубежный - лучше делать так
- **Домен** с двумя поддоменами и A-записи в DNS
- **Два Telegram-бота** — по одному для панели на RU и на world (уведомления 3X-UI)

Панель в интернет не выставлена — в неё заходят через SSH-туннель с вашего ПК.

После подключения проверьте маршрутизацию. 

В клиенте Happ иногда она не включается - включите принудительно и если произошел сбой при скачивании geoip и geosite - нажмите на скачивание вручную в клиенте.

Это позволит ходить на российские сайты и в приложения (для Android клиента Happ часть популярных приложений уже прилетает вместе с конфигурацией) напрямую с устройства, минуя VPN. Если не включать маршрутизацию на конечном устройстве, то базовая работает на российском сервере.

В остальных клиентах (не Happ) маршрутизацию придется настраивать вручную. Пример конфига можно посмотреть в [happ_routing.png](panel-setup/happ_routing.png)

---

## Подготовка

1. Два VPS и DNS на оба поддомена.
2. Скопируйте **`env/.env.example`** → **`env/.env`**, заполните домены, доступ к серверам, **`PANEL_PASSWORD`**, **`CADDY_DUMMY_BASIC_PASSWORD`**. Все переменные описаны в [.env.example](/env/.env.example)
3. Ключи SSH, если вход на сервера по ключам — в папку **`ssh/`**, имя в `.env` (как в примерах).
4. **Два бота в Telegram** (отдельные, не один на оба сервера):
   - В Telegram откройте [**@BotFather**](https://t.me/BotFather) → `/newbot` → придумайте имя и username → сохраните **токен**. Повторите для **второго** бота (ру и world).
   - Узнайте **свой** numeric ID: например через [@username_to_id_bot](https://t.me/username_to_id_bot) — он пойдёт в оба поля chat id, если вы единственный админ.
   - В **`env/.env`** заполните:
     - **`RU_SERVER_3X_TG_BOT_TOKEN`** и **`RU_SERVER_3X_TG_BOT_CHAT_ID`** — российская панель;
     - **`WORLD_SERVER_3X_TG_BOT_TOKEN`** и **`WORLD_SERVER_3X_TG_BOT_CHAT_ID`** — зарубежная панель.
   - После установки **напишите каждому боту** в личку в Telegram кнопкой «Start» / командой `/start` — иначе панель не сможет слать вам сообщения.
   - Если боты не нужны, оставьте токены пустыми — в шаблоне панели Telegram отключится (подробнее в [env/.env.example](env/.env.example)).

Не публикуйте **`env/.env`** и **`env/.env.secrets`** — там пароли и секреты, в том числе токены ботов.

---

## Запуск

Сначала один раз: **`make build`**. Далее всё делается одним плейбуком **`setup.yml`** через **`make setup`**.  

```bash
make build
make setup
```

Подробный вывод: `make setup opts="-v"`.
Только один сервер: `make setup limit="ru"` или `make setup limit="world"`.

---

### Частично — тегами

Формат: **`make setup tag=ИМЯ`**. Несколько тегов: `make setup tag=docker,ufw`.

#### Крупные этапы

| Тег | Что сделает |
|-----|-------------|
| *(без tag)* | Полная установка: серверы + секреты + 3X-UI + Caddy |
| `setup` | Всё кроме 3x-панели и caddy |
| `caddy` | Только Caddy на домене |
| `3x` | Секреты в `.env.secrets` и установка 3X-UI |

Панель заново из шаблона (**сбросит** настройки на сервере):

```bash
make setup tag="3x" regenerate_db=1
```

#### Базовая настройка сервера

| Тег | Что сделает |
|-----|-------------|
| `trash` | Удаление лишнего на сервере |
| `upgrade` | Обновление системы (возможна перезагрузка) |
| `python` | Python для задач Ansible на сервере |
| `docker` | Установка Docker |
| `dns` | DNS и связанные настройки |
| `sysctl` | Параметры сети в ядре |
| `ssh` | Смена SSH-порта (если задан новый порт в `.env`) |
| `ufw` | Фаервол и нужные порты |

Примеры:

```bash
make setup tag="docker"
make setup tag="ufw" limit="ru"
```

Произвольный плейбук/флаги (продвинутый вариант): `make run opts="setup.yml -v -t caddy"`.

---

## Ссылка для клиента (RU)

```bash
ssh -L 22000:127.0.0.1:22055 ваш_логин@ваш-домен-ru
```

Браузер: **http://localhost:22000/** — логин **`admin`**, пароль из **`PANEL_PASSWORD`**. Дальше — [panel-setup/ru](panel-setup/ru).

Ссылку можно вставлять в любой клиент, поддерживающий подписки. Например, Happ

---

## macOS

Понадобится:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Make** (`xcode-select --install` или `brew install make`)

Запуск: `make build` и `make setup`

---

## Ubuntu на вашем ПК

- [Docker Desktop](https://docs.docker.com/desktop/setup/install/linux/)
- Для Ubuntu и подобных систем может понадобиться дополнительно инициализировать хранилище секретов. Подробнее здесь: https://docs.docker.com/desktop/setup/sign-in/#credentials-management-for-linux-users . 

Запуск: `make build` и `make setup`

---

## Windows

1. Установите **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** и дождитесь, пока он запустится.
2. Склонируйте проект в обычную папку, например `C:\Users\user\3x-tandem`. Рядом должны лежать `env\.env` и при необходимости ключи в `ssh\`.
3. Откройте **PowerShell** или **Windows Terminal** в этой папке.

Сборка (один раз):

```powershell
docker compose build
```

Полная установка:

```powershell
docker compose run --rm --env-from-file .\env\.env --env-from-file .\env\.env.example ansible ansible-playbook -i inventory/vps.yml setup.yml
```

Частично — те же теги, что в разделе «Запуск» выше, через `-t` и при необходимости `--limit`:

```powershell
docker compose run --rm --env-from-file .\env\.env --env-from-file .\env\.env.example ansible ansible-playbook -i inventory/vps.yml setup.yml -t docker
docker compose run --rm --env-from-file .\env\.env --env-from-file .\env\.env.example ansible ansible-playbook -i inventory/vps.yml setup.yml -v
docker compose run --rm --env-from-file .\env\.env --env-from-file .\env\.env.example ansible ansible-playbook -i inventory/vps.yml setup.yml --limit ru
```

Пересоздать БД панели: `-t 3x -e regenerate_db=1`.

**Вход в панель** - встроенный SSH в PowerShell или Terminal:

```powershell
ssh -L 22000:127.0.0.1:22055 ваш_логин@ваш-домен-ru
```

Браузер: **http://localhost:22000/**

**SSH-ключ:** файл в `ssh\`, имя в `.env`. Если Ansible не может подключиться по ключу, задайте в `.env` вход по **паролю** — на Windows с ключами в Docker так бывает проще всего.

---

## Если что-то сломалось

| Ситуация | Действие |
|----------|----------|
| `no inventory was parsed` | Запускать команды **из корня проекта** (где `docker-compose.yml`), не забыть оба `--env-from-file`; в команде должно быть **`-i inventory/vps.yml`** (см. примеры в разделе Windows) |
| Нет доступа к VPS | Проверить `.env`, пинг/SSH с вашего ПК |
| Ключ SSH | Файл в `ssh/`, имя в `.env`; Linux/macOS: `chmod 600 ssh/имя_ключа`; Windows: при сбоях — пароль в `.env` |
| Нет секретов | `make setup tag=3x` или полный `make setup` |
| Упало на одном шаге | Исправить причину и снова **`make setup tag=...`** с тем же тегом |

`make run` без `opts` выдаст `Error: opts param required` — это нормально, для обычной работы используйте **`make setup`**.

Всегда можно удалить `/env/.env.secrets` и перезапустить заново:

```bash
make setup
```

или

```powershell
docker compose run --rm --env-from-file .\env\.env --env-from-file .\env\.env.example ansible ansible-playbook -i inventory/vps.yml setup.yml -v
```
