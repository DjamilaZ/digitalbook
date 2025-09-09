import React from "react";
import { Home, Upload, FileText } from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";
import NavItem from "./NavItem";

const Sidebar = () => {
  const location = useLocation();
  
  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <aside className="w-64 h-screen bg-white border-r flex flex-col justify-between">
      {/* Logo */}
      <div>
        <div className="flex items-center gap-2 p-6">
          <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold">
            P
          </div>
          <div>
            <h1 className="text-lg font-bold">PDFReader</h1>
            <p className="text-sm text-gray-500">Lecture intelligente</p>
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
          <NavLink to="/upload" className="no-underline">
            {({ isActive }) => (
              <NavItem 
                icon={<Upload size={18} />} 
                label="Télécharger PDF" 
                active={isActive} 
              />
            )}
          </NavLink>
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
      <div className="p-4 border-t flex items-center gap-3">
        <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">U</div>
        <div>
          <p className="text-sm font-medium">Utilisateur</p>
          <p className="text-xs text-gray-500">Lecteur PDF</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
