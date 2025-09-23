import React, { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Button from "../../System Design/Button";
import { FallingBooksAnimation } from "../Login/FallingBooksAnimation";
import authService from "../../services/authService";
import { Mail, Lock, CheckCircle } from "lucide-react";

const ResetPassword = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sendMessage, setSendMessage] = useState("");
  const [sendError, setSendError] = useState("");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState("");
  const [resetError, setResetError] = useState("");

  const handleRequest = async (e) => {
    e.preventDefault();
    setSending(true);
    setSendMessage("");
    setSendError("");
    try {
      const res = await authService.requestPasswordReset(email);
      setSendMessage(res?.message || "Email de réinitialisation envoyé");
    } catch (err) {
      setSendError(
        err?.response?.data?.error || err?.response?.data?.message || "Erreur lors de l'envoi de l'email"
      );
    } finally {
      setSending(false);
    }
  };

  const handleReset = async (e) => {
    e.preventDefault();
    setResetting(true);
    setResetMessage("");
    setResetError("");

    if (!newPassword || newPassword !== confirmPassword) {
      setResetError("Les mots de passe ne correspondent pas");
      setResetting(false);
      return;
    }

    try {
      const res = await authService.resetPassword(token, newPassword);
      setResetMessage(res?.message || "Mot de passe réinitialisé avec succès");
      // Redirection vers login après un court délai
      setTimeout(() => navigate("/login"), 1500);
    } catch (err) {
      setResetError(
        err?.response?.data?.error || err?.response?.data?.message || "Erreur lors de la réinitialisation"
      );
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-accent-50 flex items-center justify-center p-4 relative overflow-hidden">
      <FallingBooksAnimation />
      <div className="absolute top-10 left-10 w-72 h-72 bg-primary-100 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
      <div className="absolute top-40 right-10 w-72 h-72 bg-accent-100 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-8 left-20 w-72 h-72 bg-warning-100 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000"></div>

      <div className="relative z-10 bg-white/80 backdrop-blur-lg rounded-2xl shadow-2xl p-8 w-full max-w-md border border-white/20">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary rounded-full mb-4">
            <Lock className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">
            {token ? "Réinitialiser le mot de passe" : "Mot de passe oublié"}
          </h1>
          <p className="text-gray-600">
            {token
              ? "Choisissez un nouveau mot de passe pour votre compte"
              : "Entrez votre email pour recevoir un lien de réinitialisation"}
          </p>
        </div>

        {!token ? (
          <form onSubmit={handleRequest} className="space-y-5">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Adresse e-mail
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

            {sendError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{sendError}</div>
            )}
            {sendMessage && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center gap-2">
                <CheckCircle size={18} /> {sendMessage}
              </div>
            )}

            <Button type="submit" variant="primary" className="w-full" disabled={sending}>
              {sending ? "Envoi..." : "Envoyer le lien"}
            </Button>

            <Button type="button" variant="secondary" className="w-full" onClick={() => navigate("/login")}>Retour au login</Button>
          </form>
        ) : (
          <form onSubmit={handleReset} className="space-y-5">
            <div>
              <label htmlFor="newPassword" className="block text-sm font-medium text-gray-700 mb-2">
                Nouveau mot de passe
              </label>
              <input
                id="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="block w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 bg-white/70 backdrop-blur-sm"
                placeholder="••••••••"
                required
              />
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
                Confirmer le mot de passe
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="block w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200 bg-white/70 backdrop-blur-sm"
                placeholder="••••••••"
                required
              />
            </div>

            {resetError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{resetError}</div>
            )}
            {resetMessage && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center gap-2">
                <CheckCircle size={18} /> {resetMessage}
              </div>
            )}

            <Button type="submit" variant="primary" className="w-full" disabled={resetting}>
              {resetting ? "Mise à jour..." : "Réinitialiser le mot de passe"}
            </Button>

            <Button type="button" variant="secondary" className="w-full" onClick={() => navigate("/login")}>Retour au login</Button>
          </form>
        )}
      </div>
    </div>
  );
};

export default ResetPassword;
