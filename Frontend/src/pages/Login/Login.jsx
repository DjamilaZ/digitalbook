import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../../System Design/Button";
import { FallingBooksAnimation } from "./FallingBooksAnimation";
import { Mail, Lock, Eye, EyeOff, BookOpen } from "lucide-react";
import authService from "../../services/authService";

const Login = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState(() => {
    try { return localStorage.getItem('remember_email') || ""; } catch (_) { return ""; }
  });
  const [password, setPassword] = useState(() => {
    try { return localStorage.getItem('remember_password') || ""; } catch (_) { return ""; }
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [rememberMe, setRememberMe] = useState(() => {
    try {
      const rm = localStorage.getItem('remember_me');
      if (rm !== null) return rm === 'true';
      const hasCreds = !!localStorage.getItem('remember_email') || !!localStorage.getItem('remember_password');
      if (hasCreds) return true;
      const pref = localStorage.getItem('auth_pref') || sessionStorage.getItem('auth_pref');
      return pref === 'local';
    } catch (_) {
      return false;
    }
  });

  // Synchroniser depuis localStorage si "Se souvenir de moi" est actif
  useEffect(() => {
    try {
      if (rememberMe) {
        const savedEmail = localStorage.getItem('remember_email');
        const savedPassword = localStorage.getItem('remember_password');
        if (savedEmail && savedEmail !== email) setEmail(savedEmail);
        if (savedPassword && savedPassword !== password) setPassword(savedPassword);
      }
    } catch (_) {}
  }, [rememberMe]);

  // Fallback au montage: réhydrater après le premier rendu si champs vides
  useEffect(() => {
    const t = setTimeout(() => {
      try {
        if (rememberMe) {
          const savedEmail = localStorage.getItem('remember_email');
          const savedPassword = localStorage.getItem('remember_password');
          if (!email && savedEmail) setEmail(savedEmail);
          if (!password && savedPassword) setPassword(savedPassword);
        }
      } catch (_) {}
    }, 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      // Appel à l'API d'authentification réelle
      const response = await authService.login(email, password, rememberMe);
      
      console.log('Connexion réussie:', response);
      
      // Sauvegarde ou nettoyage des identifiants selon la préférence
      try {
        if (rememberMe) {
          localStorage.setItem('remember_me', 'true');
          localStorage.setItem('remember_email', email);
          localStorage.setItem('remember_password', password);
        } else {
          localStorage.removeItem('remember_me');
          localStorage.removeItem('remember_email');
          localStorage.removeItem('remember_password');
        }
      } catch (_) {}

      // Redirection vers la page d'accueil après connexion réussie
      navigate("/");
    } catch (err) {
      console.error('Erreur de connexion:', err);
      
      // Gestion des erreurs plus précise
      if (err.response) {
        // Erreur réponse du serveur
        if (err.response.status === 401) {
          setError("Email ou mot de passe incorrect");
        } else if (err.response.status === 400) {
          // Erreur de validation Django
          const errorData = err.response.data;
          if (errorData.email) {
            setError(`Email: ${errorData.email[0]}`);
          } else if (errorData.password) {
            setError(`Mot de passe: ${errorData.password[0]}`);
          } else if (errorData.non_field_errors) {
            setError(errorData.non_field_errors[0]);
          } else if (errorData.detail) {
            setError(errorData.detail);
          } else {
            setError("Données invalides");
          }
        } else if (err.response.status === 422) {
          setError("Données invalides");
        } else {
          setError(err.response.data?.message || err.response.data?.detail || "Erreur lors de la connexion");
        }
      } else if (err.request) {
        // Erreur réseau
        setError("Impossible de se connecter au serveur. Vérifiez votre connexion.");
      } else {
        // Autre erreur
        setError("Une erreur est survenue. Veuillez réessayer.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-accent-50 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animation de fond */}
      <FallingBooksAnimation />
      
      {/* Décorations de fond */}
      <div className="absolute top-10 left-10 w-72 h-72 bg-primary-100 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
      <div className="absolute top-40 right-10 w-72 h-72 bg-accent-100 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-8 left-20 w-72 h-72 bg-warning-100 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000"></div>

      {/* Carte de connexion */}
      <div className="relative z-10 bg-white/80 backdrop-blur-lg rounded-2xl shadow-2xl p-8 w-full max-w-md border border-white/20">
        {/* Logo et titre */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary rounded-full mb-4">
            <BookOpen className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Bienvenue sur <span className="text-primary">DigitalBook</span>
          </h1>
          <p className="text-gray-600">
            Connectez-vous pour accéder à votre bibliothèque numérique
          </p>
        </div>

        {/* Formulaire de connexion */}
        <form onSubmit={handleLogin} className="space-y-6" autoComplete="on">
          {/* Champ Email */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Mail className="h-5 w-5 text-gray-800" />
              </div>
              <input
                id="email"
                name="username"
                type="email"
                value={email}
                onChange={(e) => {
                  const v = e.target.value;
                  setEmail(v);
                  try { if (rememberMe) localStorage.setItem('remember_email', v); } catch (_) {}
                }}
                className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 bg-white/70 backdrop-blur-sm"
                placeholder="votre@email.com"
                autoComplete="username email"
                required
              />
            </div>
          </div>

          {/* Champ Mot de passe */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
              Mot de passe
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock className="h-5 w-5 text-gray-800" />
              </div>
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => {
                  const v = e.target.value;
                  setPassword(v);
                  try { if (rememberMe) localStorage.setItem('remember_password', v); } catch (_) {}
                }}
                className="block w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 bg-white/70 backdrop-blur-sm"
                placeholder="••••••••"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5 text-gray-600 hover:text-gray-800" />
                ) : (
                  <Eye className="h-5 w-5 text-gray-600 hover:text-gray-800" />
                )}
              </button>
            </div>
          </div>

          {/* Message d'erreur */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          {/* Options supplémentaires */}
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                checked={rememberMe}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setRememberMe(checked);
                  try {
                    if (checked) {
                      localStorage.setItem('remember_me', 'true');
                      // Enregistrer les valeurs actuelles si présentes
                      if (email) localStorage.setItem('remember_email', email);
                      if (password) localStorage.setItem('remember_password', password);
                    } else {
                      localStorage.removeItem('remember_me');
                      localStorage.removeItem('remember_email');
                      localStorage.removeItem('remember_password');
                    }
                  } catch (_) {}
                }}
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
                Se souvenir de moi
              </label>
            </div>
            <div className="text-sm">
              <button type="button" onClick={() => navigate('/reset-password')} className="font-medium text-primary hover:text-primary/80 bg-transparent border-0 p-0">
                Mot de passe oublié?
              </button>
            </div>
          </div>

          {/* Bouton de connexion */}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full"
            disabled={isLoading}
          >
            {isLoading ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white mr-2"></div>
                Connexion...
              </div>
            ) : (
              "Se connecter"
            )}
          </Button>
        </form>

        {/* Lien d'inscription */}
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            Pas encore de compte?{" "}
            <a href="#" className="font-medium text-primary hover:text-primary/80">
              Créer un compte
            </a>
          </p>
        </div>

      
    
      </div>
    </div>
  );
};

export default Login;
