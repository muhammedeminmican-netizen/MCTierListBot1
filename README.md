# MCTierListBot

## Kurulum

1. Python 3.10 veya üzeri kurulu olmalı.
2. Bağımlılıkları yükleyin:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. `.env.example` dosyasını `.env` olarak kopyalayın ve `DISCORD_TOKEN` alanına kendi Discord bot token'ınızı yazın.
4. Botu başlatın:

   ```bash
   python bot.py
   ```

5. Discord sunucusunda yetkili hesabıyla `/setup` komutunu bir kez çalıştırın.

## Aktif PvP kitleri

Sword, Axe, Crystal, UHC, Neth Pot, Dia Pot, SMP, Mace, Dia SMP, Cart,
Spear Mace, Speed, One Touch ve Spear Elytra.

Her kit için HT1–LT5 aralığında tier rolü oluşturulur (14 × 10 = 140 kit-tier rolü).

## Temel komutlar

- `/link`: Minecraft hesabını Discord hesabına bağlar.
- `/q join`: Bir kitin test kuyruğuna katılmayı başlatır.
- `/q list`: Kit kuyruğunu gösterir.
- `/q next`, `/q finish`, `/q cancel`: Yetkililerin test sürecini yönetmesini sağlar.
- `/settier` ve `/removetier`: Yetkililerin tier ekleyip kaldırmasını sağlar.
- `/profile` ve `/leaderboard`: Tier profili ve kit sıralamasını gösterir.
- `/modes`: Aktif kit listesini gösterir.

Önceki sürümlerdeki Pot/Bow tier kayıtları profil geçmişinde korunur. Eski NethPot/DiaPot rol adları da yeni rol eşitlemesinde tanınır.
