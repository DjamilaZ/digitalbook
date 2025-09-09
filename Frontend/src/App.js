import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import './App.css';

function Home() {
  return (
    <div className="container">
      <h1>Bienvenue sur DigitalBook</h1>
      <p>Votre application de gestion de livres numériques</p>
    </div>
  );
}

function App() {
  return (
    <div className="App">
      <header>
        <nav>
          <ul>
            <li><Link to="/">Accueil</Link></li>
            <li><Link to="/books">Livres</Link></li>
            <li><Link to="/about">À propos</Link></li>
          </ul>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/about" element={<div>À propos de DigitalBook</div>} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
