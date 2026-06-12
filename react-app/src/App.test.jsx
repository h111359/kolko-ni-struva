/**
 * App.test.jsx: Unit tests for the App root component.
 * Responsibilities: verify credential gating and top-level layout rendering.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';

const supabaseMock = vi.hoisted(() => ({ credentialsError: null }));

vi.mock('./lib/supabase', () => ({
  default: null,
  get credentialsError() {
    return supabaseMock.credentialsError;
  },
}));

vi.mock('./components/LandingPage', () => ({
  default: () => <div data-testid="landing-page">LandingPage</div>,
}));

import App from './App';

describe('App', () => {
  beforeEach(() => {
    supabaseMock.credentialsError = null;
    vi.clearAllMocks();
  });

  it('renders without crashing', async () => {
    await act(async () => { render(<App />); });
  });

  it('displays the credentials error when credentialsError is set', async () => {
    supabaseMock.credentialsError = 'Test credentials error message';
    await act(async () => { render(<App />); });
    expect(screen.getByText('Test credentials error message')).toBeInTheDocument();
  });

  it('does not render LandingPage when credentialsError is set', async () => {
    supabaseMock.credentialsError = 'Credentials missing';
    await act(async () => { render(<App />); });
    expect(screen.queryByTestId('landing-page')).not.toBeInTheDocument();
  });

  it('renders LandingPage immediately when credentials are valid', async () => {
    await act(async () => { render(<App />); });
    expect(screen.getByTestId('landing-page')).toBeInTheDocument();
  });

  it('renders the app title heading', async () => {
    await act(async () => { render(<App />); });
    expect(screen.getByRole('heading', { name: /Анализатор на Цени/ })).toBeInTheDocument();
  });

  it('renders the footer with kolkostruva.bg link', async () => {
    await act(async () => { render(<App />); });
    const link = screen.getByRole('link', { name: /kolkostruva\.bg/ });
    expect(link).toHaveAttribute('href', 'https://kolkostruva.bg/');
  });
});
