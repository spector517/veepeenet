# VeePeeNET

Язык: Русский | [English](README.en.md)

Установка и настройка персонального ускорителя интернета на базе [Xray](https://github.com/xtls/xray-core)

## Требования

1. Ubuntu Server 24.04+ (amd64)
2. Подключение к интернету

## Возможности

- Установка Xray
- Создание и изменение конфигурации Xray-сервера (Vless with Reality)
- Добавление и удаление клиентов Xray-сервера
- Управление исходящими подключениями Vless
- Гибкое управление правилами маршрутизации
- Обновление geodata для маршрутизации на основе geoip/geosite

## Установка
Скачайте и установите `.deb`-пакет:
```text
rm -rf /tmp/veepeenet \
    && mkdir /tmp/veepeenet \
    && (cd /tmp/veepeenet \
  && curl -LO https://github.com/spector517/veepeenet/releases/download/v2.5.1/veepeenet_2.5.1_amd64.deb \
  && sudo apt install -y ./veepeenet_2.5.1_amd64.deb
    )
```

## Использование

### Настройка сервера и добавление клиентов

Настройте Xray-сервер на хосте **my.domain.com**:
```commandline
sudo xrayctl config --host my.domain.com
```
Параметр `host` может быть **публичным** IP-адресом или доменным именем.
Лучше указывать его явно, так как автоматическое определение не всегда работает корректно, например за NAT.

Создайте клиентские конфигурации
**my_client1** и **my_client2**:
```commandline
sudo xrayctl clients add my_client1 my_client2
```

Первый запуск сервиса Xray:
```commandline
sudo xrayctl start
```

### Удаление клиентов

Удалите клиента **my_client2**:
```commandline
sudo xrayctl clients remove my_client2
```

### Просмотр клиентов

Показать всех клиентов вместе со ссылками для подключения:
```commandline
sudo xrayctl clients list
```

Показать клиентов в формате JSON:
```commandline
sudo xrayctl clients list --json
```

### Пересоздание конфигурации

Удалите текущую конфигурацию и создайте новую. Все клиенты будут удалены:
```commandline
sudo xrayctl config --host my.domain.com --clean
```

После этого добавьте новых клиентов:
```commandline
sudo xrayctl clients add new_client1
```

Перезапустите Xray, чтобы применить изменения:
```commandline
sudo xrayctl restart
```

### Справка

Показать расширенную справку:
```commandline
sudo xrayctl --help
```

### GUI-клиент
Для подключения к серверу можно использовать GUI-клиент [Happ](https://www.happ.su/main). Достаточно импортировать сгенерированную ссылку и подключиться.
Также подойдёт любой другой клиент, рекомендованный [проектом Xray](https://github.com/XTLS/Xray-core/blob/main/README.md#gui-clients)

## Команды

### Настройка Xray Vless-сервера с Reality
```
sudo xrayctl config [OPTIONS]
```

#### Параметры
| Параметр        | Тип     | Описание                                                                                                 |
| --------------- | ------- | -------------------------------------------------------------------------------------------------------- |
| --host          | TEXT    | Публичный интерфейс сервера. Если не указан, используется `hostname -i`. Рекомендуется задавать вручную. |
| --port          | INTEGER | Входящий порт. [default: 443]                                                                            |
| --reality-host  | TEXT    | Хост Reality. [default: microsoft.com]                                                                   |
| --reality-port  | INTEGER | Порт Reality. [default: 443]                                                                             |
| --reality-names | TEXT    | Доступные имена серверов Reality. [default: Reality host]                                                |
| --name          | TEXT    | Человекочитаемое имя сервера, используется после # в клиентских ссылках.                                 |
| --clean         | FLAG    | Перезаписать текущую конфигурацию. Все клиенты будут удалены. [default: no-clean]                       |

### Обновление geodata
```
sudo xrayctl update-geodata
```
Обновляет файлы `geoip.dat` и `geosite.dat`, которые используются в правилах геомаршрутизации.

### Обновление дистрибутива Xray
```
sudo xrayctl update-xray [OPTIONS]
```
Обновляет Xray до выбранной или последней доступной версии. Команда может показать список релизов с GitHub и дать выбрать нужную версию для установки.

#### Параметры

| Параметр | Тип     | Описание                                                |
| -------- | ------- | ------------------------------------------------------- |
| --version | TEXT    | Целевая версия, например v1.8.24 или 1.8.24             |
| --list    | FLAG    | Показать доступные версии и завершить работу            |
| --limit   | INTEGER | Сколько версий показать вместе с --list [default: 9]    |
| --json    |         | Вывести результат --list в формате JSON                 |

### Просмотр статуса сервиса Xray
```
sudo xrayctl status [OPTIONS]
```

#### Параметры

| Параметр | Тип  | Описание             |
| -------- | ---- | -------------------- |
| --json   | FLAG | Вывести в JSON-формате |

#### Примеры
```commandline
sudo xrayctl status
```
```
┌ [My Server] Xray server information ──────────────┐
│ status: stopped (disabled)                        │
│ uptime: n/a                                       │
│ xray_version: v25.12.8                            │
│ address: example.com:443                          │
│ reality_address: microsoft.com:443                │
│ reality_names: microsoft.com                      │
│ clients: Server has no clients                    │
│ rules: No routing rules configured                │
│ outbounds: freedom, blackhole                     │
└──────────────────────────────VeePeeNET v2.5.1─────┘
```

```commandline
sudo xrayctl status --json
```
```json
{
  "veepeenet_version": "v2.5.1",
  "veepeenet_build": 0,
  "xray_version": "v25.12.8",
  "server_status": "stopped",
  "enabled": false,
  "restart_required": false,
  "server_host": "example.com",
  "server_port": "443",
  "reality_address": "microsoft.com:443",
  "reality_names": ["microsoft.com"],
  "clients": {
    "clients": []
  },
  "routing": {},
  "outbounds": [
    {"name": "freedom"},
    {"name": "blackhole"},
    {"name": "dns"}
  ],
  "server_name": "My Server"
}
```

### Запуск, остановка, перезапуск и сброс статистики Xray
```commandline
sudo xrayctl start
```
```commandline
sudo xrayctl stop
```
```commandline
sudo xrayctl restart
```
```commandline
sudo xrayctl reset-stats
```

Команда `reset-stats` очищает накопленную статистику в секции `veepeenet.stats`.
Если сервис Xray запущен, статистика также сбрасывается через Xray API.

---

### Управление клиентами

#### Добавление клиентов
```commandline
sudo xrayctl clients add CLIENT_NAMES...
```
Если клиент с таким именем уже существует, он будет проигнорирован.

#### Удаление клиентов
Имена клиентов, которых нет на сервере, будут проигнорированы.
```commandline
sudo xrayctl clients remove CLIENT_NAMES...
```

#### Список клиентов
```text
sudo xrayctl clients list [OPTIONS]
```

| Параметр | Тип  | Описание             |
| -------- | ---- | -------------------- |
| --json   | FLAG | Вывести в JSON-формате |

---

### Управление исходящими подключениями

#### Добавление исходящего подключения Vless
```text
sudo xrayctl outbounds add NAME [OPTIONS]
```

| Параметр      | Тип     | Описание                                                     |
| ------------- | ------- | ------------------------------------------------------------ |
| --address     | TEXT    | Адрес исходящего подключения: IP или доменное имя. **(обязательно)** |
| --uuid        | TEXT    | Идентификатор Vless-клиента. **(обязательно)**               |
| --sni         | TEXT    | Имя сервера целевого узла. **(обязательно)**                 |
| --short-id    | TEXT    | Один из short_id целевого сервера. **(обязательно)**         |
| --password    | TEXT    | Публичный ключ целевого сервера. **(обязательно)**           |
| --spider-x    | TEXT    | Начальный путь и параметры для spider [default: /]           |
| --port        | INTEGER | Порт исходящего подключения Vless [default: 443]             |
| --fingerprint | TEXT    | Browser TLS Client Hello fingerprint [default: chrome]       |
| --interface   | TEXT    | Интерфейс для исходящего трафика [default: 0.0.0.0]          |

#### Добавление исходящего подключения Vless из URL
```text
sudo xrayctl outbounds add-from-url 'URL' [OPTIONS]
```

| Параметр  | Тип  | Описание                                                  |
| --------- | ---- | --------------------------------------------------------- |
| --name    | TEXT | Имя исходящего подключения. Если не указано, берётся фрагмент URL |
| --interface | TEXT | Интерфейс для исходящего трафика [default: 0.0.0.0]     |

#### Удаление исходящего подключения Vless
```commandline
sudo xrayctl outbounds remove NAME
```

#### Изменение исходящего подключения Vless
```text
sudo xrayctl outbounds change NAME [OPTIONS]
```

| Параметр      | Тип     | Описание                                                   |
| ------------- | ------- | ---------------------------------------------------------- |
| --address     | TEXT    | Адрес исходящего подключения: IP или доменное имя          |
| --uuid        | TEXT    | Идентификатор Vless-клиента                                |
| --sni         | TEXT    | Имя сервера целевого узла                                  |
| --password    | TEXT    | Публичный ключ целевого сервера                            |
| --short-id    | TEXT    | Один из short_id целевого сервера                          |
| --spider-x    | TEXT    | Начальный путь и параметры для spider                      |
| --port        | INTEGER | Порт исходящего подключения Vless                          |
| --fingerprint | TEXT    | Browser TLS Client Hello fingerprint [default: chrome]     |
| --interface   | TEXT    | Интерфейс для исходящего трафика [default: 0.0.0.0]        |
| --new-name    | TEXT    | Новое имя исходящего подключения                           |

#### Сделать исходящее подключение основным
```commandline
sudo xrayctl outbounds set-default NAME
```
Перемещает указанное исходящее подключение на первую позицию и делает его основным.

---

### Управление маршрутизацией

#### Список правил маршрутизации
```text
sudo xrayctl routing list [OPTIONS]
```

| Параметр | Тип  | Описание             |
| -------- | ---- | -------------------- |
| --json   | FLAG | Вывести в JSON-формате |

##### Пример
```commandline
xrayctl routing list
```
```
┌──────────────────────────────────────────┐
│ Domain strategy: AsIs                    │
└──────────────────────────────────────────┘
┌ Rule #10 block-ads --> blackhole ────────┐
│ name: block-ads                          │
│ domains: geosite:category-ads-all        │
└──────────────────────────────────────────┘
┌ Rule #20 bypass-ru --> freedom ──────────┐
│ name: bypass-ru                          │
│ domains: geosite:category-gov-ru         │
│ ips: geoip:ru                            │
└──────────────────────────────────────────┘
```

#### Добавление правила маршрутизации
```text
xrayctl routing add-rule NAME [OPTIONS]
```

| Параметр   | Тип     | Описание                                                            |
| ---------- | ------- | ------------------------------------------------------------------- |
| --outbound | TEXT    | Имя исходящего подключения, в которое будет направляться трафик. **(обязательно)** |
| --domain   | TEXT    | Список доменных шаблонов для совпадения, например "domain:example.com" |
| --ip       | TEXT    | Список IP-адресов или диапазонов, например "123.123.123.123"         |
| --ports    | TEXT    | Порт или диапазон портов, например "53,443,60-89"                    |
| --protocol | TEXT    | Список протоколов: http, tls, quic или bittorrent                    |
| --priority | INTEGER | Приоритет правила. Чем меньше значение, тем выше приоритет           |

Нужно указать хотя бы одно условие: `--domain`, `--ip`, `--ports` или `--protocol`.

#### Удаление правила маршрутизации
```commandline
sudo xrayctl routing remove-rule NAME
```

#### Переименование правила маршрутизации
```commandline
sudo xrayctl routing rename-rule NAME --new-name NEW_NAME
```

#### Изменение приоритета правила
```commandline
sudo xrayctl routing set-priority NAME --priority VALUE
```

#### Изменение условий правила
```text
sudo xrayctl routing change-rule NAME ACTION [OPTIONS]
```

Где `ACTION` может быть `put` (добавить значения) или `del` (удалить значения).

| Параметр   | Тип  | Описание                                                      |
| ---------- | ---- | ------------------------------------------------------------- |
| --domain   | TEXT | Список доменных шаблонов для добавления или удаления          |
| --ip       | TEXT | Список IP-адресов или диапазонов для добавления или удаления  |
| --ports    | TEXT | Порт или диапазон портов для добавления или удаления          |
| --protocol | TEXT | Список протоколов для добавления или удаления: http, tls, quic или bittorrent |

#### Установка domain strategy
```commandline
sudo xrayctl routing set-domain-strategy STRATEGY
```
Где `STRATEGY` — одно из доступных значений стратегии маршрутизации, например `AsIs`, `IPIfNonMatch` или `IPOnDemand`.

#### Изменение исходящего подключения у правила
```commandline
sudo xrayctl routing change-outbound NAME --outbound OUTBOUND_NAME
```
Меняет исходящее подключение, в которое направляется трафик по указанному правилу.

## Удаление

```commandline
sudo apt remove veepeenet
```

# Лицензия
MIT
