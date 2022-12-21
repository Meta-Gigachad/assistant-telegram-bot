# Helpful Shrek Bot
Small bot impersonation of Shrek. Bot is deployed [here](https://t.me/MetaGigachad_DebugBot) until 01.01.2023.

Uses [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) which provides **convenience wrappers** as well as **async runtime**.

Most data is stored in [MySQL](https://www.mysql.com/) database.

# Deploy

1. Add **.env** file. You can copy the example from **.env.example** and fill in the blanks.
2. You will need to have [docker](https://www.docker.com/) installed. Navigate to project root directory. Then just run
    ```bash
    docker compose --env-file .env up
    ```

# Current functionality

## Swamp Nutrition

1. You can add food when you eat it using `/add_food`
2. Then you can watch what you have eaten today using `/food_stats`

## Swamp Training

1. You can add new exercises using `/add_exercise`
2. You can generate a training session based on your exercises using `/generate_training`

## Talking with Shrek

1. You can use get who you are in Shrek universe using `/who_am_i_in_shrek`
2. You can write any message to Shrek and he will respond.
3. If you are lazy to write you can record a voice message and Shrek will answer it too.
