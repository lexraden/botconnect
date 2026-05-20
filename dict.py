MESSAGES = {
    "ru": {
        "start_message": (
            "👋 *Добро пожаловать в Bot Connect!*\n\n"
            "Это конструктор ботов обратной связи в Telegram. "
            "Смотрите подробную инструкцию [здесь](https://example.com).\n\n"
            "Добавьте своего бота чтобы начать!"
        ),
        "add_bot": "➕ Добавить бот",
        "my_bots": "📋 Мои боты",
        "help": "❓ Помощь",
        "ads": "📢 Реклама",
        "pro_subscription": "⭐ Bot Connect PRO",
        "add_bot_instructions": (
            "👨‍💻 *Чтобы подключить бот, Вам нужно выполнить два действия:*\n\n"
            "1️⃣ Перейдите в [@BotFather](https://t.me/BotFather) и создайте новый бот.\n"
            "2️⃣ После создания бота Вы получите токен (например, `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ12345678`) — скопируйте или перешлите его в этот чат.\n\n"
            "⚠️ *Важно:* Не подключайте ботов, используемых другими сервисами. Если уже подключили — отключите. "
        ),
        "invalid_token": "❌ Неверный токен или бот уже используется. Пожалуйста, проверьте токен.",
        "bot_connected": (
            "✅ Бот @{bot_username} успешно подключен к Bot Connect.\n\n"
            "📨 Отправьте боту любое сообщение и попробуйте ответить на него.\n\n"
            "📋 <b>Как отвечать на входящие сообщения?</b>\n"
            "Просто используйте функцию Ответить или двойной клик по сообщению.\n\n"
            "👥 <b>Как добавить администраторов в бот?</b>\n"
            "Создайте группу и добавьте туда подключенный бот — тогда все участники смогут отвечать на сообщения.\n\n"
            "🛠 <b>Как изменить приветственное сообщение?</b>\n"
            "Чтобы изменить приветствие, нажмите кнопку «Настроить бот» и перейдите в раздел «Приветствие».\n\n"
            "ℹ️ Если возникли вопросы, смотрите <a href='https://example.com'>видео инструкцию</a>."
        ),
        "configure_bot": "🛠 Настроить бота",
        "your_bots": "📋 Ваши боты:\n\nВыберите бота для настройки:",
        "no_bots": "🚫 У вас нет добавленных ботов.",
        "bot_button": "@{bot_username}",
        "error_user_not_found": " Пользователь не найден.",
        "subscription_bot": (
            "🎉 *Оформите подписку на бота и получите дополнительные преимущества!*\n\n"
            "🔹 *Что даёт подписка?*\n"
            "   • 🚫 Без рекламы – пользователи с подпиской не получают рекламные рассылки.\n"
            "   • 📈 Лимит сообщений увеличивается до 50,000 в день. \n"
            "   • 👨‍💻 Увеличивает количество одновременно возможных ботов для пользования\n\n"
            "🔹 *Зачем это нужно?*\n"
            "   Если ваш бот активно используется, подписка позволит отправлять"
            "   больше сообщений и поддерживать связь с аудиторией без ограничений.\n\n"
            "🔹 *Как оформить подписку?*\n"
            "   Выберите бота ниже и следуйте инструкциям.\n\n"
        ),
        "error_occurred": "Произошла ошибка. Пожалуйста, попробуйте позже.",
        "bot_not_found": "❌ Бот не найден.",
        "menu": "Кнопки",
        "mailings": "Рассылки",
        "statistics": "Статистика",
        "greeting": "Приветствие",
        "feedback": "Обратная связь",
        "disable_bot": "Отключить бота",
        "enable_bot": "Включить бота",
        "bot_management": "Управление ботом @{bot_username}.",
        "bot_statistics": (
            "📊 *Статистика бота\n@{bot_username}:*\n\n"
            "👥 *Пользователи:*\n"
            "   • Всего пользователей: {total_users}\n"
            "   • Заблокировали бот: {blocked_users}\n\n"
            "✉️ *Сообщения:*\n"
            "   • Всего сообщений: {sent_messages}\n"
            "   • Входящих: {incoming_messages}\n"
            "   • Ответов: {replied_messages}\n\n"
            "🚦 *Трафик:*\n"
            "   • Пользователей сегодня: {users_today}\n"
            "   • В этом месяце: {users_month}\n"
            "   • В этом году: {users_year}\n\n"
            "_Счетчик тех, кто заблокировал бот, обновляется после каждой рассылки._"
        ),
        "greeting_not_set": "Приветственное сообщение не установлено.",
        "current_greeting": "Выше указано ваше текущее приветственное сообщение:\n\nДля изменения отправьте новое приветствие. Бот поддерживает фото, видео и кругляшки.",
        "greeting_updated": "Приветственное сообщение успешно обновлено!",
        "bot_disable_error": "⚠️ Ошибка при отключении бота: {error}",
        "bot_already_active": "⚠️ Бот @{bot_username} уже включен.",
        "bot_activate_error": "⚠️ Ошибка при запуске бота: {error}",
        "new_chat": "Новый чат",
        "disable_chats": "Отключить чаты",
        "feedback_description": (
            "Новый чат — подключить бота к закрытому чату, чтобы все сообщения пересылались туда. "
            "Вы сможете добавить туда сотрудников и создать полноценную техподдержку."
        ),
        "add_button": "➕",
        "main_menu_description": (
            "Здесь вы можете настроить кнопки для бота. Они будут отображаться после команды */start* или привязываться к другим кнопкам и командам.\n\n"
            "Создавайте, комбинируйте и прикрепляйте кнопки к сообщениям, командам или другим кнопкам.\n\n"
            "Нажмите на ➕, чтобы добавить новую кнопку."
        ),
        "bot_connected_to_chat": "Бот успешно подключен к чату!",
        "mailing_start": "📨 Настройка рассылки...",
        "mailing_statistics": (
            "Выберите рассылку из списка или создайте новую.\n\n"
            "📨 *Рассылки:*\n"
            "   • Запланировано сегодня: {scheduled_today}, всего: {total_scheduled}\n"
            "   • Завершено сегодня: {completed_today}, всего: {total_completed}\n\n"
            "👥 *Аудитория:*\n"
            "   • Всего пользователей: {total_users}\n"
            "   • Пользователей заблокировавших бот: {blocked_users}\n\n"
            "✉️ *Лимиты:*\n"
            "   • Лимит отправки: {daily_limit} сбщ./сутки\n"
            "   • Отправлено сегодня: {sent_today} сбщ.\n"
            "   • Можно отправить сегодня: {remaining_limit} сбщ.\n\n"
            "Начало дня отсчитывается по МСК (UTC+3)."
        ),
        "create_mailing": "Создать рассылку",
        "scheduled": "Запланировано",
        "default_greeting": "Приветственное сообщение не установлено.",
        "send": "Отправить",
        "schedule": "Запланировать",
        "confirm_mailing": (
            "↑ Сообщение для рассылки находится над этим текстом. ↑\n\n"
            "Вы уверены, что хотите отправить его вашим пользователям?"
        ),
        "daily_limit_reached": (
            "Лимит отправки {user_limit} сообщений в сутки исчерпан. "
            "Вы уже отправили {sent_today_count} сообщений."
        ),
        "mailing_finished": (
            "Рассылка завершена.\n"
            "Успешно отправлено: {success_count} пользователям.\n"
            "Бота заблокировали: {blocked_users_count} пользователей."
        ),
        "schedule_mailing_prompt": (
            "Напишите время (по МСК), в которое необходимо выложить пост, в любом из следующих форматов:\n\n"
            "```\n"
            "03:28\n"
            "03 28\n"
            "03:28 11.01\n"
            "03 28 11 01\n"
            "03:28 11.01.2025\n"
            "2025-01-11 03:28\n"
            "```"
        ),
        "mailing_content_error": "Контент для рассылки не найден.",
        "schedule_mailing_error": (
            "Неверный формат времени.\n"
            "Примеры:\n"
            "03:28\n"
            "03 28\n"
            "03:28 11.01\n"
            "03 28 11 01\n"
            "03:28 11.01.2025\n"
            "2025-01-11 03:28"
        ),
        "schedule_time_past_error": "Указанное время должно быть в будущем.",
        "bot_not_found": "Бот не найден.",
        "schedule_limit_exceeded": (
            "Рассылка превышает дневной лимит сообщений.\n"
            "Лимит: {daily_limit}, Запланировано на {target_date}: {sent_on_target_date}, "
            "Доступно для рассылки: {available_users}."
        ),
        "schedule_success": "Рассылка успешно запланирована на {scheduled_time} (МСК).",
        "send_mailing_message": "📨 Пришлите сообщение, которое нужно отправить пользователям бота.",
        "no_scheduled_mailings": "Нет запланированных рассылок.",
        "scheduled_mailings": "Запланированные рассылки:",
        "edit_mailing_error": "Ошибка: рассылка не найдена.",
        "mailing_info": (
            "📨 *Информация о рассылке:*\n"
            "ID: `{mailing_id}`\n"
            "Тип: `{mailing_type}`\n"
            "Время: `{scheduled_time}`\n\n"
        ),
        "cancel_mailing": "🗑️ Отменить рассылку",
        "mailing_not_found": "Рассылка не найдена.",
        "mailing_deleted": "Рассылка успешно отменена.",
        "regular_button": "Обычная",
        "inline_button": "Inline",
        "add_button_instructions": (
            "Здесь вы можете добавить кнопки в Главное меню.\n\n"
            "Выберите тип новой кнопки:\n\n"
            "*Обычная* — находится в блоке меню снизу и содержит текст, медиа или ссылку на другое меню.\n\n"
            "*Inline* — отображается под сообщениями, может вести на ссылку, заменять текущее сообщение или содержать текст, медиа и меню."
        ),
        "enter_button_name": "Введите название кнопки:",
        "inline_type_link": "Переход по ссылке",
        "inline_type_replace": "Замена текущего сообщения",
        "inline_type_new": "Отправка нового сообщения",
        "select_inline_type": "Выберите тип inline кнопки:",
        "subscription_already_active": "У вас уже есть активная подписка на этого бота до {end_date}.",
        "month": "месяц",
        "month3": "месяца",
        "months": "месяцев",
        "rub": "руб.",
        "back": "<- Назад",
        "choose_subscription_duration": "Выберите длительность подписки:",
        "subscription_selected": "Вы выбрали подписку на {duration} за {price}.",
        "choose_payment_method": "Выберите метод оплаты:",
        "pay_via_telegram_stars": "⭐️ Telegram Звёзды",
        "pay_via_crypto_bot": "Оплата Криптой",
        "invalid_subscription_choice": " Неверный выбор подписки.",
        "payment_initiated": "Ссылка на оплату успешно создана. Перейдите по ссылке, чтобы завершить оплату:",
        "payment_failed": " Не удалось выполнить оплату. Пожалуйста, попробуйте еще раз.",
        "payment_successful": "Оплата успешно завершена. Вы подписались на бота {bot_username} до {end_date}.",
        "invoice_not_found": "Счет на оплату не найден. Запись удалена из ожидания платежей.",
        "enter_reply_message": (
            "Введите сообщение, которое будет отправляться при нажатии на кнопку:"
        ),
        "enter_reply_link": "Введите ссылку для кнопки",
        "button_not_found": "Кнопка не найдена.",
        "edit_button": "✏️ Редактировать",
        "delete_button": "🗑 Удалить",
        "button_message": "Сообщение кнопки сверху\n\nКнопка: {button_text}\n\n",
        "attach_button": "Прикрепить к другой",
        "detach_start": "Открепить от старта",
        "attach_start": "Прикрепить к старту",
        "rename_button": "Изменить название",
        "update_content": "Изменить содержание",
        "edit_button_prompt": "Что вы хотите сделать с этой кнопкой?",
        "current_button_not_found": "Ошибка: текущая кнопка не найдена.",
        "detach_button": "Отвязать кнопку",
        "attach_button_instructions": (
            "Когда вы крепите одну кнопку к другой, кнопка, которую вы прикрепили, будет вызываться вместе с сообщением кнопки, "
            "к которой вы прикрепили эту.\n\n"
            "Учтите, что можно крепить inline-кнопку к обычной, но в этом случае все остальные кнопки также должны быть inline, и наоборот с обычными кнопками.\n\n"
            "Также, нельзя крепить кнопки к кнопкам в сообщении которых содержится несколько медиа (фотографий, видео, аудио или документов).\n\n"
            "А также нельзя крепить обычную кнопку к кнопке, которая редактирует сообщение.\n\n"
            "Выберите, к какой кнопке вы хотите прикрепить эту:"
        ),
        "enter_new_button_name": "Введите новое название для кнопки:",
        "send_new_content": "Отправьте новое содержание для кнопки: текст, медиа или медиа-группу.",
        "button_display_message": "Кнопка: {button_text}\n\nСообщение кнопки сверху",
        "ad_content_missing": "Контент для рассылки не найден.",
        "ad_sent_success": "✅ Рассылка успешно отправлена от всех ботов без подписки.",
        "bot_connected_but_not_activated": (
            "⚠️ Бот @{bot_username} был добавлен, но не активирован, так как достигнут лимит активных ботов.\n\n"
            "Вы можете отключить одного из ваших ботов или оформить подписку для увеличения лимита активных ботов"
        ),
        "subscription_expired": "⚠️ Подписка на PRO для вашего бота @{bot_username} истекла. Пожалуйста, продлите подписку, чтобы продолжить использование всех возможностей.",
        "ads_message": (
            "📢 *Реклама*\n"
            "Ваш рекламный пост будет отправлен всем пользователям ботов, созданных через наш сервис, не имеющих подписку.\n\n"
            "📨 *Что нужно сделать?*\n"
            "Отправьте текст рекламного сообщения. После проверки модератором мы свяжемся с вами, чтобы обсудить детали размещения и цену.\n\n"
            "💡 *Примечание:*\n"
            "Мы следим за качеством рекламы, поэтому не размещаем запрещенные вещества, 18+ контент, скам-проекты. Также запрещена ненормативная лексика."
        ),
        "empty_ad_post": "⚠️ Пожалуйста, отправьте текст для рекламного поста.",
        "ad_post_received": "✅ Ваш рекламный пост успешно отправлен на проверку. Мы свяжемся с вами для уточнения деталей.",
        "ad_post_error": "❌ Произошла ошибка при отправке рекламного поста. Попробуйте позже.",
        "link_to_command_instruction": "Напишите команду, к которой вы хотите привязать эту кнопку (кроме команды /start).\n\nСообщение должает начинаться с /",
        "command_not_allowed": "⚠️ Команда /start не может быть использована для привязки кнопки.",
        "command_saved": "✅ Команда `{command}` успешно привязана к кнопке.",
        "command_type_mismatch": "Команда уже привязана к кнопке другого типа. Проверьте настройки и повторите попытку.",
        "link_to_command": "Привязать к команде",
        "bot_settings_description": "Выберите меню, которое хотели бы открыть:",
        "bot_settings": "Настройки бота",
        "where_to_attach": "Выбрите куда хотите привязать кнопку",
        "back_to_start": "Вернуться в главное меню",
        "add_button_greetings": "Добавить кнопку",
        "button_added": "Кнопка успешно добавлена",
        "chat_unbound": "Чат успешно отключен. Сообщения больше не будут пересылаться в него.",
        "help_button": "По всем вопросам пишите в [бот поддержки](https://t.me/botconnect_sup_bot).\n\nТак же можете посмотреть [видео-инструкцию](https://example.com) для наглядного объяснения.",
        "pay_subscription": "Оформить подписку",
        "bot_activation_limit_exceeded": (
            "⚠️ *Превышен лимит активных ботов!* \n\n"
            "Вы можете активировать не более {limit} ботов одновременно. "
            "Чтобы добавить новый бот, отключите один из текущих или оформите подписку для увеличения лимита.",
        ),
        "channels": "Каналы",
        "channels_message": (
            "В данном разделе вы можете настроить авто-принятие заявок на ваш канал\n"
            "Для того чтобы настроить бота на принятие заявок, необходимо добавить бота в администраторы канала\n\n"
            "⚠️ *ОЧЕНЬ ВАЖНО*\n\n"
            "Необходимо разрешить боту только следующую функцию:\n"
            "```\nПригласительные ссылки ✅```\n"
            "Добавьте бота в канал и после этого вам будут доступны его настройки"
        ),
        "enter_url_button_data": (
            "Введите данные кнопки в формате:\n"
            "Текст кнопки | URL\n"
            "Пример: Посетить сайт | https://example.com" 
        ),
        "invalid_url_format": "Неверный формат! Используйте: Текст кнопки | URL",
        "skip": "Без URL",
        "captcha_message": "Для принятия в канал {channel_name}, пожалуйста, пройдите верификацию",
        "not_robot": "Я не робот ✅",
        "captcha_settings": "⚙️ Настроить текст капчи",
        "captcha_text_prompt": "Введите новый текст для кнопки капчи:",
        "captcha_text_updated": "✅ Текст капчи обновлён!",
        "captcha_current_text": "Текущий текст кнопки: {text}",
        "user_access": "Прием заявок",
        "channel_greetings_settings": "Настроить приветствие",
        "channel_farewell_settings": "Настроить прощание",
        "delete_channel": "Удалить канал",
        "channel_greetings_settings_message": "Настройки приветственных сообщений:",
        "channel_farewell_settings_message": "Настройки прощаний:",
        "message_to_send": "Пожалуйста отправьте сообщение которое хотите отправлять пользователям\n\nК сообщениям медиа-группам(Где есть несколько аудио, фото и т.д) нельзя прикрепить URL-кнопки",
        "edit_url_buttons_message": "Добавить URL кнопки",
        "choose_message_language": "Выберите для какого языка пользователей будет отправляться сообщение",
        "change_message_lang": "Язык: {language}",
        "change_message_content": "Изменить контент сообщения",
        "delete_channel_message": "🗑️Удалить",
        "channel_settings_text": (
            "Настройки канала {channel_name}\n\n"
            "В данном меню вы можете настроить поведение бота при работе с каналами"
        ),
        "user_access_enabled": "✅ Авто-принятие заявок",
        "user_access_disabled": "❌ Авто-принятие заявок",
        "captha_enabled": "✅ Капча",
        "captha_disabled": "❌ Капча",
        "message_settings": (
            "📨 *Настройка сообщения*\n"
            "*{channel_name}*\n"
            "Язык: {language}\n"
            "Тип: {message_type}"
            ),
        "user_access_text": (
            "📨 *Прием заявок*\n"
            "*{channel_name}*\n\n"
            "Прием заявок: {user_access}\n"
            "Капча: {captcha}"
            ),
        "greetings": "Приветствие",
        "farewell": "Прощание",
        "message_buttons_settings": (
            "*Настройка кнопок*\n"
            "В данном разделе вы можете прикрепить URL-Кнопки к сообщению\n"
            "Пришлите кнопки сообщением в следующем формате\n\n"
            "Название кнопки1 - URL\n"
            "Название кнопки2 - URL\n\n"
            "Если вы хотите добавить 2 кнопоки в одну строку то используйте `|`\n\n"
            "Например:\n"
            "Название кнопки1 - URL | Название кнопки2 - URL\n"
            "Название кнопки3 - URL | Название кнопки4 - URL\n"
            ),
        "delete_url_buttons_message": "Удалить кнопки",
        "current_language": "Текущий язык сообщения: {language} ({code})\nВыберите новый язык:",
        "language_changed": "Язык сообщения изменен на {language} ({code})",
        "set_language_ru": "🇷🇺 Русский",
        "set_language_en": "🇬🇧 Английский",
        "set_language_all": "🌐 Все языки",
        "setup_channel": "Настроить канал",
        "deleted_channel": "Канал {channel_name} был удален",
        "change_message_content_text": "Пришлите новое сообщение для замены старого\n\nЕсли вы меняете сообщение где было 1 медиа на сообщение с несколькими медиа то URL-кнопки для этого сообщения не будут отображаться",
        "bot_added_to_channel": "🎉 Бот был добавлен в канал *{channel_name}*!\n",
        "bot_removed_from_channel": "😢 Бот был удален из канала *{channel_name}*!\n",
        "user_joined_channel": "Вы зашли в канал {channel_name}",
        "user_leaved_channel": "Вы ушли из канала {channel_name}",
        "bot_deleted_message": "Бот {bot_name} был удален",
        "bot_delete_asnwer": "Вы уверены что хотите удалить бота {bot_name}?\n\n",
        "bot_has_subscription": "У вас есть подписка на этого бота если вы удалите бота то и подписка пропадет вместе с ним",
        "accept_bot_delete": "✅ Уверен",
        "bot_delete_button": "🗑️ Удалить бота",
        "export_users": "📥 Экспорт пользователей"
    },
    "en": {
        "user_leaved_channel": "You leaved channel {channel_name}",
        "user_joined_channel": "You have joined the channel {channel_name}",
        "bot_added_to_channel": "🎉 Bot has been added to channel *{channel_name}*!\n",
        "bot_removed_from_channel": "😢 Bot has been removed from channel *{channel_name}*!\n",
        "user_access": "Request Handling",
        "channel_greetings_settings": "Configure Greeting",
        "channel_farewell_settings": "Configure Farewell",
        "delete_channel": "Delete Channel",
        "channel_settings_text": (
            "Channel Settings {channel_name}\n\n"
            "In this menu, you can configure the bot's behavior when working with channels."
        ),
        "channel_greetings_settings_message": "Greeting message settings:",
        "channel_farewell_settings_message": "Farewell message settings:",
        "message_to_send": "Please send the message you want to send to users.\n\nURL buttons cannot be attached to media group messages (where there are multiple audio, photos, etc.).",
        "edit_url_buttons_message": "Add URL buttons",
        "choose_message_language": "Select the language for which the message will be sent.",
        "change_message_lang": "Language: {language}",
        "change_message_content": "Edit message content",
        "delete_channel_message": "🗑️ Delete",
        "user_access_enabled": "✅ Auto-accept requests",
        "user_access_disabled": "❌ Auto-accept requests",
        "captha_enabled": "✅ Captcha",
        "captha_disabled": "❌ Captcha",
        "message_settings": (
            "📨 *Message Settings*\n"
            "*{channel_name}*\n"
            "Language: {language}\n"
            "Type: {message_type}"
        ),
        "user_access_text": (
            "📨 *Request Handling*\n"
            "*{channel_name}*\n\n"
            "Request handling: {user_access}\n"
            "Captcha: {captcha}"
        ),
        "greetings": "Greeting",
        "farewell": "Farewell",
        "message_buttons_settings": (
            "*Button Configuration*\n"
            "In this section, you can attach URL buttons to the message.\n"
            "Send the buttons in the following format:\n\n"
            "Button Name 1 - link\n"
            "Button Name 2 - link\n\n"
            "If you want to add two buttons in one row, use `|`\n\n"
            "For example:\n"
            "Button Name 1 - link | Button Name 2 - link\n"
            "Button Name 3 - link | Button Name 4 - link\n"
        ),
        "delete_url_buttons_message": "Delete buttons",
        "current_language": "Current message language: {language} ({code})\nSelect a new language:",
        "language_changed": "Message language changed to {language} ({code}).",
        "set_language_ru": "🇷🇺 Russian",
        "set_language_en": "🇬🇧 English",
        "set_language_all": "🌐 All languages",
        "not_robot": "I'm not a robot ✅",
        "captcha_settings": "⚙️ Configure captcha text",
        "captcha_text_prompt": "Enter new text for the captcha button:",
        "captcha_text_updated": "✅ Captcha text updated!",
        "captcha_current_text": "Current button text: {text}",
        "captcha_message": "To be accepted into the channel {channel_name}, please confirm the verification",
        "enter_url_button_data": (
            "Enter the button data in the format:\n"
            "Button Text | URL\n"
            "Example: Visit Website | https://example.com"
        ),
        "invalid_url_format": "Invalid format! Use: Button Text | URL",
        "skip": "Without URL",
        "channels_message": (
            "In this section, you can configure the auto-approval of requests to your channel.\n"
            "To set up the bot for request approval, you need to add the bot as an administrator to the channel.\n\n"
            "⚠️ *VERY IMPORTANT*\n\n"
            "You must grant the bot only the following permission:\n"
            "```\nInvite links ✅```\n"
            "Add the bot to the channel, and after that, its settings will be available to you."
        ),
        "channels": "Channels",
        "bot_activation_limit_exceeded": (
            "⚠️ *The active bot limit has been exceeded!* \n\n"
            "You can activate up to {limit} bots at the same time."
            "To add a new bot, deactivate one of the current ones or subscribe to increase the limit."
        ),
        "pay_subscription": "Subscribe",
        "month": "month",
        "help_button": "For any questions, please contact the [support bot](https://t.me/botconnect_sup_bot).\n\nYou can also watch the [video tutorial](https://example.com) for a visual explanation.",
        "chat_unbound": "Chat has been successfully disabled. Messages will no longer be forwarded to it.",
        "button_added": "Button was succesfully added",
        "add_button_greetings": "Add Button",
        "back_to_start": "Back to start menu",
        "where_to_attach": "Choose where attach button to",
        "bot_settings": "Bot Settings",
        "bot_settings_description": "Choose the menu you want to open:",
        "link_to_command": "Link To Command",
        "command_type_mismatch": "The command is already linked to a button of a different type. Please check settings and try again.",
        "command_not_allowed": "⚠️ The /start command cannot be used for button linking.",
        "command_saved": "✅ The command `{command}` has been successfully linked to the button.",
        "link_to_command_instruction": "Please enter the command you want to link this button to (excluding the /start command).\n\nMessage must starts with /",
        "empty_ad_post": "⚠️ Please send the text for the advertisement post.",
        "ad_post_received": "✅ Your advertisement post has been successfully sent for review. We will contact you to clarify the details.",
        "ad_post_error": "❌ An error occurred while sending the advertisement post. Please try again later.",
        "ads_message": (
            "📢 *Advertisement*\n"
            "Your promotional post will be sent to all users of bots created through our service who do not have a subscription.\n\n"
            "📨 *What do you need to do?*\n"
            "Send the text of your promotional message. After moderation, we will contact you to discuss the placement details and pricing.\n\n"
            "💡 *Note:*\n"
            "We monitor the quality of advertisements, so we do not allow prohibited substances, 18+ content, scam projects, or any inappropriate language."
        ),
        "subscription_expired": "⚠️ The PRO subscription for your bot @{bot_username} has expired. Please renew your subscription to continue using all features.",
        "bot_connected_but_not_activated": (
            "⚠️ Bot @{bot_username} was added but not activated because the active bot limit has been reached. "
            "You can disable one of your bots or subscribe to increase the limit of active bots."
        ),
        "ad_content_missing": "Ad content not found.",
        "ad_sent_success": "✅ The ad has been successfully sent from all bots without a subscription.",
        "button_display_message": "Button: {button_text}\n\nButton message above",
        "send_new_content": "Send new content for the button: text, media, or a media group.",
        "enter_new_button_name": "Enter a new name for the button:",
        "current_button_not_found": "Error: the current button was not found.",
        "detach_button": "Detach button",
        "attach_button_instructions": (
            "When you attach one button to another, the button you attached will be triggered along with the message "
            "of the button you attached it to.\n\n"
            "Note that you can attach an inline button to a regular button, but in this case, all other buttons must also be inline, and vice versa.\n\n"
            "Also, you cannot attach buttons to buttons whose messages contain multiple media files (photos, videos, audio, or documents).\n\n"
            "Additionally, a regular button cannot be attached to a button that edits a message.\n\n"
            "Choose the button to which you want to attach this one:"
        ),
        "attach_button": "Attach to another",
        "detach_start": "Detach from start",
        "attach_start": "Attach to start",
        "rename_button": "Rename",
        "update_content": "Update content",
        "edit_button_prompt": "What would you like to do with this button?",
        "button_not_found": "Button not found.",
        "edit_button": "✏️ Edit",
        "delete_button": "🗑 Delete",
        "button_message": "Message from the button above\n\nButton: {button_text}\n\n",
        "enter_reply_message": (
            "Enter the message to be sent when the button is clicked:"
        ),
        "enter_reply_link": "Enter link for button",
        "start_message": (
            "👋 *Welcome to Bot Connect!*\n\n"
            "This is a Telegram feedback bot constructor. "
            "Check out the detailed instructions [here](https://example.com).\n\n"
            "Add your bot to get started!"
        ),
        "add_bot": "➕ Add Bot",
        "my_bots": "📋 My Bots",
        "help": "❓ Help",
        "ads": "📢 Ads",
        "pro_subscription": "⭐ Bot PRO",
        "add_bot_instructions": (
            "👨‍💻 *To connect a bot, you need to perform two steps:*\n\n"
            "1️⃣ Go to [@BotFather](https://t.me/BotFather) and create a new bot.\n"
            "2️⃣ After creating the bot, you will receive a token (e.g., `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ12345678`) — copy or forward it to this chat.\n\n"
            "⚠️ *Important:* Do not connect bots used by other services. If you have already connected one — disconnect it."
        ),
        "invalid_token": "❌ Invalid token or the bot is already in use. Please check the token.",
        "bot_connected": (
            "✅ Bot @{bot_username} has been successfully connected to Bot Connect.\n\n"
            "📨 Send any message to the bot and try replying to it.\n\n"
            "📋 <b>How to reply to incoming messages?</b>\n"
            "Simply use the Reply function or double-click on the message.\n\n"
            "👥 <b>How to add administrators to the bot?</b>\n"
            "Create a group and add the connected bot there — then all members will be able to reply to messages.\n\n"
            "🛠 <b>How to change the welcome message?</b>\n"
            "To change the greeting, click the «Configure Bot» button and go to the «Greeting» section.\n\n"
            "ℹ️ If you have any questions, check out the <a href='https://example.com'>video tutorial</a>."
        ),
        "configure_bot": "🛠 Configure Bot",
        "your_bots": "📋 Your bots:\n\nSelect a bot to configure:",
        "no_bots": "🚫 You don't have any added bots.",
        "bot_button": "@{bot_username}",
        "error_user_not_found": "User not found.",
        "subscription_bot": (
            "🎉 *Subscribe to the bot and get additional benefits!*\n\n"
            "🔹 *What does the subscription offer?*\n"
            "   • 🚫 No ads – users with a subscription won’t receive promotional messages.\n"
            "   • 📈 Message limit increases to 50,000 per day.\n"
            "   • 👨‍💻 Increases the number of bots you can use simultaneously.\n\n"
            "🔹 *Why is this important?*\n"
            "   If your bot is actively used, the subscription will allow you to send more messages "
            "   and maintain communication with your audience without restrictions.\n\n"
            "🔹 *How to subscribe?*\n"
            "   Select a bot below and follow the instructions.\n\n"
                    ),
        "back": "<- Back",
        "error_occurred": "An error occurred. Please try again later.",
        "bot_not_found": "❌ Bot not found.",
        "menu": "Buttons",
        "mailings": "Mailings",
        "statistics": "Statistics",
        "greeting": "Greeting",
        "feedback": "Feedback",
        "disable_bot": "Disable Bot",
        "enable_bot": "Enable Bot",
        "bot_management": "Managing bot @{bot_username}.",
        "bot_statistics": (
            "📊 *Statistics for bot\n@{bot_username}:*\n\n"
            "👥 *Users:*\n"
            "   • Total users: {total_users}\n"
            "   • Blocked bot: {blocked_users}\n\n"
            "✉️ *Messages:*\n"
            "   • Total messages: {sent_messages}\n"
            "   • Incoming: {incoming_messages}\n"
            "   • Replies: {replied_messages}\n\n"
            "🚦 *Traffic:*\n"
            "   • Users today: {users_today}\n"
            "   • This month: {users_month}\n"
            "   • This year: {users_year}\n\n"
            "_The counter for users who blocked the bot is updated after each mailing._"
        ),
        "greeting_not_set": "Greeting message is not set.",
        "current_greeting": "Here is your current welcome message:\n\nTo change it, send a new greeting. The bot supports photos, videos, and video-notes.",
        "greeting_updated": "Greeting message successfully updated!",
        "bot_disable_error": "⚠️ Error disabling bot: {error}",
        "bot_already_active": "⚠️ Bot @{bot_username} is already active.",
        "bot_activate_error": "⚠️ Error activating bot: {error}",
        "new_chat": "New Chat",
        "disable_chats": "Disable Chats",
        "feedback_description": (
            "New chat — connect the bot to a private chat to forward all messages there. "
            "You can add employees to the chat and create a full-fledged support team."
        ),
        "add_button": "➕",
        "main_menu_description": (
            "Here you can configure buttons for the bot. They will be displayed after the */start* command or attached to other buttons and commands.\n\n"
            "Create, combine, and attach buttons to messages, commands, or other buttons.\n\n"
            "Click on ➕ to add a new button."
        ),
        "bot_connected_to_chat": "The bot has been successfully connected to the chat!",
        "mailing_start": "📨 Setting up the mailing...",
        "mailing_statistics": (
            "Select a mailing from the list or create a new one.\n\n"
            "📨 *Mailings:*\n"
            "   • Scheduled today: {scheduled_today}, total: {total_scheduled}\n"
            "   • Completed today: {completed_today}, total: {total_completed}\n\n"
            "👥 *Audience:*\n"
            "   • Total users: {total_users}\n"
            "   • Users who blocked the bot: {blocked_users}\n\n"
            "✉️ *Limits:*\n"
            "   • Daily sending limit: {daily_limit} msgs./day\n"
            "   • Sent today: {sent_today} msgs.\n"
            "   • Remaining today: {remaining_limit} msgs.\n\n"
            "The day starts at MSK (UTC+3)."
        ),
        "create_mailing": "Create mailing",
        "scheduled": "Scheduled",
        "default_greeting": "Default greeting is not set.",
        "send": "Send",
        "schedule": "Schedule",
        "confirm_mailing": (
            "↑ The message for the mailing is above this text. ↑\n\n"
            "Are you sure you want to send it to your users?"
        ),
        "daily_limit_reached": (
            "The daily limit of {user_limit} messages has been reached. "
            "You have already sent {sent_today_count} messages."
        ),
        "mailing_finished": (
            "Mailing completed.\n"
            "Successfully sent to: {success_count} users.\n"
            "Bot was blocked by: {blocked_users_count} users."
        ),
        "schedule_mailing_prompt": (
            "Specify the time (in MSK) for posting in any of the following formats:\n\n"
            "```\n"
            "03:28\n"
            "03 28\n"
            "03:28 11.01\n"
            "03 28 11 01\n"
            "03:28 11.01.2025\n"
            "2025-01-11 03:28\n"
            "```"
        ),
        "mailing_content_error": "Mailing content not found.",
        "schedule_mailing_error": (
            "Invalid time format.\n"
            "Examples:\n"
            "03:28\n"
            "03 28\n"
            "03:28 11.01\n"
            "03 28 11 01\n"
            "03:28 11.01.2025\n"
            "2025-01-11 03:28"
        ),
        "schedule_time_past_error": "Specified time must be in the future.",
        "bot_not_found": "Bot not found.",
        "schedule_limit_exceeded": (
            "The mailing exceeds the daily message limit.\n"
            "Limit: {daily_limit}, Scheduled for {target_date}: {sent_on_target_date}, "
            "Available for mailing: {available_users}."
        ),
        "schedule_success": "The mailing is successfully scheduled for {scheduled_time} (MSK).",
        "send_mailing_message": "📨 Please send the message to be sent to the bot users.",
        "no_scheduled_mailings": "No scheduled mailings.",
        "scheduled_mailings": "Scheduled mailings:",
        "edit_mailing_error": "Error: mailing not found.",
        "mailing_info": (
            "📨 *Mailing Info:*\n"
            "ID: `{mailing_id}`\n"
            "Type: `{mailing_type}`\n"
            "Time: `{scheduled_time}`\n\n"
        ),
        "cancel_mailing": "🗑️ Cancel Mailing",
        "mailing_not_found": "Mailing not found.",
        "mailing_deleted": "Mailing successfully canceled.",
        "regular_button": "Regular",
        "inline_button": "Inline",
        "add_button_instructions": (
            "Here you can add buttons to the Main Menu.\n\n"
            "Select the type of the new button:\n\n"
            "*Regular* — located in the menu block at the bottom and can contain text, media, or a link to another menu.\n\n"
            "*Inline* — displayed under messages, can lead to a link, replace the current message, or contain text, media, and menus."
        ),
        "enter_button_name": "Enter the button name:",
        "inline_type_link": "Open a link",
        "inline_type_replace": "Replace the current message",
        "inline_type_new": "Send a new message",
        "select_inline_type": "Choose the type of inline button:",
        "subscription_already_active": "You already have an active subscription for this bot until {end_date}.",
        "months": "months",
        "rub": "RUB",
        "choose_subscription_duration": "Select the subscription duration:",
        "subscription_selected": "You selected a subscription for {duration} at {price}.",
        "choose_payment_method": "Select a payment method:",
        "pay_via_telegram_stars": "⭐️ Telegram Stars",
        "pay_via_crypto_bot": "Pay via Crypto",
        "invalid_subscription_choice": "Invalid subscription choice.",
        "payment_initiated": "Payment link successfully created. Follow the link to complete the payment:",
        "payment_failed": "Payment failed.",
        "payment_successful": "Payment successfully completed. You are subscribed to the bot {bot_username} until {end_date}.",
        "invoice_not_found": "Invoice not found. The record has been removed from pending payments.",
        "export_users": "📥 Export users"
    }
}
