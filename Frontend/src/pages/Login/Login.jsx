import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../../System Design/Button";
import { FallingBooksAnimation } from "./FallingBooksAnimation";
import { Mail, Lock, Eye, EyeOff, BookOpen } from "lucide-react";
import authService from "../../services/authService";

const Login = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      // Appel à l'API d'authentification réelle
      const response = await authService.login(email, password);
      
      console.log('Connexion réussie:', response);
      
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
        <form onSubmit={handleLogin} className="space-y-6">
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
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 bg-white/70 backdrop-blur-sm"
                placeholder="votre@email.com"
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
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="block w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 bg-white/70 backdrop-blur-sm"
                placeholder="••••••••"
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
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
                Se souvenir de moi
              </label>
            </div>
            <div className="text-sm">
              <a href="#" className="font-medium text-primary hover:text-primary/80">
                Mot de passe oublié?
              </a>
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
