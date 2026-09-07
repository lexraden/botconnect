/** Minimal subset of Telegram Bot API types used by Bot Connect. */

export interface TgUser {
  id: number;
  is_bot: boolean;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
}

export interface TgChat {
  id: number;
  type: "private" | "group" | "supergroup" | "channel";
  title?: string;
  username?: string;
  first_name?: string;
  is_forum?: boolean;
}

export interface TgPhotoSize {
  file_id: string;
  width: number;
  height: number;
}

export interface TgMessage {
  message_id: number;
  message_thread_id?: number;
  from?: TgUser;
  sender_chat?: TgChat;
  chat: TgChat;
  date: number;
  text?: string;
  caption?: string;
  photo?: TgPhotoSize[];
  video?: { file_id: string };
  document?: { file_id: string; file_name?: string };
  animation?: { file_id: string };
  audio?: { file_id: string };
  voice?: { file_id: string };
  sticker?: { file_id: string };
  reply_to_message?: TgMessage;
  new_chat_members?: TgUser[];
  left_chat_member?: TgUser;
  media_group_id?: string;
}

export interface TgCallbackQuery {
  id: string;
  from: TgUser;
  message?: TgMessage;
  data?: string;
}

export interface TgChatMember {
  status: "creator" | "administrator" | "member" | "restricted" | "left" | "kicked";
  user: TgUser;
}

export interface TgChatMemberUpdated {
  chat: TgChat;
  from: TgUser;
  date: number;
  old_chat_member: TgChatMember;
  new_chat_member: TgChatMember;
}

export interface TgChatJoinRequest {
  chat: TgChat;
  from: TgUser;
  user_chat_id: number;
  date: number;
}

export interface TgUpdate {
  update_id: number;
  message?: TgMessage;
  edited_message?: TgMessage;
  callback_query?: TgCallbackQuery;
  my_chat_member?: TgChatMemberUpdated;
  chat_member?: TgChatMemberUpdated;
  chat_join_request?: TgChatJoinRequest;
}

export interface InlineKeyboardButton {
  text: string;
  url?: string;
  callback_data?: string;
}

export interface InlineKeyboardMarkup {
  inline_keyboard: InlineKeyboardButton[][];
}

export interface ReplyKeyboardMarkup {
  keyboard: { text: string }[][];
  resize_keyboard?: boolean;
  is_persistent?: boolean;
}

export interface ReplyKeyboardRemove {
  remove_keyboard: true;
}

export type ReplyMarkup = InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove;

export type FileType = "photo" | "video" | "document" | "animation" | "audio" | "voice";

/** Extracts the "main" attachment from a message (largest photo, video, etc.) */
export function extractFile(m: TgMessage): { fileId: string; fileType: FileType } | null {
  if (m.photo?.length) return { fileId: m.photo[m.photo.length - 1].file_id, fileType: "photo" };
  if (m.video) return { fileId: m.video.file_id, fileType: "video" };
  if (m.animation) return { fileId: m.animation.file_id, fileType: "animation" };
  if (m.document) return { fileId: m.document.file_id, fileType: "document" };
  if (m.audio) return { fileId: m.audio.file_id, fileType: "audio" };
  if (m.voice) return { fileId: m.voice.file_id, fileType: "voice" };
  return null;
}

export function displayName(u: TgUser): string {
  const name = [u.first_name, u.last_name].filter(Boolean).join(" ").trim();
  return name || u.username || String(u.id);
}
