// frontend/src/index.js
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App'; // ✅ CORRECT — no curly braces

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);

