# Oracle DEPLOY — пошаговая инструкция

Локальный MVP уже работает. Осталось 4 шага: GitHub repo → connect → Cloudflare Worker → Windows cron. Всё бесплатно. ~30-40 минут.

---

## Шаг 1: GitHub repo (5 мин)

1. Открой https://github.com/new
2. **Repository name:** `polymarket-oracle-feed` (или любое)
3. **Public** (обязательно — иначе raw.githubusercontent не отдаст файл)
4. **БЕЗ** README, .gitignore, license — у нас уже есть
5. Жми **Create repository**
6. На следующей странице скопируй URL вида `https://github.com/<твой_user>/polymarket-oracle-feed.git`

## Шаг 2: Push локального repo (2 мин)

В PowerShell:
```powershell
cd "C:\Users\icap\OneDrive\Рабочий стол\polymarket_monetization\oracle"

# ЗАМЕНИ <твой_user>
git remote add origin https://github.com/<твой_user>/polymarket-oracle-feed.git
git branch -M main
git push -u origin main
```

При первом push GitHub попросит логин/пароль. Используй **Personal Access Token** вместо пароля:
- https://github.com/settings/tokens → Generate new token (classic) → scope `repo` → копируй и вставь как пароль.
- Или установи [GitHub CLI](https://cli.github.com/) и `gh auth login` — проще.

После push проверь что snapshot виден:
```
https://raw.githubusercontent.com/<твой_user>/polymarket-oracle-feed/main/public/snapshot.json
```
Должен открыться JSON.

## Шаг 3: Cloudflare Worker (10 мин)

1. Зарегистрируйся: https://dash.cloudflare.com/sign-up (бесплатно, нужен только email)

2. В PowerShell:
   ```powershell
   cd "C:\Users\icap\OneDrive\Рабочий стол\polymarket_monetization\oracle"
   wrangler login
   ```
   Откроется браузер — авторизуй wrangler в Cloudflare.

3. Открой `worker.js` в редакторе. Замени строку 24:
   ```js
   const SNAPSHOT_URL = "https://raw.githubusercontent.com/<твой_user>/polymarket-oracle-feed/main/public/snapshot.json";
   ```
   на свой реальный URL (см. Шаг 2).

4. Деплой:
   ```powershell
   wrangler deploy
   ```
   Получишь URL вида `https://polymarket-oracle.<твой_handle>.workers.dev`

5. Проверь:
   ```
   https://polymarket-oracle.<твой_handle>.workers.dev/snapshot.json   ← должен открыть JSON
   https://polymarket-oracle.<твой_handle>.workers.dev/health           ← {"status":"ok",...}
   ```

6. Закоммить изменённый worker.js:
   ```powershell
   git add worker.js
   git commit -m "deploy: production SNAPSHOT_URL"
   git push
   ```

## Шаг 4: Windows Task Scheduler — cron каждую минуту (5 мин)

1. Открой **Task Scheduler** (Win+R → `taskschd.msc`)
2. **Create Task...** (НЕ Basic Task — нужны расширенные настройки)
3. **General:**
   - Name: `polymarket-oracle-update`
   - Run whether user is logged on or not — оставь как есть
   - ✅ **Run with highest privileges** (для надёжности)
4. **Triggers** → New:
   - Begin: **On a schedule**
   - **One time**, Start: текущее время
   - ✅ **Repeat task every: 1 minute**
   - For a duration of: **Indefinitely**
5. **Actions** → New:
   - Action: **Start a program**
   - Program: `powershell.exe`
   - Arguments:
     ```
     -NoProfile -ExecutionPolicy Bypass -File "C:\Users\icap\OneDrive\Рабочий стол\polymarket_monetization\oracle\update_and_push.ps1"
     ```
6. **Settings:**
   - ✅ Allow task to be run on demand
   - ❌ Stop the task if it runs longer than: **поставь 5 минут** (иначе зависнет навсегда)
   - If the task is already running: **Do not start a new instance**
7. OK → попросит пароль Windows-юзера (нужно)
8. Правый клик → **Run** — проверить запуск
9. Глянь лог: `oracle\logs\update_and_push.log`

Если push требует ввода пароля каждый раз — используй [git credential manager](https://github.com/git-ecosystem/git-credential-manager) (обычно идёт с Git for Windows) или ssh-ключ.

---

## После деплоя

Через 10-15 минут от первого push'а у тебя есть:

- ✅ **Public endpoint:** `https://polymarket-oracle.<handle>.workers.dev/snapshot.json`
- ✅ **Update freq:** 60 секунд
- ✅ **Подпись валидна** (проверяется `python -m oracle.verify_snapshot`)
- ✅ **CORS, кэш 30с, /health endpoint**
- ✅ **$0/мес**

Можно показывать prediction-протоколам как часть `M2 First Outreach` в TRACK_ORACLE.md.

---

## Чек-лист (вычёркивай по мере)

- [ ] GitHub repo создан и public
- [ ] `git push` прошёл, snapshot.json виден через raw.githubusercontent
- [ ] Cloudflare аккаунт создан
- [ ] `wrangler login` ОК
- [ ] `worker.js` обновлён правильным SNAPSHOT_URL и закоммичен
- [ ] `wrangler deploy` вернул *.workers.dev URL
- [ ] Endpoint `/snapshot.json` отдаёт JSON в браузере
- [ ] Task Scheduler настроен на 1 мин
- [ ] В `logs/update_and_push.log` через 2-3 минуты есть строка "push OK"
- [ ] Через 5-10 минут зашёл на endpoint — `generated_at_unix` обновился

---

## Что НЕ работает / частые проблемы

| Симптом | Причина | Решение |
|---|---|---|
| `git push` спрашивает пароль каждый раз | Нет credential helper | `git config --global credential.helper manager` или ssh-ключ |
| Worker отдаёт 502 upstream_unavailable | SNAPSHOT_URL неверный или repo private | Проверь URL в браузере. Repo обязан быть PUBLIC. |
| Endpoint отдаёт старый snapshot | Cloudflare кэширует 30с | Подожди или `?nocache=N` (Worker всё равно кэширует) |
| Task Scheduler ругается "Access denied" | Запуск под другим юзером | Run with highest privileges + правильный аккаунт |
| `wrangler deploy` ошибка quota | Превысил лимит free tier (вряд ли в первый день) | Подожди, или $5/мес paid |
