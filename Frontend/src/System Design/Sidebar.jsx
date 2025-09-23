import React, { useEffect, useRef, useState } from "react";
import { Home, Upload, FileText, User, LogOut, ChevronDown } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import NavItem from "./NavItem";
import authService from "../services/authService";

const Sidebar = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const userMenuRef = useRef(null);

  // Charger les infos utilisateur depuis le stockage local
  useEffect(() => {
    setUser(authService.getUserData());
    const onStorage = (e) => {
      if (e.key === 'user' || e.key === 'token') {
        setUser(authService.getUserData());
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  // Fermer le menu si clic à l'extérieur
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const userName = authService.getUserName() || 'Utilisateur';
  const userRole = authService.getUserRole() || 'Lecteur PDF';
  const initials = (userName || 'U')
    .split(' ')
    .filter(Boolean)
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
  const isAdmin = authService.isAdmin();

  const handleProfile = () => {
    setMenuOpen(false);
    navigate('/profile');
  };

  const handleLogout = async () => {
    setMenuOpen(false);
    try {
      await authService.logout();
    } finally {
      navigate('/login');
    }
  };

  return (
    <aside className="w-64 h-screen bg-white border-r flex flex-col justify-between fixed left-0 top-0 bottom-0 z-50">
      {/* Logo */}
      <div>
        <div className="flex flex-col items-center p-6">
          <img src="/total-energies-logo.png" alt="Total Energies Logo" className="w-20 h-20 object-contain mb-3" />
          <div className="text-center">
            <h1 className="text-lg font-bold">DigitalBook</h1>
            <p className="text-sm text-gray-500">Lecture de vos documents en toutes simplicité</p>
          </div>
        </div>
        
        {/* Nav */}
        <nav className="mt-6 flex flex-col gap-1">
          <NavLink to="/" className="no-underline">
            {({ isActive }) => (
              <NavItem 
                icon={<Home size={18} />} 
                label="Accueil" 
                active={isActive} 
              />
            )}
          </NavLink>
          {isAdmin && (
            <NavLink to="/upload" className="no-underline">
              {({ isActive }) => (
                <NavItem 
                  icon={<Upload size={18} />} 
                  label="Télécharger PDF" 
                  active={isActive} 
                />
              )}
            </NavLink>
          )}
          <NavLink to="/documents" className="no-underline">
            {({ isActive }) => (
              <NavItem 
                icon={<FileText size={18} />} 
                label="Mes Documents" 
                active={isActive} 
              />
            )}
          </NavLink>
        </nav>
      </div>

      {/* User */}
      <div className="p-4 border-t relative" ref={userMenuRef}>
        <button
          type="button"
          className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50"
          onClick={() => setMenuOpen((o) => !o)}
        >
          <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center text-sm font-semibold">{initials || 'U'}</div>
          <div className="flex-1 text-left">
            <p className="text-sm font-medium">{userName || 'Utilisateur'}</p>
            <p className="text-xs text-gray-500">{userRole || 'Lecteur PDF'}</p>
          </div>
          <ChevronDown size={16} className={`text-gray-400 transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
        </button>

        {menuOpen && (
          <div className="absolute left-2 bottom-14 w-48 bg-white border rounded-lg shadow-lg py-1 z-50">
            <button
              type="button"
              onClick={handleProfile}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              <User size={16} /> Profil
            </button>
            <div className="h-px bg-gray-100 my-1" />
            <button
              type="button"
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              <LogOut size={16} /> Déconnecter
            </button>
          </div>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;
