CREATE TABLE "accounts" (
	"id" serial PRIMARY KEY NOT NULL,
	"telegram_id" bigint NOT NULL,
	"username" text,
	"first_name" text,
	"last_name" text,
	"language_code" text DEFAULT 'ru',
	"is_admin" boolean DEFAULT false NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "accounts_telegram_id_unique" UNIQUE("telegram_id")
);
--> statement-breakpoint
CREATE TABLE "bot_users" (
	"id" serial PRIMARY KEY NOT NULL,
	"bot_id" integer NOT NULL,
	"telegram_id" bigint NOT NULL,
	"username" text,
	"first_name" text,
	"last_name" text,
	"language_code" text,
	"is_banned" boolean DEFAULT false NOT NULL,
	"is_blocked" boolean DEFAULT false NOT NULL,
	"last_seen_at" timestamp with time zone DEFAULT now() NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "bots" (
	"id" serial PRIMARY KEY NOT NULL,
	"owner_id" integer NOT NULL,
	"telegram_bot_id" bigint NOT NULL,
	"username" text NOT NULL,
	"title" text,
	"encrypted_token" text NOT NULL,
	"webhook_secret" text NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"greeting_text" text,
	"greeting_file_id" text,
	"greeting_file_type" text,
	"forward_chat_id" bigint,
	"received_count" integer DEFAULT 0 NOT NULL,
	"replied_count" integer DEFAULT 0 NOT NULL,
	"last_webhook_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "bots_telegram_bot_id_unique" UNIQUE("telegram_bot_id")
);
--> statement-breakpoint
CREATE TABLE "channel_messages" (
	"id" serial PRIMARY KEY NOT NULL,
	"channel_id" integer NOT NULL,
	"kind" text NOT NULL,
	"language_code" text DEFAULT 'any' NOT NULL,
	"text" text,
	"file_id" text,
	"file_type" text,
	"buttons" jsonb DEFAULT '[]'::jsonb NOT NULL
);
--> statement-breakpoint
CREATE TABLE "channels" (
	"id" serial PRIMARY KEY NOT NULL,
	"bot_id" integer NOT NULL,
	"chat_id" bigint NOT NULL,
	"title" text NOT NULL,
	"type" text DEFAULT 'channel' NOT NULL,
	"auto_accept" boolean DEFAULT true NOT NULL,
	"captcha" boolean DEFAULT false NOT NULL,
	"captcha_button_text" text,
	"is_connected" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "forwarded_messages" (
	"id" serial PRIMARY KEY NOT NULL,
	"bot_id" integer NOT NULL,
	"admin_chat_id" bigint NOT NULL,
	"admin_message_id" integer NOT NULL,
	"user_telegram_id" bigint NOT NULL,
	"user_message_id" integer NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "login_tokens" (
	"id" serial PRIMARY KEY NOT NULL,
	"token" text NOT NULL,
	"telegram_id" bigint NOT NULL,
	"expires_at" timestamp with time zone NOT NULL,
	"used_at" timestamp with time zone,
	CONSTRAINT "login_tokens_token_unique" UNIQUE("token")
);
--> statement-breakpoint
CREATE TABLE "mailings" (
	"id" serial PRIMARY KEY NOT NULL,
	"bot_id" integer NOT NULL,
	"text" text,
	"file_id" text,
	"file_type" text,
	"button_text" text,
	"button_url" text,
	"scheduled_at" timestamp with time zone NOT NULL,
	"status" text DEFAULT 'scheduled' NOT NULL,
	"sent_count" integer DEFAULT 0 NOT NULL,
	"failed_count" integer DEFAULT 0 NOT NULL,
	"last_user_id" bigint DEFAULT 0 NOT NULL,
	"error" text,
	"started_at" timestamp with time zone,
	"finished_at" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "menu_buttons" (
	"id" serial PRIMARY KEY NOT NULL,
	"bot_id" integer NOT NULL,
	"parent_id" integer,
	"text" text NOT NULL,
	"kind" text DEFAULT 'inline' NOT NULL,
	"action" text DEFAULT 'send' NOT NULL,
	"reply_text" text,
	"file_id" text,
	"file_type" text,
	"url" text,
	"command" text,
	"position" integer DEFAULT 0 NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "payments" (
	"id" serial PRIMARY KEY NOT NULL,
	"bot_id" integer NOT NULL,
	"account_id" integer NOT NULL,
	"provider" text DEFAULT 'cryptobot' NOT NULL,
	"invoice_id" text NOT NULL,
	"pay_url" text,
	"months" integer NOT NULL,
	"amount" numeric(12, 2) NOT NULL,
	"currency" text DEFAULT 'USDT' NOT NULL,
	"status" text DEFAULT 'pending' NOT NULL,
	"paid_at" timestamp with time zone,
	"expires_at" timestamp with time zone NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "payments_invoice_id_unique" UNIQUE("invoice_id")
);
--> statement-breakpoint
CREATE TABLE "pending_join_requests" (
	"id" serial PRIMARY KEY NOT NULL,
	"channel_id" integer NOT NULL,
	"user_telegram_id" bigint NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "processed_updates" (
	"bot_id" integer NOT NULL,
	"update_id" bigint NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "subscriptions" (
	"id" serial PRIMARY KEY NOT NULL,
	"bot_id" integer NOT NULL,
	"months" integer NOT NULL,
	"price" numeric(12, 2) NOT NULL,
	"currency" text DEFAULT 'USDT' NOT NULL,
	"starts_at" timestamp with time zone DEFAULT now() NOT NULL,
	"ends_at" timestamp with time zone NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "bot_users" ADD CONSTRAINT "bot_users_bot_id_bots_id_fk" FOREIGN KEY ("bot_id") REFERENCES "public"."bots"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "bots" ADD CONSTRAINT "bots_owner_id_accounts_id_fk" FOREIGN KEY ("owner_id") REFERENCES "public"."accounts"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "channel_messages" ADD CONSTRAINT "channel_messages_channel_id_channels_id_fk" FOREIGN KEY ("channel_id") REFERENCES "public"."channels"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "channels" ADD CONSTRAINT "channels_bot_id_bots_id_fk" FOREIGN KEY ("bot_id") REFERENCES "public"."bots"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "forwarded_messages" ADD CONSTRAINT "forwarded_messages_bot_id_bots_id_fk" FOREIGN KEY ("bot_id") REFERENCES "public"."bots"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "mailings" ADD CONSTRAINT "mailings_bot_id_bots_id_fk" FOREIGN KEY ("bot_id") REFERENCES "public"."bots"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "menu_buttons" ADD CONSTRAINT "menu_buttons_bot_id_bots_id_fk" FOREIGN KEY ("bot_id") REFERENCES "public"."bots"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "payments" ADD CONSTRAINT "payments_bot_id_bots_id_fk" FOREIGN KEY ("bot_id") REFERENCES "public"."bots"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "payments" ADD CONSTRAINT "payments_account_id_accounts_id_fk" FOREIGN KEY ("account_id") REFERENCES "public"."accounts"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "pending_join_requests" ADD CONSTRAINT "pending_join_requests_channel_id_channels_id_fk" FOREIGN KEY ("channel_id") REFERENCES "public"."channels"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "subscriptions" ADD CONSTRAINT "subscriptions_bot_id_bots_id_fk" FOREIGN KEY ("bot_id") REFERENCES "public"."bots"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE UNIQUE INDEX "bot_users_bot_tg_uq" ON "bot_users" USING btree ("bot_id","telegram_id");--> statement-breakpoint
CREATE INDEX "bot_users_bot_idx" ON "bot_users" USING btree ("bot_id");--> statement-breakpoint
CREATE INDEX "bots_owner_idx" ON "bots" USING btree ("owner_id");--> statement-breakpoint
CREATE UNIQUE INDEX "channel_messages_uq" ON "channel_messages" USING btree ("channel_id","kind","language_code");--> statement-breakpoint
CREATE UNIQUE INDEX "channels_bot_chat_uq" ON "channels" USING btree ("bot_id","chat_id");--> statement-breakpoint
CREATE UNIQUE INDEX "fwd_admin_msg_uq" ON "forwarded_messages" USING btree ("bot_id","admin_chat_id","admin_message_id");--> statement-breakpoint
CREATE INDEX "mailings_due_idx" ON "mailings" USING btree ("status","scheduled_at");--> statement-breakpoint
CREATE INDEX "menu_buttons_bot_idx" ON "menu_buttons" USING btree ("bot_id");--> statement-breakpoint
CREATE UNIQUE INDEX "pending_join_uq" ON "pending_join_requests" USING btree ("channel_id","user_telegram_id");--> statement-breakpoint
CREATE UNIQUE INDEX "processed_updates_uq" ON "processed_updates" USING btree ("bot_id","update_id");--> statement-breakpoint
CREATE INDEX "subscriptions_bot_ends_idx" ON "subscriptions" USING btree ("bot_id","ends_at");