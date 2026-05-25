/**
 * supabase.js: Supabase client singleton for the Kolko Ni Struva React app.
 * Provides a single shared client instance loaded from Vite environment variables.
 * Responsibilities: initialise and export the Supabase client used by all data-service functions.
 * Environment variables are loaded from the project-root .env file (prefixed VITE_).
 */
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabasePublishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

// Export a descriptive error so App.jsx can surface it instead of silently crashing.
// Check for missing credentials first, then validate the key prefix/format.
export const credentialsError = (() => {
  if (!supabaseUrl || !supabasePublishableKey) {
    return 'Липсват Supabase credentials. Създайте или попълнете .env файла в корена на проекта с VITE_SUPABASE_URL и VITE_SUPABASE_PUBLISHABLE_KEY.';
  }
  // Reject server-side secret keys — they bypass Row Level Security and must never reach the browser.
  if (
    supabasePublishableKey.startsWith('sb_secret_') ||
    // Reject JWT-format keys (exactly 3 dot-separated segments): the legacy anon key format.
    supabasePublishableKey.split('.').length === 3
  ) {
    return 'Невалиден Supabase ключ. VITE_SUPABASE_PUBLISHABLE_KEY трябва да започва с "sb_publishable_". Не поставяйте "sb_secret_" ключ в браузъра.';
  }
  return null;
})();

/**
 * Shared Supabase client instance, or null when credentials are absent or invalid.
 * Uses the public publishable key — no secret or service-role key is embedded here.
 */
const supabase = credentialsError ? null : createClient(supabaseUrl, supabasePublishableKey);

export default supabase;
