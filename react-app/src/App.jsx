/**
 * App.jsx: Root application component for the Kolko Ni Struva React app.
 * Renders the unified LandingPage and only blocks on credential validation.
 */
import './App.css';
import { credentialsError } from './lib/supabase';
import LandingPage from './components/LandingPage';

/**
 * Root application component. Renders the landing page immediately when
 * Supabase browser credentials are valid.
 *
 * @returns {JSX.Element} The full application layout.
 */
function App() {
  const loadError = credentialsError;

  return (
    <>
      <header>
        <h1>📊 Анализатор на Цени</h1>
        <p className="subtitle">Визуализация на данни от kolkostruva.bg</p>
      </header>

      <main>
        {loadError && <p className="error-text">{loadError}</p>}
        {!loadError && <LandingPage />}
      </main>

      <footer>
        <p>
          Данни от{' '}
          <a href="https://kolkostruva.bg/" target="_blank" rel="noreferrer">
            kolkostruva.bg
          </a>
        </p>
      </footer>
    </>
  );
}

export default App;


