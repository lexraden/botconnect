import "dotenv/config";
import type { Config } from "drizzle-kit";

/**
 * The URL comes from the environment: a hardcoded one silently pointed
 * `drizzle-kit migrate` at localhost instead of the database it was given.
 */
export default {
  dialect: "postgresql",
  schema: "./src/db/schema.ts",
  out: "./drizzle",
  dbCredentials: {
    url: process.env.DATABASE_URL ?? "postgresql://postgres:postgres@127.0.0.1:5432/app_db",
  },
} satisfies Config;
