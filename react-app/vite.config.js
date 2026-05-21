/**
 * vite.config.js: Vite build configuration for the Kolko Ni Struva React application.
 * Configures React plugin and base settings for Netlify deployment.
 * Environment variables are loaded from the repository root .env file via envDir config.
 * Test environment is configured for Vitest with jsdom and @testing-library/jest-dom matchers.
 */
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // Load environment variables from the repository root .env file.
  // Vite only exposes variables prefixed with VITE_ to the client.
  envDir: '../',
  test: {
    // Use jsdom to simulate a browser DOM environment for React component tests.
    environment: 'jsdom',
    // Automatically import @testing-library/jest-dom matchers in every test file.
    setupFiles: ['./src/test-setup.js'],
    // Expose Vitest globals (describe, it, expect, vi) without explicit imports.
    globals: true,
  },
});
