/**
 * Copy data from a v1 (Python/aiogram) database into a v2 one.
 *
 *   V1_DATABASE_URL=postgres://…/v1  DATABASE_URL=postgres://…/v2 \
 *     ENCRYPTION_KEY=…  npm run migrate:v1 -- [--dry-run]
 *
 * The two databases must be separate: v1 and v2 both have `mailings` and
 * `channel_messages` tables with different columns, so they cannot share one.
 *
 * Safe to re-run: every insert is ON CONFLICT DO NOTHING, so a second pass adds
 * only what was missing. Webhooks are NOT touched — after the migration press
 * "Переподключить вебхук" on each bot's page (or run setWebhook yourself), which
 * is also what moves traffic from v1 to v2 when you are ready.
 */
import { Client } from "pg";
import { encrypt, randomToken } from "../src/lib/crypto";

const DRY = process.argv.includes("--dry-run");

function required(name: string): string {
  const v = process.env[name];
  if (!v) {
    console.error(`${name} is required`);
    process.exit(1);
  }
  return v;
}

/** v1 stores media as "photo:AgAC…"; v2 keeps type and id apart. */
function splitMedia(value: string | null): { fileType: string | null; fileId: string | null } {
  if (!value) return { fileType: null, fileId: null };
  const idx = value.indexOf(":");
  if (idx < 0) return { fileType: null, fileId: value };
  const fileType = value.slice(0, idx);
  const fileId = value.slice(idx + 1);
  if (!fileId || fileType === "text") return { fileType: null, fileId: null };
  return { fileType, fileId };
}

function buttonKind(v1Type: string | null): string {
  return v1Type === "regular" ? "reply" : "inline";
}

function buttonAction(v1Action: string | null): string {
  if (v1Action === "link") return "url";
  if (v1Action === "replace") return "edit";
  return "send";
}

async function main() {
  const v1Url = required("V1_DATABASE_URL");
  const v2Url = required("DATABASE_URL");
  if (v1Url === v2Url) {
    console.error("V1_DATABASE_URL and DATABASE_URL must differ: both schemas define `mailings` and `channel_messages`");
    process.exit(1);
  }
  required("ENCRYPTION_KEY"); // tokens are re-encrypted with it; a wrong key here means unusable bots

  const v1 = new Client({ connectionString: v1Url });
  const v2 = new Client({ connectionString: v2Url });
  await v1.connect();
  await v2.connect();

  const stats: Record<string, number> = {};
  const count = (what: string, n = 1) => (stats[what] = (stats[what] ?? 0) + n);

  // In a dry run nothing is written, but ids still have to flow so the counts
  // downstream (users, channels, messages) are real numbers and not zeros.
  let fakeId = 0;
  const insertId = async (sql: string, params: unknown[]): Promise<number | undefined> => {
    if (DRY) return ++fakeId;
    const res = await v2.query<{ id: number }>(sql, params);
    return res.rows[0]?.id;
  };
  const insert = async (sql: string, params: unknown[]) => {
    if (!DRY) await v2.query(sql, params);
  };

  try {
    if (!DRY) await v2.query("begin");

    // ---------- accounts ----------
    // v1 has no accounts table: owners are user_bots.user_id, with names in main_bot_users.
    const owners = await v1.query<{
      user_id: string;
      username: string | null;
      first_name: string | null;
      last_name: string | null;
      language_code: string | null;
    }>(`
      select distinct on (b.user_id)
             b.user_id, m.username, m.first_name, m.last_name, m.language_code
        from user_bots b
        left join main_bot_users m on m.user_id = b.user_id
       order by b.user_id
    `);

    const accountIdByTelegramId = new Map<string, number>();
    for (const o of owners.rows) {
      const id = await insertId(
        `insert into accounts (telegram_id, username, first_name, last_name, language_code)
         values ($1, $2, $3, $4, coalesce($5, 'ru'))
         on conflict (telegram_id) do update set username = excluded.username
         returning id`,
        [o.user_id, o.username, o.first_name, o.last_name, o.language_code],
      );
      if (!id) continue;
      accountIdByTelegramId.set(String(o.user_id), id);
      count("accounts");
    }

    // ---------- bots ----------
    const v1Bots = await v1.query<{
      id: number;
      user_id: string;
      bot_token: string;
      bot_username: string;
      greeting_message: string | null;
      greeting_file: string | null;
      sent_messages_to: string | null;
      sent_messages_count: number | null;
      replied_messages_count: number | null;
      is_started: boolean | null;
    }>(`select * from user_bots order by id`);

    const botIdByToken = new Map<string, number>();
    const botIdByV1Id = new Map<number, number>();

    for (const b of v1Bots.rows) {
      const telegramBotId = Number(b.bot_token.split(":")[0]);
      if (!Number.isInteger(telegramBotId) || telegramBotId <= 0) {
        console.warn(`  ! bot ${b.id} (@${b.bot_username}): token has no numeric id, skipped`);
        continue;
      }
      const greeting = splitMedia(b.greeting_file);
      const ownerId = accountIdByTelegramId.get(String(b.user_id));
      if (!ownerId) {
        console.warn(`  ! bot ${b.id} (@${b.bot_username}): owner ${b.user_id} missing, skipped`);
        continue;
      }
      let botId = await insertId(
        `insert into bots (owner_id, telegram_bot_id, username, encrypted_token, webhook_secret,
                           is_active, greeting_text, greeting_file_id, greeting_file_type,
                           forward_chat_id, received_count, replied_count)
         values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
         on conflict (telegram_bot_id) do nothing
         returning id`,
        [
          ownerId,
          telegramBotId,
          b.bot_username,
          encrypt(b.bot_token),
          randomToken(),
          b.is_started ?? true,
          b.greeting_message,
          greeting.fileId,
          greeting.fileType,
          b.sent_messages_to,
          b.sent_messages_count ?? 0,
          b.replied_messages_count ?? 0,
        ],
      );
      if (!botId && !DRY) {
        const existing = await v2.query<{ id: number }>(`select id from bots where telegram_bot_id = $1`, [telegramBotId]);
        botId = existing.rows[0]?.id;
      }
      if (!botId) continue;
      botIdByToken.set(b.bot_token, botId);
      botIdByV1Id.set(b.id, botId);
      count("bots");
    }

    // ---------- bot users ----------
    const v1Users = await v1.query<{
      bot_token: string;
      user_id: string;
      username: string | null;
      first_name: string | null;
      last_name: string | null;
      language_code: string | null;
      is_banned: boolean | null;
      is_blocked: boolean | null;
      created_at: string | null;
    }>(`select * from users`);

    for (const u of v1Users.rows) {
      const botId = botIdByToken.get(u.bot_token);
      if (!botId) continue;
      await insert(
        `insert into bot_users (bot_id, telegram_id, username, first_name, last_name, language_code,
                                is_banned, is_blocked, created_at)
         values ($1,$2,$3,$4,$5,$6,$7,$8, coalesce($9::timestamptz, now()))
         on conflict (bot_id, telegram_id) do nothing`,
        [botId, u.user_id, u.username, u.first_name, u.last_name, u.language_code,
         u.is_banned ?? false, u.is_blocked ?? false, u.created_at],
      );
      count("bot_users");
    }

    // ---------- menu buttons ----------
    const v1Buttons = await v1.query<{
      id: number;
      bot_token: string;
      button_text: string;
      reply_message: string | null;
      file_id: string | null;
      button_type: string | null;
      action_type: string | null;
      command: string | null;
    }>(`select * from bot_menu_buttons order by id`);

    // menu_buttons has no natural key, so a re-run would duplicate them:
    // skip any bot that already has buttons instead.
    const botsWithButtons = new Set<number>();
    if (!DRY) {
      const existing = await v2.query<{ bot_id: number }>(`select distinct bot_id from menu_buttons`);
      for (const r of existing.rows) botsWithButtons.add(r.bot_id);
    }

    for (const btn of v1Buttons.rows) {
      const botId = botIdByToken.get(btn.bot_token);
      if (!botId || botsWithButtons.has(botId)) continue;
      const action = buttonAction(btn.action_type);
      await insert(
        `insert into menu_buttons (bot_id, text, kind, action, reply_text, url, file_id, command)
         values ($1,$2,$3,$4,$5,$6,$7,$8)`,
        [
          botId,
          btn.button_text,
          buttonKind(btn.button_type),
          action,
          action === "url" ? null : btn.reply_message,
          action === "url" ? btn.reply_message : null,
          btn.file_id,
          btn.command,
        ],
      );
      count("menu_buttons");
    }

    // ---------- channels ----------
    // Positive chat ids are private chats a v1 bug registered as channels; they are junk.
    const v1Channels = await v1.query<{
      id: number;
      bot_id: number;
      channel_name: string;
      channel_id: string;
      auto_accept: boolean | null;
      captcha: boolean | null;
      captcha_button_text: string | null;
    }>(`select * from bots_channels where channel_id < 0 order by id`);

    const channelIdByV1Id = new Map<number, number>();
    for (const ch of v1Channels.rows) {
      const botId = botIdByV1Id.get(ch.bot_id);
      if (!botId) continue;
      let channelId = await insertId(
        `insert into channels (bot_id, chat_id, title, type, auto_accept, captcha, captcha_button_text)
         values ($1,$2,$3,$4,$5,$6,$7)
         on conflict (bot_id, chat_id) do nothing
         returning id`,
        [
          botId,
          ch.channel_id,
          ch.channel_name,
          String(ch.channel_id).startsWith("-100") ? "channel" : "supergroup",
          ch.auto_accept ?? true,
          ch.captcha ?? false,
          ch.captcha_button_text,
        ],
      );
      if (!channelId && !DRY) {
        const existing = await v2.query<{ id: number }>(
          `select id from channels where bot_id = $1 and chat_id = $2`, [botId, ch.channel_id]);
        channelId = existing.rows[0]?.id;
      }
      if (!channelId) continue;
      channelIdByV1Id.set(ch.id, channelId);
      count("channels");
    }

    // ---------- channel messages (+ their buttons, which v2 keeps as jsonb) ----------
    const v1ChannelMessages = await v1.query<{
      id: number;
      channel_id: number | string;
      language_code: string;
      message_type: string;
      message_text: string | null;
      message_file: string | null;
    }>(`select * from channel_messages order by id`);

    const v1MessageButtons = await v1.query<{
      message_id: number;
      button_text: string;
      button_url: string;
      row: number | null;
    }>(`select * from channel_message_buttons order by row, id`);

    const buttonsByMessage = new Map<number, { text: string; url: string; row: number }[]>();
    for (const b of v1MessageButtons.rows) {
      const list = buttonsByMessage.get(b.message_id) ?? [];
      list.push({ text: b.button_text, url: b.button_url, row: b.row ?? 0 });
      buttonsByMessage.set(b.message_id, list);
    }

    for (const m of v1ChannelMessages.rows) {
      // v1 declares this column BIGINT, and the driver hands bigints back as strings
      const channelId = channelIdByV1Id.get(Number(m.channel_id));
      if (!channelId) continue;
      const media = splitMedia(m.message_file);
      await insert(
        `insert into channel_messages (channel_id, kind, language_code, text, file_id, file_type, buttons)
         values ($1,$2,$3,$4,$5,$6,$7::jsonb)
         on conflict (channel_id, kind, language_code) do nothing`,
        [
          channelId,
          m.message_type === "farewell" ? "farewell" : "greeting",
          m.language_code === "all" ? "any" : m.language_code,
          m.message_text,
          media.fileId,
          media.fileType,
          JSON.stringify(buttonsByMessage.get(m.id) ?? []),
        ],
      );
      count("channel_messages");
    }

    // ---------- subscriptions (only the ones still running) ----------
    const v1Subs = await v1.query<{
      bot_id: number;
      subscription_months: number;
      subscription_price: number | null;
      start_date: string | null;
      end_date: string;
    }>(`select * from bot_subscriptions where end_date > now() order by id`);

    for (const s of v1Subs.rows) {
      const botId = botIdByV1Id.get(s.bot_id);
      if (!botId) continue;
      const inserted = await insertId(
        `insert into subscriptions (bot_id, months, price, currency, starts_at, ends_at)
         select $1,$2,$3,'RUB', coalesce($4::timestamptz, now()), $5::timestamptz
          where not exists (
                select 1 from subscriptions where bot_id = $1 and ends_at = $5::timestamptz)
         returning id`,
        [botId, s.subscription_months, s.subscription_price ?? 0, s.start_date, s.end_date],
      );
      if (inserted) count("subscriptions");
    }

    if (!DRY) await v2.query("commit");

    console.log(DRY ? "\nDry run — nothing written:" : "\nMigrated:");
    for (const [what, n] of Object.entries(stats)) console.log(`  ${what.padEnd(18)} ${n}`);
    if (!DRY) {
      console.log("\nWebhooks were left alone. Point each bot at v2 when you are ready:");
      console.log("  dashboard → bot → «Переподключить вебхук»");
    }
  } catch (e) {
    if (!DRY) await v2.query("rollback").catch(() => {});
    throw e;
  } finally {
    await v1.end();
    await v2.end();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
