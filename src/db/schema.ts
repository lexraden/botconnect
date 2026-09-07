import {
  pgTable,
  serial,
  bigint,
  text,
  boolean,
  integer,
  timestamp,
  numeric,
  uniqueIndex,
  index,
  jsonb,
} from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";

/**
 * Bot Connect v2 schema.
 *
 * Key differences vs v1:
 *  - bot tokens are encrypted at rest and NEVER used as foreign keys
 *  - every bot has a webhook secret (Telegram `secret_token`) instead of the token in the URL
 *  - channels are unique per (bot, chat) instead of globally
 *  - money is `numeric`, all timestamps are `timestamptz`
 */

// ---------- Accounts (owners who log into the dashboard) ----------
export const accounts = pgTable("accounts", {
  id: serial("id").primaryKey(),
  telegramId: bigint("telegram_id", { mode: "number" }).notNull().unique(),
  username: text("username"),
  firstName: text("first_name"),
  lastName: text("last_name"),
  languageCode: text("language_code").default("ru"),
  isAdmin: boolean("is_admin").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

// One-time login codes issued by the main bot (/login)
export const loginTokens = pgTable("login_tokens", {
  id: serial("id").primaryKey(),
  token: text("token").notNull().unique(),
  telegramId: bigint("telegram_id", { mode: "number" }).notNull(),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  usedAt: timestamp("used_at", { withTimezone: true }),
});

// ---------- User bots ----------
export const bots = pgTable(
  "bots",
  {
    id: serial("id").primaryKey(),
    ownerId: integer("owner_id")
      .notNull()
      .references(() => accounts.id, { onDelete: "cascade" }),
    telegramBotId: bigint("telegram_bot_id", { mode: "number" }).notNull().unique(),
    username: text("username").notNull(),
    title: text("title"),
    encryptedToken: text("encrypted_token").notNull(),
    webhookSecret: text("webhook_secret").notNull(),
    isActive: boolean("is_active").notNull().default(true),

    // Feedback settings
    greetingText: text("greeting_text"),
    greetingFileId: text("greeting_file_id"),
    greetingFileType: text("greeting_file_type"), // photo | video | document | animation
    forwardChatId: bigint("forward_chat_id", { mode: "number" }),

    // Counters (denormalized for the dashboard)
    receivedCount: integer("received_count").notNull().default(0),
    repliedCount: integer("replied_count").notNull().default(0),

    lastWebhookAt: timestamp("last_webhook_at", { withTimezone: true }),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("bots_owner_idx").on(t.ownerId)],
);

// Users of a specific user bot
export const botUsers = pgTable(
  "bot_users",
  {
    id: serial("id").primaryKey(),
    botId: integer("bot_id")
      .notNull()
      .references(() => bots.id, { onDelete: "cascade" }),
    telegramId: bigint("telegram_id", { mode: "number" }).notNull(),
    username: text("username"),
    firstName: text("first_name"),
    lastName: text("last_name"),
    languageCode: text("language_code"),
    isBanned: boolean("is_banned").notNull().default(false),
    isBlocked: boolean("is_blocked").notNull().default(false), // user blocked the bot
    lastSeenAt: timestamp("last_seen_at", { withTimezone: true }).notNull().defaultNow(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [
    uniqueIndex("bot_users_bot_tg_uq").on(t.botId, t.telegramId),
    index("bot_users_bot_idx").on(t.botId),
  ],
);

// Map "message forwarded to admin chat" -> original user, so admin replies route back.
// v1 parsed reply chains via Telegram forward metadata which breaks for privacy-protected users.
export const forwardedMessages = pgTable(
  "forwarded_messages",
  {
    id: serial("id").primaryKey(),
    botId: integer("bot_id")
      .notNull()
      .references(() => bots.id, { onDelete: "cascade" }),
    adminChatId: bigint("admin_chat_id", { mode: "number" }).notNull(),
    adminMessageId: integer("admin_message_id").notNull(),
    userTelegramId: bigint("user_telegram_id", { mode: "number" }).notNull(),
    userMessageId: integer("user_message_id").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [uniqueIndex("fwd_admin_msg_uq").on(t.botId, t.adminChatId, t.adminMessageId)],
);

// ---------- Menu buttons ----------
export const menuButtons = pgTable(
  "menu_buttons",
  {
    id: serial("id").primaryKey(),
    botId: integer("bot_id")
      .notNull()
      .references(() => bots.id, { onDelete: "cascade" }),
    parentId: integer("parent_id"), // nested inline menus
    text: text("text").notNull(),
    kind: text("kind").notNull().default("inline"), // inline | reply
    action: text("action").notNull().default("send"), // send | edit | url
    replyText: text("reply_text"),
    fileId: text("file_id"),
    fileType: text("file_type"),
    url: text("url"),
    command: text("command"), // e.g. "/prices"
    position: integer("position").notNull().default(0),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("menu_buttons_bot_idx").on(t.botId)],
);

// ---------- Mailings ----------
export const mailings = pgTable(
  "mailings",
  {
    id: serial("id").primaryKey(),
    botId: integer("bot_id")
      .notNull()
      .references(() => bots.id, { onDelete: "cascade" }),
    text: text("text"),
    fileId: text("file_id"),
    fileType: text("file_type"),
    buttonText: text("button_text"),
    buttonUrl: text("button_url"),
    scheduledAt: timestamp("scheduled_at", { withTimezone: true }).notNull(),
    status: text("status").notNull().default("scheduled"), // scheduled | running | done | failed | cancelled
    sentCount: integer("sent_count").notNull().default(0),
    failedCount: integer("failed_count").notNull().default(0),
    lastUserId: bigint("last_user_id", { mode: "number" }).notNull().default(0), // cursor for resumable batches
    error: text("error"),
    startedAt: timestamp("started_at", { withTimezone: true }),
    finishedAt: timestamp("finished_at", { withTimezone: true }),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("mailings_due_idx").on(t.status, t.scheduledAt)],
);

// ---------- Subscriptions & payments ----------
export const subscriptions = pgTable(
  "subscriptions",
  {
    id: serial("id").primaryKey(),
    botId: integer("bot_id")
      .notNull()
      .references(() => bots.id, { onDelete: "cascade" }),
    months: integer("months").notNull(),
    price: numeric("price", { precision: 12, scale: 2 }).notNull(),
    currency: text("currency").notNull().default("USDT"),
    startsAt: timestamp("starts_at", { withTimezone: true }).notNull().defaultNow(),
    endsAt: timestamp("ends_at", { withTimezone: true }).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("subscriptions_bot_ends_idx").on(t.botId, t.endsAt)],
);

export const payments = pgTable("payments", {
  id: serial("id").primaryKey(),
  botId: integer("bot_id")
    .notNull()
    .references(() => bots.id, { onDelete: "cascade" }),
  accountId: integer("account_id")
    .notNull()
    .references(() => accounts.id, { onDelete: "cascade" }),
  provider: text("provider").notNull().default("cryptobot"),
  invoiceId: text("invoice_id").notNull().unique(),
  payUrl: text("pay_url"),
  months: integer("months").notNull(),
  amount: numeric("amount", { precision: 12, scale: 2 }).notNull(),
  currency: text("currency").notNull().default("USDT"),
  status: text("status").notNull().default("pending"), // pending | paid | expired | cancelled
  paidAt: timestamp("paid_at", { withTimezone: true }),
  expiresAt: timestamp("expires_at", { withTimezone: true }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

// ---------- Channels ----------
export const channels = pgTable(
  "channels",
  {
    id: serial("id").primaryKey(),
    botId: integer("bot_id")
      .notNull()
      .references(() => bots.id, { onDelete: "cascade" }),
    chatId: bigint("chat_id", { mode: "number" }).notNull(),
    title: text("title").notNull(),
    type: text("type").notNull().default("channel"), // channel | supergroup
    autoAccept: boolean("auto_accept").notNull().default(true),
    captcha: boolean("captcha").notNull().default(false),
    captchaButtonText: text("captcha_button_text"),
    isConnected: boolean("is_connected").notNull().default(true),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [uniqueIndex("channels_bot_chat_uq").on(t.botId, t.chatId)],
);

export const channelMessages = pgTable(
  "channel_messages",
  {
    id: serial("id").primaryKey(),
    channelId: integer("channel_id")
      .notNull()
      .references(() => channels.id, { onDelete: "cascade" }),
    kind: text("kind").notNull(), // greeting | farewell | captcha
    languageCode: text("language_code").notNull().default("any"),
    text: text("text"),
    fileId: text("file_id"),
    fileType: text("file_type"),
    // [{ text, url, row }]
    buttons: jsonb("buttons").$type<{ text: string; url: string; row: number }[]>().notNull().default([]),
  },
  (t) => [uniqueIndex("channel_messages_uq").on(t.channelId, t.kind, t.languageCode)],
);

// Pending join requests waiting for captcha click
export const pendingJoinRequests = pgTable(
  "pending_join_requests",
  {
    id: serial("id").primaryKey(),
    channelId: integer("channel_id")
      .notNull()
      .references(() => channels.id, { onDelete: "cascade" }),
    userTelegramId: bigint("user_telegram_id", { mode: "number" }).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [uniqueIndex("pending_join_uq").on(t.channelId, t.userTelegramId)],
);

// Idempotency guard for Telegram updates (Telegram retries on non-200)
export const processedUpdates = pgTable(
  "processed_updates",
  {
    botId: integer("bot_id").notNull(),
    updateId: bigint("update_id", { mode: "number" }).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [uniqueIndex("processed_updates_uq").on(t.botId, t.updateId)],
);

// ---------- Relations ----------
export const accountsRelations = relations(accounts, ({ many }) => ({
  bots: many(bots),
}));

export const botsRelations = relations(bots, ({ one, many }) => ({
  owner: one(accounts, { fields: [bots.ownerId], references: [accounts.id] }),
  users: many(botUsers),
  buttons: many(menuButtons),
  mailings: many(mailings),
  subscriptions: many(subscriptions),
  channels: many(channels),
}));

export const channelsRelations = relations(channels, ({ one, many }) => ({
  bot: one(bots, { fields: [channels.botId], references: [bots.id] }),
  messages: many(channelMessages),
}));

export const channelMessagesRelations = relations(channelMessages, ({ one }) => ({
  channel: one(channels, { fields: [channelMessages.channelId], references: [channels.id] }),
}));

export type Bot = typeof bots.$inferSelect;
export type BotUser = typeof botUsers.$inferSelect;
export type MenuButton = typeof menuButtons.$inferSelect;
export type Mailing = typeof mailings.$inferSelect;
export type Channel = typeof channels.$inferSelect;
export type ChannelMessage = typeof channelMessages.$inferSelect;
export type Account = typeof accounts.$inferSelect;
