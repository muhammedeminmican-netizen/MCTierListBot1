import logging
import os
import re

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mctierlist")

DATABASE_PATH = os.getenv("DATABASE_PATH", "mctierlist.db")
# Aktif kitler: Discord slash komutları, kuyruk, roller ve sıralamalar
# bu tek listeden beslenir. Böylece bir kitin bir yerde unutulması önlenir.
MODES = [
    app_commands.Choice(name="Sword", value="sword"),
    app_commands.Choice(name="Axe", value="axe"),
    app_commands.Choice(name="Crystal", value="crystal"),
    app_commands.Choice(name="UHC", value="uhc"),
    app_commands.Choice(name="Neth Pot", value="nethpot"),
    app_commands.Choice(name="Dia Pot", value="diapot"),
    app_commands.Choice(name="SMP", value="smp"),
    app_commands.Choice(name="Mace", value="mace"),
    app_commands.Choice(name="Dia SMP", value="diasmp"),
    app_commands.Choice(name="Cart", value="cart"),
    app_commands.Choice(name="Spear Mace", value="spearmace"),
    app_commands.Choice(name="Speed", value="speed"),
    app_commands.Choice(name="One Touch", value="onetouch"),
    app_commands.Choice(name="Spear Elytra", value="spearelytra"),
]
TIERS = [
    app_commands.Choice(name="HT1", value="HT1"),
    app_commands.Choice(name="LT1", value="LT1"),
    app_commands.Choice(name="HT2", value="HT2"),
    app_commands.Choice(name="LT2", value="LT2"),
    app_commands.Choice(name="HT3", value="HT3"),
    app_commands.Choice(name="LT3", value="LT3"),
    app_commands.Choice(name="HT4", value="HT4"),
    app_commands.Choice(name="LT4", value="LT4"),
    app_commands.Choice(name="HT5", value="HT5"),
    app_commands.Choice(name="LT5", value="LT5"),
]
TIER_ORDER = {choice.value: position for position, choice in enumerate(TIERS)}
MODE_NAMES = {choice.value: choice.name for choice in MODES}
# Önceki sürümlerde kaydedilen sonuçlar profillerde görünmeye devam etsin.
LEGACY_MODE_NAMES = {"pot": "Pot (eski mod)", "bow": "Bow (eski mod)"}
MODE_NAMES.update(LEGACY_MODE_NAMES)
# Eski sürümlerde bu iki rol etiketi boşluksuz oluşturulmuştu.
LEGACY_MODE_ROLE_LABELS = {"nethpot": ("NethPot",), "diapot": ("DiaPot",)}
MODE_ORDER = {choice.value: position for position, choice in enumerate(MODES)}
TICKET_MODE_VALUES = tuple(choice.value for choice in MODES) + tuple(LEGACY_MODE_NAMES)
TICKET_MODE_PATTERN = "|".join(re.escape(value) for value in TICKET_MODE_VALUES)
MINECRAFT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,16}$")
TIER_ROLE_COLORS = {
    "HT1": discord.Color.from_rgb(231, 76, 60),
    "LT1": discord.Color.from_rgb(230, 126, 34),
    "HT2": discord.Color.from_rgb(241, 196, 15),
    "LT2": discord.Color.from_rgb(211, 184, 64),
    "HT3": discord.Color.from_rgb(46, 204, 113),
    "LT3": discord.Color.from_rgb(39, 174, 96),
    "HT4": discord.Color.from_rgb(52, 152, 219),
    "LT4": discord.Color.from_rgb(41, 128, 185),
    "HT5": discord.Color.from_rgb(155, 89, 182),
    "LT5": discord.Color.from_rgb(127, 140, 141),
}
SETUP_LAYOUT = (
    (
        "📌 BİLGİ",
        (
            ("text", "hos-geldin", None),
            ("text", "kurallar", "rules"),
            ("text", "duyurular", None),
            ("text", "tier-rehberi", "guide"),
        ),
    ),
    (
        "🏆 TIER LİSTESİ",
        (("text", "tier-sonuclari", None), ("text", "tier-basvurusu", "application")),
    ),
    (
        "💬 TOPLULUK",
        (
            ("text", "genel-sohbet", None),
            ("text", "bot-komutlari", None),
            ("text", "medya", None),
            ("voice", "Genel Sohbet", None),
        ),
    ),
    (
        "🛡 YETKİLİ",
        (
            ("text", "yetkili-sohbet", None),
            ("text", "tier-loglari", None),
            ("voice", "Tier Testleri", None),
        ),
    ),
)
SETUP_STARTER_MESSAGES = {
    "rules": (
        "Sunucuda saygılı olun; spam, taciz ve hile teşviki yasaktır.\n"
        "Komutlar: `/link`, `/profile`, `/leaderboard`; yetkililer tier kaydı için `/settier` kullanır.\n"
        "Tier değerlendirmeleri Tier Tester ekibiyle planlanır."
    ),
    "application": (
        "Başvuru için Minecraft hesabını `/link` ile bağla; durumunu `/profile` ve "
        "`/leaderboard` ile kontrol edebilirsin. `/q join` ile modunu seçip Minecraft adı, "
        "eski tier (yoksa N/A) ve ‘Hangi SW?’ sorularını yanıtla; özel test ticketın açılır. "
        "Sıra ve başvuru için `/q leave` ve "
        "`/q list` kullan. Tier Tester veya Sunucuyu Yönet yetkilileri `/q next`, `/q finish` "
        "ve gerekirse `/q cancel` komutlarını kullanır; `/settier` manuel tier kaydı içindir.\n"
        "Tier değerlendirmeleri Tier Tester ekibiyle planlanır."
    ),
    "guide": (
        "Tierler oyun modlarına göre tutulur. Hesabını `/link` ile bağla; `/profile` ve "
        "`/leaderboard` ile kayıtları görüntüle. `/q join` ile modunu seçip Minecraft adı, "
        "eski tier (yoksa N/A) ve ‘Hangi SW?’ sorularını yanıtlayarak özel test ticketı açabilir, "
        "`/q leave` ile ayrılabilir ve `/q list` ile sırayı görebilirsin. Tier Tester veya "
        "Sunucuyu Yönet yetkilileri `/q next`, `/q finish` ve `/q cancel` komutlarıyla "
        "değerlendirmeyi yönetir; sonuçlar ayrıca `/settier` ile kaydedilebilir.\n"
        "Tier değerlendirmeleri Tier Tester ekibiyle planlanır."
    ),
}


class TierDatabase:
    def __init__(self, path: str):
        self.path = path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.path) as database:
            await database.executescript(
                """
                CREATE TABLE IF NOT EXISTS players (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    minecraft_name TEXT NOT NULL COLLATE NOCASE,
                    PRIMARY KEY (guild_id, user_id),
                    UNIQUE (guild_id, minecraft_name)
                );
                CREATE TABLE IF NOT EXISTS tiers (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    mode TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    updated_by INTEGER NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (guild_id, user_id, mode)
                );
                CREATE TABLE IF NOT EXISTS tier_queue (
                    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('waiting', 'testing', 'finishing')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_tier_queue_one_active_user
                    ON tier_queue (guild_id, user_id)
                    WHERE status IN ('waiting', 'testing', 'finishing');
                CREATE UNIQUE INDEX IF NOT EXISTS idx_tier_queue_one_active_test
                    ON tier_queue (guild_id, mode)
                    WHERE status IN ('testing', 'finishing');
                CREATE INDEX IF NOT EXISTS idx_tier_queue_fifo
                    ON tier_queue (guild_id, mode, status, queue_id);
                """
            )
            await database.execute(
                "UPDATE tier_queue SET status = 'testing' WHERE status = 'finishing'"
            )
            await database.commit()

    async def link_player(self, guild_id: int, user_id: int, minecraft_name: str) -> None:
        async with aiosqlite.connect(self.path) as database:
            await database.execute(
                """
                INSERT INTO players (guild_id, user_id, minecraft_name)
                VALUES (?, ?, ?)
                ON CONFLICT (guild_id, user_id)
                DO UPDATE SET minecraft_name = excluded.minecraft_name
                """,
                (guild_id, user_id, minecraft_name),
            )
            await database.commit()

    async def get_player(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.path) as database:
            database.row_factory = aiosqlite.Row
            cursor = await database.execute(
                "SELECT minecraft_name FROM players WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            return await cursor.fetchone()

    async def get_tiers(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.path) as database:
            database.row_factory = aiosqlite.Row
            cursor = await database.execute(
                "SELECT mode, tier FROM tiers WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            return await cursor.fetchall()

    async def set_tier(
        self, guild_id: int, user_id: int, mode: str, tier: str, updated_by: int
    ) -> None:
        async with aiosqlite.connect(self.path) as database:
            await database.execute(
                """
                INSERT INTO tiers (guild_id, user_id, mode, tier, updated_by)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (guild_id, user_id, mode) DO UPDATE SET
                    tier = excluded.tier,
                    updated_by = excluded.updated_by,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (guild_id, user_id, mode, tier, updated_by),
            )
            await database.commit()

    async def remove_tier(self, guild_id: int, user_id: int, mode: str) -> bool:
        async with aiosqlite.connect(self.path) as database:
            cursor = await database.execute(
                "DELETE FROM tiers WHERE guild_id = ? AND user_id = ? AND mode = ?",
                (guild_id, user_id, mode),
            )
            await database.commit()
            return cursor.rowcount > 0

    async def leaderboard(self, guild_id: int, mode: str):
        async with aiosqlite.connect(self.path) as database:
            database.row_factory = aiosqlite.Row
            cursor = await database.execute(
                """
                SELECT players.user_id, players.minecraft_name, tiers.tier
                FROM tiers
                JOIN players
                  ON players.guild_id = tiers.guild_id
                 AND players.user_id = tiers.user_id
                WHERE tiers.guild_id = ? AND tiers.mode = ?
                """,
                (guild_id, mode),
            )
            rows = await cursor.fetchall()
        return sorted(rows, key=lambda row: (TIER_ORDER[row["tier"]], row["minecraft_name"].casefold()))

    async def queue_join(self, guild_id: int, user_id: int, mode: str) -> dict:
        async with aiosqlite.connect(self.path) as database:
            database.row_factory = aiosqlite.Row
            await database.execute("BEGIN IMMEDIATE")
            try:
                cursor = await database.execute(
                    "SELECT minecraft_name FROM players WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id),
                )
                if await cursor.fetchone() is None:
                    await database.rollback()
                    return {"status": "no_link"}

                cursor = await database.execute(
                    "SELECT queue_id, mode, status FROM tier_queue "
                    "WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id),
                )
                existing = await cursor.fetchone()
                if existing is not None:
                    position = None
                    if existing["status"] == "waiting":
                        cursor = await database.execute(
                            "SELECT COUNT(*) FROM tier_queue "
                            "WHERE guild_id = ? AND mode = ? AND status = 'waiting' AND queue_id <= ?",
                            (guild_id, existing["mode"], existing["queue_id"]),
                        )
                        position = (await cursor.fetchone())[0]
                    await database.rollback()
                    return {
                        "status": "duplicate",
                        "entry": dict(existing),
                        "position": position,
                    }

                cursor = await database.execute(
                    "INSERT INTO tier_queue (guild_id, user_id, mode, status) "
                    "VALUES (?, ?, ?, 'waiting')",
                    (guild_id, user_id, mode),
                )
                queue_id = cursor.lastrowid
                cursor = await database.execute(
                    "SELECT COUNT(*) FROM tier_queue "
                    "WHERE guild_id = ? AND mode = ? AND status = 'waiting' AND queue_id <= ?",
                    (guild_id, mode, queue_id),
                )
                position = (await cursor.fetchone())[0]
                await database.commit()
                return {"status": "joined", "position": position}
            except Exception:
                await database.rollback()
                raise

    async def queue_user_entry(self, guild_id: int, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.path) as database:
            database.row_factory = aiosqlite.Row
            cursor = await database.execute(
                "SELECT queue_id, mode, status FROM tier_queue "
                "WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            entry = await cursor.fetchone()
            if entry is None:
                return None
            position = None
            if entry["status"] == "waiting":
                cursor = await database.execute(
                    "SELECT COUNT(*) FROM tier_queue "
                    "WHERE guild_id = ? AND mode = ? AND status = 'waiting' AND queue_id <= ?",
                    (guild_id, entry["mode"], entry["queue_id"]),
                )
                position = (await cursor.fetchone())[0]
            return {**dict(entry), "position": position}

    async def queue_ticket_entry(
        self, guild_id: int, mode: str, minecraft_name: str
    ) -> dict | None:
        async with aiosqlite.connect(self.path) as database:
            database.row_factory = aiosqlite.Row
            cursor = await database.execute(
                "SELECT tier_queue.queue_id, tier_queue.user_id, tier_queue.mode, "
                "tier_queue.status FROM tier_queue "
                "JOIN players ON players.guild_id = tier_queue.guild_id "
                "AND players.user_id = tier_queue.user_id "
                "WHERE tier_queue.guild_id = ? AND tier_queue.mode = ? "
                "AND players.minecraft_name = ? COLLATE NOCASE",
                (guild_id, mode, minecraft_name),
            )
            entry = await cursor.fetchone()
            return dict(entry) if entry is not None else None

    async def queue_leave(self, guild_id: int, user_id: int) -> dict | None:
        async with aiosqlite.connect(self.path) as database:
            database.row_factory = aiosqlite.Row
            await database.execute("BEGIN IMMEDIATE")
            cursor = await database.execute(
                "SELECT queue_id, mode, status FROM tier_queue "
                "WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id),
            )
            entry = await cursor.fetchone()
            if entry is None:
                await database.commit()
                return None
            if entry["status"] == "finishing":
                await database.commit()
                return {**dict(entry), "result": "finishing"}
            await database.execute(
                "DELETE FROM tier_queue WHERE queue_id = ?", (entry["queue_id"],)
            )
            await database.commit()
            return {**dict(entry), "result": "left"}

    async def queue_list(self, guild_id: int, mode: str) -> list[dict]:
        async with aiosqlite.connect(self.path) as database:
            database.row_factory = aiosqlite.Row
            cursor = await database.execute(
                "SELECT tier_queue.queue_id, tier_queue.user_id, tier_queue.mode, "
                "tier_queue.status, players.minecraft_name FROM tier_queue "
                "LEFT JOIN players ON players.guild_id = tier_queue.guild_id "
                "AND players.user_id = tier_queue.user_id "
                "WHERE tier_queue.guild_id = ? AND tier_queue.mode = ? "
                "ORDER BY CASE tier_queue.status WHEN 'testing' THEN 0 "
                "WHEN 'finishing' THEN 0 ELSE 1 END, tier_queue.queue_id",
                (guild_id, mode),
            )
            return [dict(row) for row in await cursor.fetchall()]

    async def queue_next(self, guild_id: int, mode: str) -> dict:
        async with aiosqlite.connect(self.path) as database:
            database.row_factory = aiosqlite.Row
            await database.execute("BEGIN IMMEDIATE")
            cursor = await database.execute(
                "SELECT queue_id, user_id, mode, status FROM tier_queue "
                "WHERE guild_id = ? AND mode = ? AND status IN ('testing', 'finishing')",
                (guild_id, mode),
            )
            active = await cursor.fetchone()
            if active is not None:
                await database.commit()
                return {"status": "active", "entry": dict(active)}

            cursor = await database.execute(
                "SELECT queue_id, user_id, mode, status FROM tier_queue "
                "WHERE guild_id = ? AND mode = ? AND status = 'waiting' "
                "ORDER BY queue_id LIMIT 1",
                (guild_id, mode),
            )
            entry = await cursor.fetchone()
            if entry is None:
                await database.commit()
                return {"status": "empty"}
            await database.execute(
                "UPDATE tier_queue SET status = 'testing' "
                "WHERE queue_id = ? AND status = 'waiting'",
                (entry["queue_id"],),
            )
            await database.commit()
            return {"status": "called", "entry": dict(entry)}

    async def queue_claim_finish(self, guild_id: int, mode: str) -> dict:
        async with aiosqlite.connect(self.path) as database:
            database.row_factory = aiosqlite.Row
            await database.execute("BEGIN IMMEDIATE")
            cursor = await database.execute(
                "SELECT queue_id, user_id, mode, status FROM tier_queue "
                "WHERE guild_id = ? AND mode = ? AND status IN ('testing', 'finishing')",
                (guild_id, mode),
            )
            entry = await cursor.fetchone()
            if entry is None:
                await database.commit()
                return {"status": "none"}
            if entry["status"] == "finishing":
                await database.commit()
                return {"status": "busy"}
            await database.execute(
                "UPDATE tier_queue SET status = 'finishing' "
                "WHERE queue_id = ? AND status = 'testing'",
                (entry["queue_id"],),
            )
            await database.commit()
            return {"status": "claimed", "entry": dict(entry)}

    async def queue_restore_finish(self, queue_id: int) -> None:
        async with aiosqlite.connect(self.path) as database:
            await database.execute(
                "UPDATE tier_queue SET status = 'testing' "
                "WHERE queue_id = ? AND status = 'finishing'",
                (queue_id,),
            )
            await database.commit()

    async def queue_complete_finish(self, guild_id: int, queue_id: int) -> bool:
        async with aiosqlite.connect(self.path) as database:
            cursor = await database.execute(
                "DELETE FROM tier_queue WHERE guild_id = ? AND queue_id = ? "
                "AND status = 'finishing'",
                (guild_id, queue_id),
            )
            await database.commit()
            return cursor.rowcount > 0

    async def queue_cancel(self, guild_id: int, mode: str) -> dict | None:
        async with aiosqlite.connect(self.path) as database:
            database.row_factory = aiosqlite.Row
            await database.execute("BEGIN IMMEDIATE")
            cursor = await database.execute(
                "SELECT queue_id, user_id, mode, status FROM tier_queue "
                "WHERE guild_id = ? AND mode = ? AND status IN ('testing', 'finishing')",
                (guild_id, mode),
            )
            entry = await cursor.fetchone()
            if entry is None:
                await database.commit()
                return None
            if entry["status"] == "finishing":
                await database.commit()
                return {**dict(entry), "result": "finishing"}
            await database.execute(
                "DELETE FROM tier_queue WHERE queue_id = ? AND status = 'testing'",
                (entry["queue_id"],),
            )
            await database.commit()
            return {**dict(entry), "result": "cancelled"}


database = TierDatabase(DATABASE_PATH)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
synced_guild_ids: set[int] = set()


@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.id in synced_guild_ids:
            continue
        bot.tree.clear_commands(guild=guild)
        try:
            await bot.tree.sync(guild=guild)
            synced_guild_ids.add(guild.id)
            logger.info("%s sunucusundaki yinelenen slash komutları temizlendi", guild.name)
        except discord.HTTPException as error:
            logger.warning("%s sunucusuna slash komutları eşitlenemedi: %s", guild.name, error)
    logger.info("Bot %s olarak giriş yaptı", bot.user)
    print("KODARI_READY", flush=True)


@bot.event
async def setup_hook():
    await database.initialize()
    synced = await bot.tree.sync()
    logger.info("%s slash komutu Discord ile eşitlendi", len(synced))


def tier_staff_check():
    async def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        return isinstance(member, discord.Member) and (
            member.guild_permissions.manage_guild
            or any(role.name == "Tier Tester" for role in member.roles)
        )

    return app_commands.check(predicate)


def tier_role_name(mode: str, tier: str) -> str:
    return f"{MODE_NAMES[mode]} • {tier}"


def mode_tier_roles(guild: discord.Guild, mode: str) -> list[discord.Role]:
    labels = {MODE_NAMES[mode], *LEGACY_MODE_ROLE_LABELS.get(mode, ())}
    names = {
        f"{label} • {tier.value}"
        for label in labels
        for tier in TIERS
    }
    return [role for role in guild.roles if role.name in names]


async def sync_tier_role(
    guild: discord.Guild,
    member: discord.Member,
    mode: str,
    tier: str,
    reason: str,
) -> str | None:
    target_role = discord.utils.get(guild.roles, name=tier_role_name(mode, tier))
    if target_role is None:
        return (
            f"Discord'da `{tier_role_name(mode, tier)}` rolü yok. "
            "Veritabanı kaydedildi; `/setup` çalıştırıp rolü oluşturun."
        )

    other_roles = [
        role
        for role in mode_tier_roles(guild, mode)
        if role.id != target_role.id and role in member.roles
    ]
    try:
        if target_role not in member.roles:
            await member.add_roles(target_role, reason=reason)
        if other_roles:
            await member.remove_roles(*other_roles, reason=reason)
    except discord.HTTPException as error:
        logger.warning("Tier rolü eşitlenemedi: %s", error)
        return (
            "Veritabanı kaydedildi, ancak Discord rol eşitlemesi başarısız oldu. "
            "Botta Manage Roles iznini ve bot rolünün tier rollerinden yukarıda olduğunu kontrol edin."
        )
    return None


queue_group = app_commands.Group(name="q", description="Tier test kuyruğu komutları")


class TierQueueApplicationModal(discord.ui.Modal):
    def __init__(self, mode: str, linked_name: str):
        super().__init__(title=f"{MODE_NAMES[mode]} Tier Test Başvurusu")
        self.mode = mode
        self.linked_name = linked_name
        self.minecraft_name = discord.ui.TextInput(
            label="Minecraft oyuncu adı",
            placeholder="/link ile bağladığın ad",
            default=linked_name,
            min_length=3,
            max_length=16,
        )
        self.old_tier = discord.ui.TextInput(
            label="Eski tier",
            placeholder="Tierin yoksa N/A yaz",
            max_length=30,
        )
        self.sw = discord.ui.TextInput(
            label="Hangi SW?",
            placeholder="İstediğin SW bilgisini yaz",
            max_length=200,
        )
        self.add_item(self.minecraft_name)
        self.add_item(self.old_tier)
        self.add_item(self.sw)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Bu başvuru yalnızca bir sunucuda kullanılabilir.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        player = await database.get_player(guild.id, interaction.user.id)
        entered_name = self.minecraft_name.value.strip()
        if player is None:
            await interaction.followup.send(
                "Başvuru için önce `/link` ile Minecraft hesabını bağlamalısın.",
                ephemeral=True,
            )
            return
        if (
            not MINECRAFT_NAME_PATTERN.fullmatch(entered_name)
            or entered_name.casefold() != player["minecraft_name"].casefold()
        ):
            await interaction.followup.send(
                f"Minecraft adı `/link` hesabınla eşleşmeli: **{player['minecraft_name']}**.",
                ephemeral=True,
            )
            return

        existing = await database.queue_user_entry(guild.id, interaction.user.id)
        if existing is not None:
            queued_mode = MODE_NAMES[existing["mode"]]
            if existing["status"] == "waiting":
                message = (
                    f"Zaten **{queued_mode}** kuyruğunda {existing['position']}. sıradasın. "
                    "Başka bir aktif başvuru açamazsın."
                )
            else:
                message = (
                    f"Zaten **{queued_mode}** modunda testtesin. "
                    "Test bitmeden başka bir başvuru açamazsın."
                )
            await interaction.followup.send(message, ephemeral=True)
            return

        bot_member = guild.me
        if bot_member is None or not bot_member.guild_permissions.manage_channels:
            await interaction.followup.send(
                "Ticket açılamadı; botta **Manage Channels** izni olmalı. Kuyruğa eklenmedin.",
                ephemeral=True,
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                embed_links=True,
            ),
        }
        for role in guild.roles:
            if role.name in {"Admin", "Tier Tester"}:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                )

        old_tier = self.old_tier.value.strip() or "N/A"
        sw_info = self.sw.value.strip() or "Belirtilmedi"
        safe_old_tier = old_tier.replace("`", "ˋ")
        safe_sw_info = sw_info.replace("`", "ˋ")
        topic = (
            f"Oyuncu: {entered_name} | Eski tier: {old_tier} | Hangi SW?: {sw_info}"
        )[:1024]
        category = discord.utils.get(guild.categories, name="🏆 TIER LİSTESİ")
        channel_name = f"q-{self.mode}-{entered_name.casefold()}"

        try:
            ticket = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                topic=topic,
                reason="MCTierList tier testi başvurusu",
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "Ticket açılamadı: botun **Manage Channels** iznini ve kanal izinlerini kontrol edin. "
                "Kuyruğa eklenmedin.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as error:
            logger.warning("Tier test ticketı açılamadı: %s", error)
            await interaction.followup.send(
                f"Ticket açılamadı (Discord HTTP {error.status}); kuyruğa eklenmedin.",
                ephemeral=True,
            )
            return

        try:
            result = await database.queue_join(guild.id, interaction.user.id, self.mode)
        except aiosqlite.Error:
            logger.exception("Ticket açıldı ancak oyuncu kuyruğa eklenemedi")
            try:
                await ticket.delete(reason="Kuyruğa ekleme başarısız oldu")
            except discord.HTTPException:
                logger.warning("Kuyruğa alınamayan ticket temizlenemedi: %s", ticket.id)
            await interaction.followup.send(
                "Başvuru veritabanına kaydedilemedi. Tekrar denemeden önce Tier Tester ile iletişime geç.",
                ephemeral=True,
            )
            return

        if result["status"] != "joined":
            try:
                await ticket.delete(reason="Aktif kuyruk kaydı zaten mevcut")
            except discord.HTTPException:
                logger.warning("Tekrarlanan başvuru ticketı temizlenemedi: %s", ticket.id)
            if result["status"] == "no_link":
                message = "Minecraft hesabı bağlantın bulunamadı; önce `/link` kullanmalısın."
            else:
                queued_mode = MODE_NAMES[result["entry"]["mode"]]
                message = f"Zaten **{queued_mode}** için aktif bir kuyruk veya test kaydın var."
            await interaction.followup.send(message, ephemeral=True)
            return

        try:
            await ticket.send(
                f"🎫 **{MODE_NAMES[self.mode]} test başvurusu**\n"
                f"Oyuncu: {interaction.user.mention} — **{entered_name}**\n"
                f"Eski tier: `{safe_old_tier}`\n"
                f"Hangi SW?: `{safe_sw_info}`\n"
                f"Kuyruk sırası: **{result['position']}**\n"
                "Tier Tester sıran geldiğinde testi `/q next` ile başlatıp `/q finish` ile sonucu kaydeder.",
                allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
            )
        except discord.HTTPException as error:
            logger.warning("Ticket açıldı fakat başvuru mesajı gönderilemedi: %s", error)
            await interaction.followup.send(
                f"Kuyruğa katıldın ({result['position']}. sıra) ve ticket açıldı: {ticket.mention}. "
                "Ancak başvuru mesajı gönderilemedi; Tier Tester ile iletişime geç.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"Başvurun alındı ve **{result['position']}.** sıraya eklendin. "
            f"Özel test ticketın: {ticket.mention}",
            ephemeral=True,
        )


def setup_failure(label: str, error: discord.HTTPException) -> str:
    if isinstance(error, discord.Forbidden):
        return f"{label}: erişim reddedildi; bot izinlerini ve rol sırasını kontrol edin."
    return f"{label}: Discord API hatası (HTTP {error.status})."


async def update_overwrite(
    channel,
    target,
    label: str,
    failures: list[str],
    **permissions,
) -> None:
    overwrite = channel.overwrites_for(target)
    changed = False
    for name, value in permissions.items():
        if getattr(overwrite, name) != value:
            setattr(overwrite, name, value)
            changed = True
    if not changed:
        return
    try:
        await channel.set_permissions(
            target, overwrite=overwrite, reason="MCTierList sunucu kurulumu"
        )
    except discord.HTTPException as error:
        failures.append(setup_failure(label, error))


async def ensure_setup_role(
    guild: discord.Guild,
    name: str,
    permissions: discord.Permissions,
    colour: discord.Color,
    counts: dict[str, int],
    failures: list[str],
) -> discord.Role | None:
    role = discord.utils.get(guild.roles, name=name)
    if role is None:
        try:
            role = await guild.create_role(
                name=name,
                permissions=permissions,
                colour=colour,
                reason="MCTierList sunucu kurulumu",
            )
            counts["roles_created"] += 1
        except discord.HTTPException as error:
            failures.append(setup_failure(f"Rol {name}", error))
            return None
    else:
        counts["roles_reused"] += 1
        changes = {}
        if role.permissions != permissions:
            changes["permissions"] = permissions
        if role.colour != colour:
            changes["colour"] = colour
        if changes:
            try:
                await role.edit(**changes, reason="MCTierList sunucu kurulumu")
            except discord.HTTPException as error:
                failures.append(setup_failure(f"Rol {name}", error))
    return role


@bot.tree.command(name="setup", description="MCTierList sunucu kanallarını ve rollerini kur")
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_guild=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    bot_member = guild.me
    required_permissions = {
        "manage_roles": "Manage Roles",
        "manage_channels": "Manage Channels",
        "view_channel": "View Channels",
        "send_messages": "Send Messages",
        "embed_links": "Embed Links",
    }
    missing_permissions = [
        label
        for attribute, label in required_permissions.items()
        if not getattr(bot_member.guild_permissions, attribute)
    ]
    if missing_permissions:
        await interaction.followup.send(
            "Kurulum başlatılmadı. Botta eksik izinler: **"
            + ", ".join(missing_permissions)
            + "**. Gerekli izinler: Manage Roles, Manage Channels, View Channels, Send Messages ve Embed Links.",
            ephemeral=True,
        )
        return

    counts = {
        "categories_created": 0,
        "categories_reused": 0,
        "channels_created": 0,
        "channels_reused": 0,
        "roles_created": 0,
        "roles_reused": 0,
        "starter_messages": 0,
    }
    failures: list[str] = []

    admin_permissions = discord.Permissions.none()
    for permission in (
        "manage_guild",
        "manage_channels",
        "manage_roles",
        "manage_messages",
        "kick_members",
        "ban_members",
    ):
        setattr(admin_permissions, permission, True)
    tester_permissions = discord.Permissions.none()
    admin_role = await ensure_setup_role(
        guild,
        "Admin",
        admin_permissions,
        discord.Color.from_rgb(231, 76, 60),
        counts,
        failures,
    )
    tester_role = await ensure_setup_role(
        guild,
        "Tier Tester",
        tester_permissions,
        discord.Color.from_rgb(52, 152, 219),
        counts,
        failures,
    )
    for mode in MODES:
        for tier in TIERS:
            await ensure_setup_role(
                guild,
                tier_role_name(mode.value, tier.value),
                discord.Permissions.none(),
                TIER_ROLE_COLORS[tier.value],
                counts,
                failures,
            )

    categories: dict[str, discord.CategoryChannel | None] = {}
    for category_name, _ in SETUP_LAYOUT:
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            try:
                category = await guild.create_category(
                    category_name, reason="MCTierList sunucu kurulumu"
                )
                counts["categories_created"] += 1
            except discord.HTTPException as error:
                failures.append(setup_failure(f"Kategori {category_name}", error))
        else:
            counts["categories_reused"] += 1
        categories[category_name] = category

        if category is not None and category_name == "🛡 YETKİLİ":
            await update_overwrite(
                category,
                guild.default_role,
                f"{category_name} @everyone izni",
                failures,
                view_channel=False,
            )
            for role in (admin_role, tester_role):
                if role is not None:
                    await update_overwrite(
                        category,
                        role,
                        f"{category_name} {role.name} izni",
                        failures,
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        connect=True,
                        speak=True,
                    )
            await update_overwrite(
                category,
                bot_member,
                f"{category_name} bot izni",
                failures,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                connect=True,
                speak=True,
                embed_links=True,
            )
        elif category is not None:
            await update_overwrite(
                category,
                guild.default_role,
                f"{category_name} @everyone izni",
                failures,
                view_channel=True,
            )

    for category_name, channel_specs in SETUP_LAYOUT:
        category = categories[category_name]
        if category is None:
            failures.append(f"{category_name}: kategori yok, iç kanallar atlandı.")
            continue

        is_staff = category_name == "🛡 YETKİLİ"
        for channel_type, channel_name, starter_key in channel_specs:
            channel_class = discord.VoiceChannel if channel_type == "voice" else discord.TextChannel
            matching = [
                channel
                for channel in guild.channels
                if isinstance(channel, channel_class) and channel.name == channel_name
            ]
            channel = next(
                (item for item in matching if item.category_id == category.id),
                matching[0] if matching else None,
            )
            newly_created = channel is None
            if newly_created:
                try:
                    if channel_type == "voice":
                        channel = await guild.create_voice_channel(
                            channel_name,
                            category=category,
                            reason="MCTierList sunucu kurulumu",
                        )
                    else:
                        channel = await guild.create_text_channel(
                            channel_name,
                            category=category,
                            reason="MCTierList sunucu kurulumu",
                        )
                    counts["channels_created"] += 1
                except discord.HTTPException as error:
                    failures.append(setup_failure(f"Kanal {channel_name}", error))
                    continue
            else:
                counts["channels_reused"] += 1
                if channel.category_id != category.id:
                    try:
                        await channel.edit(
                            category=category, reason="MCTierList sunucu kurulumu"
                        )
                    except discord.HTTPException as error:
                        failures.append(setup_failure(f"Kanal {channel_name}", error))

            readonly = channel_name in {
                "kurallar",
                "duyurular",
                "tier-rehberi",
                "tier-sonuclari",
            }
            if is_staff:
                await update_overwrite(
                    channel,
                    guild.default_role,
                    f"{channel_name} @everyone izni",
                    failures,
                    view_channel=False,
                )
                for role in (admin_role, tester_role):
                    if role is not None:
                        await update_overwrite(
                            channel,
                            role,
                            f"{channel_name} {role.name} izni",
                            failures,
                            view_channel=True,
                            send_messages=True,
                            read_message_history=True,
                            connect=True,
                            speak=True,
                        )
                await update_overwrite(
                    channel,
                    bot_member,
                    f"{channel_name} bot izni",
                    failures,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    connect=True,
                    speak=True,
                    embed_links=True,
                )
            elif channel_type == "voice":
                await update_overwrite(
                    channel,
                    guild.default_role,
                    f"{channel_name} @everyone izni",
                    failures,
                    view_channel=True,
                    connect=True,
                    speak=True,
                )
                await update_overwrite(
                    channel,
                    bot_member,
                    f"{channel_name} bot izni",
                    failures,
                    view_channel=True,
                    connect=True,
                    speak=True,
                )
            else:
                await update_overwrite(
                    channel,
                    guild.default_role,
                    f"{channel_name} @everyone izni",
                    failures,
                    view_channel=True,
                    read_message_history=True,
                    send_messages=not readonly,
                )
                await update_overwrite(
                    channel,
                    bot_member,
                    f"{channel_name} bot izni",
                    failures,
                    view_channel=True,
                    read_message_history=True,
                    send_messages=True,
                    embed_links=True,
                )

            if newly_created and starter_key is not None:
                try:
                    await channel.send(
                        SETUP_STARTER_MESSAGES[starter_key],
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                    counts["starter_messages"] += 1
                except discord.HTTPException as error:
                    failures.append(setup_failure(f"{channel_name} başlangıç mesajı", error))

    result = (
        "**MCTierList kurulumu tamamlandı**\n"
        f"Kategoriler: {counts['categories_created']} oluşturuldu / {counts['categories_reused']} kullanıldı\n"
        f"Kanallar: {counts['channels_created']} oluşturuldu / {counts['channels_reused']} kullanıldı\n"
        f"Roller: {counts['roles_created']} oluşturuldu / {counts['roles_reused']} kullanıldı"
        f" ({len(MODES) * len(TIERS)} mod-tier rolü hedefleniyor)\n"
        f"Başlangıç mesajı: {counts['starter_messages']} gönderildi\n"
        "Gerekli bot izinleri: Manage Roles, Manage Channels, View Channels, Send Messages ve Embed Links."
    )
    if failures:
        shown_failures = failures[:5]
        remaining = len(failures) - len(shown_failures)
        result += "\n\n**Kısmi sorunlar:**\n" + "\n".join(
            f"• {failure}" for failure in shown_failures
        )
        if remaining:
            result += f"\n• Ayrıca {remaining} işlem başarısız oldu."
        result += "\nGerekirse bot rolünü ilgili rollerin üstüne taşıyıp izinlerini kontrol edin."
    await interaction.followup.send(result, ephemeral=True)


@bot.tree.command(name="link", description="Minecraft hesabını Discord hesabına bağla")
@app_commands.guild_only()
@app_commands.checks.cooldown(1, 3.0, key=lambda interaction: interaction.user.id)
async def link(interaction: discord.Interaction, minecraft_adi: str):
    if not MINECRAFT_NAME_PATTERN.fullmatch(minecraft_adi):
        await interaction.response.send_message(
            "Minecraft adı 3-16 karakter olmalı ve yalnızca harf, rakam veya alt çizgi içerebilir.",
            ephemeral=True,
        )
        return

    try:
        await database.link_player(interaction.guild_id, interaction.user.id, minecraft_adi)
    except aiosqlite.IntegrityError:
        await interaction.response.send_message(
            "Bu Minecraft hesabı sunucuda başka bir Discord hesabına bağlı.", ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"Minecraft hesabın **{minecraft_adi}** olarak bağlandı."
    )


@bot.tree.command(name="settier", description="Bir oyuncuya oyun modunda tier ata (yetkili)")
@app_commands.guild_only()
@tier_staff_check()
@app_commands.choices(mode=MODES, tier=TIERS)
async def settier(
    interaction: discord.Interaction,
    uye: discord.Member,
    mode: app_commands.Choice[str],
    tier: app_commands.Choice[str],
):
    player = await database.get_player(interaction.guild_id, uye.id)
    if player is None:
        await interaction.response.send_message(
            f"{uye.mention} henüz `/link` ile Minecraft hesabını bağlamamış.", ephemeral=True
        )
        return

    await database.set_tier(
        interaction.guild_id, uye.id, mode.value, tier.value, interaction.user.id
    )
    sync_error = await sync_tier_role(
        interaction.guild,
        uye,
        mode.value,
        tier.value,
        "MCTierList tier ataması",
    )
    message = (
        f"**{player['minecraft_name']}** oyuncusuna **{MODE_NAMES[mode.value]}** "
        f"modunda **{tier.value}** tierı atandı."
    )
    if sync_error:
        message += f"\n⚠️ {sync_error}"
    await interaction.response.send_message(message)


@bot.tree.command(name="removetier", description="Bir oyuncunun mod tierını sil (yetkili)")
@app_commands.guild_only()
@tier_staff_check()
@app_commands.choices(mode=MODES)
async def removetier(
    interaction: discord.Interaction,
    uye: discord.Member,
    mode: app_commands.Choice[str],
):
    removed = await database.remove_tier(interaction.guild_id, uye.id, mode.value)
    tier_roles = [role for role in mode_tier_roles(interaction.guild, mode.value) if role in uye.roles]
    sync_error = None
    try:
        if tier_roles:
            await uye.remove_roles(*tier_roles, reason="MCTierList tier kaldırma")
    except discord.HTTPException as error:
        logger.warning("Tier rolü kaldırılamadı: %s", error)
        sync_error = (
            "Discord rolü kaldırılamadı. Botta Manage Roles iznini ve bot rolünün tier rollerinden "
            "yukarıda olduğunu kontrol edin."
        )
    if removed:
        message = f"{uye.mention} kullanıcısının **{MODE_NAMES[mode.value]}** tierı veritabanından silindi."
    else:
        message = "Bu oyuncunun belirtilen modda kayıtlı bir tierı yok."
        if tier_roles and sync_error is None:
            message += " Eski Discord tier rolü de kaldırıldı."
    if sync_error:
        message += f"\n⚠️ {sync_error}"
    await interaction.response.send_message(message, ephemeral=not removed or sync_error is not None)


@queue_group.command(name="join", description="Minecraft hesabınla mod kuyruğuna katıl")
@app_commands.guild_only()
@app_commands.choices(mode=MODES)
async def q_join(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    player = await database.get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.response.send_message(
            "Kuyruğa girmeden önce Minecraft hesabını `/link` ile bağlamalısın.",
            ephemeral=True,
        )
        return
    existing = await database.queue_user_entry(interaction.guild_id, interaction.user.id)
    if existing is not None:
        queued_mode = MODE_NAMES[existing["mode"]]
        if existing["status"] == "waiting":
            message = (
                f"Zaten **{queued_mode}** kuyruğunda {existing['position']}. sıradasın. "
                "Başka mod kuyruğuna aynı anda katılamazsın."
            )
        else:
            message = (
                f"Zaten **{queued_mode}** modunda testtesin. "
                "Test bitmeden başka bir kuyruğa katılamazsın."
            )
        await interaction.response.send_message(message, ephemeral=True)
        return
    await interaction.response.send_modal(
        TierQueueApplicationModal(mode.value, player["minecraft_name"])
    )


@queue_group.command(name="leave", description="Kendi aktif kuyruk kaydından ayrıl")
@app_commands.guild_only()
async def q_leave(interaction: discord.Interaction):
    entry = await database.queue_leave(interaction.guild_id, interaction.user.id)
    if entry is None:
        await interaction.response.send_message(
            "Aktif bir kuyruk veya test kaydın bulunmuyor.", ephemeral=True
        )
    elif entry["result"] == "finishing":
        await interaction.response.send_message(
            "Tier sonucu kaydediliyor; bu sırada kuyruktan ayrılamazsın.", ephemeral=True
        )
    else:
        state = "aktif testten" if entry["status"] == "testing" else "bekleme kuyruğundan"
        await interaction.response.send_message(
            f"**{MODE_NAMES[entry['mode']]}** modundaki {state} ayrıldın.", ephemeral=True
        )


@queue_group.command(name="list", description="Bir modun test sırasını görüntüle")
@app_commands.guild_only()
@app_commands.choices(mode=MODES)
async def q_list(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    entries = await database.queue_list(interaction.guild_id, mode.value)
    if not entries:
        await interaction.response.send_message(
            f"**{MODE_NAMES[mode.value]}** kuyruğu şu anda boş."
        )
        return

    active = next(
        (entry for entry in entries if entry["status"] in {"testing", "finishing"}),
        None,
    )
    waiting = [entry for entry in entries if entry["status"] == "waiting"]
    lines = [f"**{MODE_NAMES[mode.value]} — Test Kuyruğu**"]
    if active is not None:
        active_name = active["minecraft_name"] or "Minecraft hesabı bulunamadı"
        active_label = "Sonuç kaydediliyor" if active["status"] == "finishing" else "Testte"
        lines.append(f"🧪 {active_label}: <@{active['user_id']}> — `{active_name}`")
    else:
        lines.append("Şu anda aktif test yok.")
    if waiting:
        lines.append("**Bekleyenler:**")
        lines.extend(
            f"{position}. <@{entry['user_id']}> — `{entry['minecraft_name'] or 'hesap yok'}`"
            for position, entry in enumerate(waiting[:20], start=1)
        )
        if len(waiting) > 20:
            lines.append(f"… ve {len(waiting) - 20} oyuncu daha.")
    else:
        lines.append("Bekleyen oyuncu yok.")
    await interaction.response.send_message(
        "\n".join(lines), allowed_mentions=discord.AllowedMentions.none()
    )


@queue_group.command(name="next", description="Sıradaki oyuncuyu test için çağır (yetkili)")
@app_commands.guild_only()
@tier_staff_check()
@app_commands.choices(mode=MODES)
async def q_next(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    await interaction.response.defer(thinking=True)
    result = await database.queue_next(interaction.guild_id, mode.value)
    if result["status"] == "empty":
        await interaction.followup.send(
            f"**{MODE_NAMES[mode.value]}** kuyruğunda bekleyen oyuncu yok."
        )
        return
    if result["status"] == "active":
        active = result["entry"]
        message = (
            f"Bu modda zaten bir oyuncu testte: <@{active['user_id']}>. "
            "Mevcut testi `/q finish` veya `/q cancel` ile sonuçlandırın."
        )
        await interaction.followup.send(
            message, allowed_mentions=discord.AllowedMentions.none()
        )
        return

    entry = result["entry"]
    player = await database.get_player(interaction.guild_id, entry["user_id"])
    minecraft_name = player["minecraft_name"] if player else "Minecraft hesabı bulunamadı"
    await interaction.followup.send(
        f"🧪 **{MODE_NAMES[mode.value]} testi başladı!** Sıradaki oyuncu: "
        f"<@{entry['user_id']}> — **{minecraft_name}**.",
        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
    )


@queue_group.command(name="finish", description="Aktif testi tier vererek tamamla (yetkili)")
@app_commands.guild_only()
@tier_staff_check()
@app_commands.choices(mode=MODES, tier=TIERS)
async def q_finish(
    interaction: discord.Interaction,
    mode: app_commands.Choice[str],
    tier: app_commands.Choice[str],
):
    await interaction.response.defer(thinking=True)
    result = await database.queue_claim_finish(interaction.guild_id, mode.value)
    if result["status"] == "none":
        await interaction.followup.send(
            f"**{MODE_NAMES[mode.value]}** modunda tamamlanacak aktif test yok.",
            ephemeral=True,
        )
        return
    if result["status"] == "busy":
        await interaction.followup.send(
            "Bu testin tier sonucu başka bir işlem tarafından kaydediliyor. Biraz sonra tekrar dene.",
            ephemeral=True,
        )
        return

    entry = result["entry"]
    player = await database.get_player(interaction.guild_id, entry["user_id"])
    if player is None:
        await database.queue_restore_finish(entry["queue_id"])
        await interaction.followup.send(
            "Aktif oyuncunun Minecraft hesabı bağlı görünmüyor. `/link` sonrasında testi tekrar tamamlayın.",
            ephemeral=True,
        )
        return

    try:
        await database.set_tier(
            interaction.guild_id,
            entry["user_id"],
            mode.value,
            tier.value,
            interaction.user.id,
        )
    except aiosqlite.Error:
        logger.exception("Kuyruk testi tier sonucu veritabanına kaydedilemedi")
        try:
            await database.queue_restore_finish(entry["queue_id"])
        except aiosqlite.Error:
            logger.exception("Kuyruk testi durumu geri alınamadı")
        await interaction.followup.send(
            "Tier veritabanına kaydedilemedi; test açık bırakıldı. Daha sonra tekrar deneyin.",
            ephemeral=True,
        )
        return

    guild = interaction.guild
    member = guild.get_member(entry["user_id"])
    sync_error = None
    if member is None:
        try:
            member = await guild.fetch_member(entry["user_id"])
        except discord.HTTPException as error:
            logger.warning("Test oyuncusu sunucu üyesi olarak alınamadı: %s", error)
            sync_error = (
                "Tier veritabanına kaydedildi, ancak oyuncu sunucudan alınamadığı için "
                "Discord rolü eşitlenemedi."
            )
    if member is not None:
        sync_error = await sync_tier_role(
            guild,
            member,
            mode.value,
            tier.value,
            "MCTierList test sonucu",
        )

    try:
        closed = await database.queue_complete_finish(interaction.guild_id, entry["queue_id"])
    except aiosqlite.Error:
        logger.exception("Tier kaydedildi ancak test kuyruğu kapatılamadı")
        closed = False
    if not closed:
        sync_error = (sync_error + "\n" if sync_error else "") + (
            "Tier kaydedildi, ancak kuyruk kaydı kapatılamadı; bot yeniden başlatılınca "
            "test tekrar açık duruma alınır."
        )

    message = (
        f"✅ <@{entry['user_id']}> (**{player['minecraft_name']}**) için "
        f"**{MODE_NAMES[mode.value]} {tier.value}** sonucu kaydedildi."
    )
    if sync_error:
        message += f"\n⚠️ {sync_error}"
    await interaction.followup.send(
        message, allowed_mentions=discord.AllowedMentions.none()
    )


@queue_group.command(name="cancel", description="Aktif testi tier kaydetmeden iptal et (yetkili)")
@app_commands.guild_only()
@tier_staff_check()
@app_commands.choices(mode=MODES)
async def q_cancel(
    interaction: discord.Interaction,
    mode: app_commands.Choice[str],
    reason: str | None = None,
):
    result = await database.queue_cancel(interaction.guild_id, mode.value)
    if result is None:
        await interaction.response.send_message(
            f"**{MODE_NAMES[mode.value]}** modunda iptal edilecek aktif test yok.",
            ephemeral=True,
        )
        return
    if result["result"] == "finishing":
        await interaction.response.send_message(
            "Tier sonucu kaydedilmekte; bu işlem sırasında test iptal edilemez.",
            ephemeral=True,
        )
        return

    message = (
        f"**{MODE_NAMES[mode.value]}** test iptal edildi; <@{result['user_id']}> "
        "yeniden kuyruğa katılabilir. Tier kaydı yapılmadı."
    )
    if reason:
        message += f"\nNeden: {reason[:300]}"
    await interaction.response.send_message(
        message, allowed_mentions=discord.AllowedMentions.none()
    )


@queue_group.command(name="close", description="Bu test ticketını sil ve kuyruğu kapat")
@app_commands.guild_only()
async def q_close(interaction: discord.Interaction):
    channel = interaction.channel
    guild = interaction.guild
    member = interaction.user
    if not isinstance(channel, discord.TextChannel) or guild is None:
        await interaction.response.send_message(
            "Bu komut yalnızca test ticketı metin kanalında kullanılabilir.", ephemeral=True
        )
        return

    match = re.fullmatch(
        rf"q-({TICKET_MODE_PATTERN})-([A-Za-z0-9_]{{3,16}})",
        channel.name,
    )
    if match is None:
        await interaction.response.send_message(
            "Bu kanal tanınan bir test ticketı değil. `/q close` komutunu `q-mod-oyuncuadı` kanalında kullan.",
            ephemeral=True,
        )
        return

    try:
        entry = await database.queue_ticket_entry(guild.id, match.group(1), match.group(2))
    except aiosqlite.Error:
        logger.exception("Ticket kapatılırken kuyruk kaydı okunamadı")
        await interaction.response.send_message(
            "Kuyruk kaydı kontrol edilemedi; ticket silinmedi. Daha sonra tekrar dene.",
            ephemeral=True,
        )
        return

    is_staff = isinstance(member, discord.Member) and (
        member.guild_permissions.manage_guild
        or any(role.name == "Tier Tester" for role in member.roles)
    )
    if not is_staff and (entry is None or entry["user_id"] != member.id):
        await interaction.response.send_message(
            "Bu ticketı yalnızca başvuru sahibi veya Tier Tester / Sunucuyu Yönet yetkilisi kapatabilir.",
            ephemeral=True,
        )
        return
    if entry is not None and entry["status"] == "finishing":
        await interaction.response.send_message(
            "Tier sonucu kaydediliyor; işlem bitene kadar ticket kapatılamaz.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    try:
        await channel.delete(reason=f"MCTierList ticketı kapatıldı: {member}")
    except discord.Forbidden:
        await interaction.followup.send(
            "Ticket silinemedi. Botta **Manage Channels** iznini kontrol edin.", ephemeral=True
        )
        return
    except discord.HTTPException as error:
        logger.warning("Test ticketı silinemedi: %s", error)
        await interaction.followup.send(
            f"Ticket silinemedi (Discord HTTP {error.status}); tekrar deneyin.", ephemeral=True
        )
        return

    if entry is not None:
        try:
            removed = await database.queue_leave(guild.id, entry["user_id"])
        except aiosqlite.Error:
            logger.exception("Ticket silindi ancak kuyruk kaydı temizlenemedi")
            await interaction.followup.send(
                "Ticket silindi ancak kuyruk kaydı temizlenemedi. Oyuncu `/q leave` kullanmalı veya yetkili `/q cancel` ile temizlemeli.",
                ephemeral=True,
            )
            return
        if removed is not None and removed.get("result") == "finishing":
            await interaction.followup.send(
                "Ticket silindi ancak tier sonucu kaydedilmekte olduğu için kuyruk kaydı kaldı. İşlem bitince yetkili kontrol etmeli.",
                ephemeral=True,
            )
            return

    await interaction.followup.send("Ticket silindi ve ilgili kuyruk kaydı kapatıldı.", ephemeral=True)


bot.tree.add_command(queue_group)


@bot.tree.command(name="profile", description="Bir oyuncunun Minecraft tier profilini göster")
@app_commands.guild_only()
@app_commands.checks.cooldown(1, 3.0, key=lambda interaction: interaction.user.id)
async def profile(interaction: discord.Interaction, uye: discord.Member):
    player = await database.get_player(interaction.guild_id, uye.id)
    if player is None:
        await interaction.response.send_message(
            f"{uye.mention} henüz Minecraft hesabını bağlamamış.", ephemeral=True
        )
        return

    tiers = await database.get_tiers(interaction.guild_id, uye.id)
    embed = discord.Embed(
        title=f"{player['minecraft_name']} — Tier Profili",
        color=discord.Color.green(),
    )
    if tiers:
        for row in sorted(
            tiers,
            key=lambda item: (
                MODE_ORDER.get(item["mode"], len(MODE_ORDER)),
                TIER_ORDER.get(item["tier"], len(TIER_ORDER)),
            ),
        ):
            mode_name = MODE_NAMES.get(row["mode"], row["mode"].replace("_", " ").title())
            embed.add_field(name=mode_name, value=f"**{row['tier']}**", inline=True)
    else:
        embed.description = "Bu oyuncuya henüz tier atanmamış."
    embed.set_thumbnail(url=uye.display_avatar.url)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="leaderboard", description="Bir modun sunucu tier sıralamasını göster")
@app_commands.guild_only()
@app_commands.choices(mode=MODES)
@app_commands.checks.cooldown(1, 3.0, key=lambda interaction: interaction.user.id)
async def leaderboard(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    rows = await database.leaderboard(interaction.guild_id, mode.value)
    embed = discord.Embed(
        title=f"{MODE_NAMES[mode.value]} Tier Sıralaması",
        color=discord.Color.gold(),
    )
    if not rows:
        embed.description = "Bu modda henüz tierlı oyuncu yok."
    else:
        lines = [
            f"**{position}.** `{row['tier']}` — **{row['minecraft_name']}**"
            for position, row in enumerate(rows[:10], start=1)
        ]
        embed.description = "\n".join(lines)
        if len(rows) > 10:
            embed.set_footer(text=f"İlk 10 oyuncu gösteriliyor · Toplam {len(rows)} oyuncu")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="modes", description="Tier sistemindeki oyun modlarını göster")
@app_commands.guild_only()
async def modes(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Tier modları: " + ", ".join(choice.name for choice in MODES)
    )


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "Bu komut için sunucuyu yönetme yetkisine sahip olmalısın."
    elif isinstance(error, app_commands.CommandOnCooldown):
        message = f"Çok hızlı kullanıyorsun. {error.retry_after:.1f} saniye sonra tekrar dene."
    elif isinstance(error, app_commands.NoPrivateMessage):
        message = "Bu komut yalnızca bir sunucuda kullanılabilir."
    elif isinstance(error, app_commands.CheckFailure):
        message = "Bu komut için Sunucuyu Yönet yetkisi veya Tier Tester rolü gerekir."
    else:
        original = error.original if isinstance(error, app_commands.CommandInvokeError) else error
        logger.error(
            "Slash komutu başarısız oldu",
            exc_info=(type(original), original, original.__traceback__),
        )
        message = "Komut çalışırken bir hata oluştu. Lütfen daha sonra tekrar dene."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("DISCORD_TOKEN .env dosyasında tanımlı değil.")

bot.run(token)