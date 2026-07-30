/**
 * Optional browser Supabase client (Auth + direct Postgres REST).
 * Cloud is used when VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY are set.
 * AI still goes through FastAPI; this is for auth/data sync.
 */

import { createClient } from "@supabase/supabase-js";

const url = (import.meta.env.VITE_SUPABASE_URL || "").trim();
const anon = (import.meta.env.VITE_SUPABASE_ANON_KEY || "").trim();

export const supabaseEnabled = Boolean(url && anon);

export const supabase = supabaseEnabled
  ? createClient(url, anon, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null;
