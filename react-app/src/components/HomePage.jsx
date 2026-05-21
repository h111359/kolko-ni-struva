/**
 * HomePage.jsx: Landing page component for the Kolko Ni Struva React app.
 * Renders the welcome heading, intro text, three feature cards, and CTA section.
 * Matches the legacy app's home section layout exactly.
 */

/**
 * Stateless landing page component. Requires no props; all content is static.
 *
 * @returns {JSX.Element} The landing page with feature cards and CTA.
 */
function HomePage() {
  return (
    <div className="landing-page">
      <div className="landing-content">
        <h2>Добре дошли в Анализатора на Цени</h2>
        <p className="intro-text">
          Този инструмент ви помага да анализирате и сравнявате цените на хранителни продукти
          в различни търговски вериги и градове из България, използвайки отворените данни от{' '}
          <a href="https://kolkostruva.bg/" target="_blank" rel="noreferrer">
            kolkostruva.bg
          </a>
          .
        </p>

        <div className="features">
          <div className="feature-card">
            <div className="feature-icon">📈</div>
            <h3>Цени по категория</h3>
            <p>
              Вижте средната цена на различните категории продукти във вашия град.
              Сравнете цените между категориите с интерактивна графика.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">📋</div>
            <h3>Търсене на продукти</h3>
            <p>
              Намерете конкретни продукти по град и категория.
              Открийте най-изгодните оферти и промоции.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">🗺️</div>
            <h3>Сравнение по места</h3>
            <p>
              Сравнете цените на една категория продукти в различни градове.
              Вижте къде се предлагат най-добрите цени.
            </p>
          </div>
        </div>

        <div className="cta-section">
          <p className="cta-text">
            Изберете отчет от менюто горе, за да започнете анализ на цените
          </p>
        </div>
      </div>
    </div>
  );
}

export default HomePage;
