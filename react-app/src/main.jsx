/**
 * main.jsx: Application entry point for the Kolko Ni Struva React app.
 * Mounts the root App component into the #root DOM element.
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
