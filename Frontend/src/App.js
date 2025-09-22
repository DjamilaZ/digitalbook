import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Sidebar from './System Design/Sidebar';
import Home from './pages/Home/Home';
import Login from './pages/Login/Login';
import Upload from './pages/Upload/Upload';
import Documents from './pages/Documents/Documents';
import DocumentViewer from './pages/DocumentViewer/DocumentViewer';
import authService from './services/authService';
import Profile from './pages/Profile/Profile';
import ResetPassword from './pages/ResetPassword/ResetPassword';

// Composant pour protéger les routes nécessitant une authentification
const ProtectedRoute = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const authStatus = authService.isAuthenticated();
        if (authStatus) {
          // Optionnel: valider le token avec le backend
          try {
            await authService.validateToken();
            setIsAuthenticated(true);
          } catch (error) {
            console.log('Token invalide, redirection vers login');
            setIsAuthenticated(false);
          }
        } else {
          setIsAuthenticated(false);
        }
      } catch (error) {
        console.error('Erreur lors de la vérification d\'authentification:', error);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement...</p>
        </div>
      </div>
    );
  }

  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

// Composant pour protéger les routes réservées aux administrateurs
const AdminRoute = ({ children }) => {
  const [allowed, setAllowed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAdmin = async () => {
      try {
        const authStatus = authService.isAuthenticated();
        if (authStatus) {
          try {
            await authService.validateToken();
          } catch (error) {
            // Token invalide, on refusera plus bas
          }
        }
        setAllowed(authStatus && authService.isAdmin());
      } catch (error) {
        setAllowed(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAdmin();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Chargement...</p>
        </div>
      </div>
    );
  }

  return allowed ? children : <Navigate to="/" replace />;
};

// Composant pour le layout principal
const MainLayout = () => {
  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1 ml-64">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/upload" element={
            <AdminRoute>
              <Upload />
            </AdminRoute>
          } />
          <Route path="/documents" element={<Documents />} />
          <Route path="/documents/:id" element={<DocumentViewer />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="bg-gray-50 min-h-screen">
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/*" element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        } />
      </Routes>
    </div>
  );
}

export default App;
