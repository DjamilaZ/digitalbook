import React from 'react';
import { Routes, Route } from 'react-router-dom';
import './App.css';
import Sidebar from './System Design/Sidebar';
import Home from './pages/Home/Home';
import Upload from './pages/Upload/Upload';
import Documents from './pages/Documents/Documents';
import DocumentViewer from './pages/DocumentViewer/DocumentViewer';

function App() {
  return (
    <div className="flex bg-gray-50 min-h-screen">
      <Sidebar />
      <div className="flex-1 ml-64">
        <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/documents/:id" element={<DocumentViewer />} />
      </Routes>
      </div>
    </div>
  );
}

export default App;
