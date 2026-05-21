/**
 * HomePage.test.jsx: Smoke render test for the HomePage component.
 * Part of the kolko-ni-struva React app test suite (request R-20260425-2313).
 * Verifies that HomePage renders without errors and displays expected headings.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import HomePage from './HomePage';

// HomePage is stateless and has no external dependencies; no mocking required.
vi.mock('../lib/supabase', () => ({ default: null, credentialsError: null }));

describe('HomePage', () => {
  it('renders without crashing', () => {
    render(<HomePage />);
  });

  it('displays the welcome heading', () => {
    render(<HomePage />);
    // The Bulgarian welcome heading must be present in the DOM.
    expect(screen.getByText(/добре дошли/i)).toBeInTheDocument();
  });

  it('renders the three feature cards', () => {
    render(<HomePage />);
    const cards = document.querySelectorAll('.feature-card');
    expect(cards).toHaveLength(3);
  });
});
