import React, { useEffect, useState } from "react";
import Button from "../../System Design/Button";
import authService from "../../services/authService";
import { Mail, Shield, LogOut, Phone, Building, Calendar, BookOpen, Edit3, Save, X } from "lucide-react";
import { FallingBooksAnimation } from "../Login/FallingBooksAnimation";

// Utilitaire pour construire un profil affichable à partir des données utilisateur
const buildProfileFromUser = (u) => ({
  firstName: u?.first_name || "",
  lastName: u?.last_name || "",
  email: u?.email || "",
  phone: u?.phone || u?.profile?.phone || "",
  department: u?.department || u?.profile?.department || "",
  position: u?.position || u?.profile?.position || u?.role?.name || u?.role_name || "",
  joinDate: u?.date_joined || u?.created_at || "",
  bio: u?.bio || u?.profile?.bio || "",
  avatar: u?.avatar || u?.profile?.avatar || "",
  status: u?.is_active === false ? "inactive" : "active",
});

const Profile = () => {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(buildProfileFromUser(null));
  const [editedProfile, setEditedProfile] = useState(buildProfileFromUser(null));
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  // Changement de mot de passe
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [cpLoading, setCpLoading] = useState(false);
  const [cpError, setCpError] = useState("");
  const [cpMessage, setCpMessage] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        // 1) Afficher d'abord les données locales pour un rendu rapide
        const local = authService.getUserData();
        if (local) {
          setUser(local);
          const mapped = buildProfileFromUser(local);
          setProfile(mapped);
          setEditedProfile(mapped);
        }
        setLoading(false);

        // 2) Puis tenter de rafraîchir depuis l'API
        try {
          const fresh = await authService.getUserProfile();
          if (fresh) {
            setUser(fresh);
            const mappedFresh = buildProfileFromUser(fresh);
            setProfile(mappedFresh);
            if (!isEditing) setEditedProfile(mappedFresh);
          }
        } catch (_) {
          // on ignore si l'API profil échoue; l'utilisateur reste affiché depuis le local
        }
      } catch (e) {
        setError("Impossible de charger le profil");
        setLoading(false);
      }
    };
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fullName = profile.firstName && profile.lastName
    ? `${profile.firstName} ${profile.lastName}`
    : user?.username || profile.email || "Utilisateur";

  const role = user?.role?.name || user?.role_name || "Lecteur";

  const initials = (fullName || "U")
    .split(" ")
    .filter(Boolean)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const handleLogout = async () => {
    try {
      await authService.logout();
    } finally {
      window.location.href = "/login";
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
    setEditedProfile(profile);
  };

  const handleSave = async () => {
    // TODO: Appeler l'API de mise à jour du profil si disponible
    setProfile(editedProfile);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedProfile(profile);
    setIsEditing(false);
  };

  const handleInputChange = (field, value) => {
    setEditedProfile((prev) => ({ ...prev, [field]: value }));
  };

  const joinDateDisplay = profile.joinDate
    ? new Date(profile.joinDate).toLocaleDateString("fr-FR", { year: "numeric", month: "long", day: "numeric" })
    : "—";

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setCpError("");
    setCpMessage("");
    if (!oldPassword || !newPassword || !confirmPassword) {
      setCpError("Veuillez remplir tous les champs");
      return;
    }
    if (newPassword !== confirmPassword) {
      setCpError("Les mots de passe ne correspondent pas");
      return;
    }
    try {
      setCpLoading(true);
      const res = await authService.changePassword(oldPassword, newPassword);
      setCpMessage(res?.message || "Mot de passe changé avec succès");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setCpError(err?.response?.data?.error || err?.response?.data?.message || "Erreur lors du changement de mot de passe");
    } finally {
      setCpLoading(false);
    }
  };

  return (
    <div className="flex-1 p-8 overflow-y-auto relative overflow-hidden min-h-screen bg-gradient-to-br from-primary-50 via-white to-accent-50">
      {/* Animation de fond */}
      <FallingBooksAnimation />
      {/* Décorations de fond (identiques à la page de login) */}
      <div className="absolute top-10 left-10 w-72 h-72 bg-primary-100 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
      <div className="absolute top-40 right-10 w-72 h-72 bg-accent-100 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-8 left-20 w-72 h-72 bg-warning-100 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000"></div>

      <div className="relative z-10 max-w-4xl mx-auto">
        {loading ? (
          <div className="bg-white/80 backdrop-blur-lg border border-white/20 rounded-2xl p-8 text-center shadow-2xl">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary mx-auto mb-3"></div>
            <p className="text-gray-600">Chargement du profil...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        ) : (
          <div className="bg-white/80 backdrop-blur-lg border border-white/20 rounded-2xl shadow-2xl p-6 md:p-8">
            {/* Header */}
            <div className="flex items-start md:items-center justify-between mb-6">
              <div className="flex items-center gap-4">
                <div className="w-20 h-20 rounded-full bg-primary-50 text-primary flex items-center justify-center text-2xl font-semibold border-4 border-primary/20">
                  {initials}
                </div>
                <div>
                  <h1 className="text-2xl font-bold">Profil Utilisateur</h1>
                  <p className="text-gray-600 -mt-1">Gérez vos informations personnelles et préférences</p>
                </div>
              </div>
              {/* <div className="flex gap-2">
                {!isEditing ? (
                  <Button onClick={handleEdit} variant="secondary" size="md" className="border border-primary text-primary hover:bg-primary/10">
                    <Edit3 className="w-4 h-4 mr-2" /> Modifier
                  </Button>
                ) : (
                  <>
                    <Button onClick={handleSave} size="md" className="bg-primary hover:bg-primary/90 text-white">
                      <Save className="w-4 h-4 mr-2" /> Sauvegarder
                    </Button>
                    <Button onClick={handleCancel} variant="secondary" size="md" className="border border-gray-300 text-gray-600 hover:bg-gray-100">
                      <X className="w-4 h-4 mr-2" /> Annuler
                    </Button>
                  </>
                )}
              </div> */}
            </div>

            {/* Sections */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Informations personnelles */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center">
                  <Shield className="w-5 h-5 mr-2 text-primary" /> Informations personnelles
                </h3>

                {/* Prénom / Nom */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Prénom</label>
                    {isEditing ? (
                      <input
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent bg-white/70"
                        value={editedProfile.firstName}
                        onChange={(e) => handleInputChange("firstName", e.target.value)}
                      />
                    ) : (
                      <p className="text-gray-900 bg-gray-50 p-2 rounded-md border border-gray-200">{profile.firstName || "—"}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Nom</label>
                    {isEditing ? (
                      <input
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent bg-white/70"
                        value={editedProfile.lastName}
                        onChange={(e) => handleInputChange("lastName", e.target.value)}
                      />
                    ) : (
                      <p className="text-gray-900 bg-gray-50 p-2 rounded-md border border-gray-200">{profile.lastName || "—"}</p>
                    )}
                  </div>
                </div>

                {/* Email */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center"><Mail className="w-4 h-4 mr-2" /> Adresse e-mail</label>
                  {isEditing ? (
                    <input
                      type="email"
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent bg-white/70"
                      value={editedProfile.email}
                      onChange={(e) => handleInputChange("email", e.target.value)}
                    />
                  ) : (
                    <p className="text-gray-900 bg-gray-50 p-2 rounded-md border border-gray-200">{profile.email || "—"}</p>
                  )}
                </div>

                {/* Téléphone */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center"><Phone className="w-4 h-4 mr-2" /> Téléphone</label>
                  {isEditing ? (
                    <input
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent bg-white/70"
                      value={editedProfile.phone}
                      onChange={(e) => handleInputChange("phone", e.target.value)}
                    />
                  ) : (
                    <p className="text-gray-900 bg-gray-50 p-2 rounded-md border border-gray-200">{profile.phone || "—"}</p>
                  )}
                </div>
              </div>

              {/* Informations professionnelles */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center">
                  <Building className="w-5 h-5 mr-2 text-primary" /> Informations professionnelles
                </h3>

                {/* Département */}
                {/* <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Département</label>
                  {isEditing ? (
                    <input
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent bg-white/70"
                      value={editedProfile.department}
                      onChange={(e) => handleInputChange("department", e.target.value)}
                    />
                  ) : (
                    <p className="text-gray-900 bg-gray-50 p-2 rounded-md border border-gray-200">{profile.department || "—"}</p>
                  )}
                </div> */}

                {/* Poste */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Rôle</label>
                  {isEditing ? (
                    <input
                      className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent bg-white/70"
                      value={editedProfile.position}
                      onChange={(e) => handleInputChange("position", e.target.value)}
                    />
                  ) : (
                    <p className="text-gray-900 bg-gray-50 p-2 rounded-md border border-gray-200">{profile.position || role || "—"}</p>
                  )}
                </div>

                {/* Date d'arrivée */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center"><Calendar className="w-4 h-4 mr-2" /> Date d'arrivée</label>
                  <p className="text-gray-900 bg-gray-50 p-2 rounded-md border border-gray-200">{joinDateDisplay}</p>
                </div>

                {/* Statut */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Statut</label>
                  {profile.status === "active" ? (
                    <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-primary/10 text-primary border border-primary/20">Actif</span>
                  ) : (
                    <span className="inline-flex items-center px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600 border border-gray-200">Inactif</span>
                  )}
                </div>
              </div>
            </div>

            {/* À propos */}
            <div className="mt-8">
              <h3 className="text-lg font-semibold flex items-center">
                <BookOpen className="w-5 h-5 mr-2 text-primary" /> À propos
              </h3>
              <div className="mt-3">
                {isEditing ? (
                  <textarea
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent bg-white/70 min-h-[100px]"
                    value={editedProfile.bio}
                    onChange={(e) => handleInputChange("bio", e.target.value)}
                    placeholder="Décrivez votre parcours et vos compétences..."
                  />
                ) : (
                  <p className="text-gray-900 bg-gray-50 p-3 rounded-md border border-gray-200 leading-relaxed">{profile.bio || "—"}</p>
                )}
              </div>
            </div>

            {/* Changer le mot de passe */}
            {/* <div className="mt-8">
              <h3 className="text-lg font-semibold">Changer le mot de passe</h3>
              <form onSubmit={handleChangePassword} className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Ancien mot de passe</label>
                  <input
                    type="password"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent bg-white/70"
                    value={oldPassword}
                    onChange={(e) => setOldPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Nouveau mot de passe</label>
                  <input
                    type="password"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent bg-white/70"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Confirmer le mot de passe</label>
                  <input
                    type="password"
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary focus:border-transparent bg-white/70"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>

                {cpError && (
                  <div className="md:col-span-3 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{cpError}</div>
                )}
                {cpMessage && (
                  <div className="md:col-span-3 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">{cpMessage}</div>
                )}

                <div className="md:col-span-3">
                  <Button type="submit" variant="primary" disabled={cpLoading}>
                    {cpLoading ? "Mise à jour..." : "Mettre à jour le mot de passe"}
                  </Button>
                </div>
              </form>
            </div> */}

            {/* Actions bas de page */}
            <div className="mt-8 flex flex-wrap gap-3">
              <Button
                variant="secondary"
                className="border border-gray-300 text-gray-700 hover:bg-gray-100"
                onClick={() => window.history.back()}
              >
                Retour
              </Button>
              <Button
                variant="primary"
                className="bg-red-600 hover:bg-red-600/90"
                onClick={handleLogout}
              >
                <LogOut size={18} className="mr-2" />
                Déconnecter
              </Button>
            </div>

            {/* Footer */}
            <div className="mt-6 pt-4 border-t border-white/40 text-center text-xs text-gray-500">
              {new Date().getFullYear()} Total Energies - Profil utilisateur sécurisé
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Profile;