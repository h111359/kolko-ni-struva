/**
 * supabase.js: Supabase client singleton for the Kolko Ni Struva React app.
 * Provides a single shared client instance loaded from Vite environment variables.
 * Responsibilities: initialise and export the Supabase client used by all data-service functions.
 * Environment variables are loaded from the project-root .env file (prefixed VITE_).
 */
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Export a descriptive error so App.jsx can surface it instead of silently crashing.
export const credentialsError =
  !supabaseUrl || !supabaseAnonKey
    ? 'Липсват Supabase credentials. Създайте или попълнете .env файла в корена на проекта с VITE_SUPABASE_URL и VITE_SUPABASE_ANON_KEY.'
    : null;

/**
 * Shared Supabase client instance, or null when credentials are absent.
 * Uses the public anon key — no service role key is embedded here.
 */
const supabase = credentialsError ? null : createClient(supabaseUrl, supabaseAnonKey);

export default supabase;
