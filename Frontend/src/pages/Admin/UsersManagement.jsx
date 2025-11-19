import React, { useEffect, useMemo, useState } from 'react';
import { Users, Edit, Trash2, RefreshCw, Save, X, UserPlus, Search, Mail, UserRound } from 'lucide-react';
import api from '../../services/api';
import authService from '../../services/authService';

const roleOptions = [
  { value: 'employe', label: 'Employé' },
  { value: 'manager', label: 'Manager' },
  { value: 'admin', label: 'Admin' },
];

const emptyForm = {
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  username: '',
  role_name: 'employe',
};

const UsersManagement = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState(emptyForm);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [query, setQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  const isAdmin = useMemo(() => authService.isAdmin(), []);
  const isManager = useMemo(() => authService.isManager(), []);
  const currentUser = useMemo(() => authService.getUserData(), []);

  const loadUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/auth/users/');
      const data = res?.data;
      setUsers((data && Array.isArray(data.results)) ? data.results : (data || []));
      setLastUpdated(new Date());
    } catch (e) {
      setError("Impossible de charger les utilisateurs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const onChange = (setter) => (e) => {
    const { name, value, type, checked } = e.target;
    setter((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const createUser = async () => {
    setCreating(true);
    setError('');
    try {
      const payload = { ...form };
      if (!payload.password) delete payload.password;
      if (!payload.username) delete payload.username;
      await api.post('/auth/users/', payload);
      setForm(emptyForm);
      setShowCreateModal(false);
      await loadUsers();
    } catch (e) {
      setError("Création échouée. Vérifiez les champs.");
    } finally {
      setCreating(false);
    }
  };

  const startEdit = (u) => {
    setEditingId(u.id);
    setEditForm({
      email: u.email || '',
      password: '',
      first_name: u.first_name || '',
      last_name: u.last_name || '',
      username: u.username || '',
      role_name: u.role_name || 'employe',
    });
    setShowEditModal(true);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditForm(emptyForm);
  };

  const saveEdit = async (id) => {
    setLoading(true);
    setError('');
    try {
      const payload = { ...editForm };
      if (!payload.password) delete payload.password;
      await api.patch(`/auth/users/${id}/`, payload);
      setEditingId(null);
      setShowEditModal(false);
      await loadUsers();
    } catch (e) {
      setError("Mise à jour échouée.");
    } finally {
      setLoading(false);
    }
  };

  const deleteUser = async (id) => {
    if (!window.confirm('Supprimer cet utilisateur ?')) return;
    setLoading(true);
    setError('');
    try {
      await api.delete(`/auth/users/${id}/`);
      await loadUsers();
    } catch (e) {
      setError("Suppression échouée.");
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = useMemo(() => {
    const q = query.trim().toLowerCase();
    return users.filter(u => {
      // Exclure l'utilisateur connecté de la liste
      if (currentUser && u.id === currentUser.id) return false;
      const matchesQ = !q || (
        (u.email || '').toLowerCase().includes(q) ||
        (u.first_name || '').toLowerCase().includes(q) ||
        (u.last_name || '').toLowerCase().includes(q) ||
        (u.username || '').toLowerCase().includes(q)
      );
      const matchesRole = !roleFilter || u.role_name === roleFilter;
      return matchesQ && matchesRole;
    });
  }, [users, query, roleFilter, currentUser]);

  const initialsOf = (name, email) => {
    const base = (name && name.trim()) || email || '';
    const parts = base.split(' ').filter(Boolean);
    const raw = (parts[0]?.[0] || '') + (parts[1]?.[0] || '');
    return (raw || (email?.[0] || 'U')).toUpperCase();
  };

  const canAccess = isAdmin || isManager;
  const canWrite = isAdmin; // managers read-only

  if (!canAccess) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold text-gray-800">Accès refusé</h1>
        <p className="text-gray-600">Vous n'avez pas les droits pour accéder à cette page.</p>
      </div>
    );
  }

  

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      <div className="flex flex-col gap-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
              <Users size={20} />
            </div>
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">Gestion des utilisateurs</h1>
              <p className="text-sm text-gray-500">Créer, modifier et supprimer des comptes.</p>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-2">
            {canWrite && (
              <button
                className="inline-flex items-center gap-2 px-3 py-2 bg-primary text-white rounded hover:bg-primary/90 text-sm shadow-sm"
                onClick={() => setShowCreateModal(true)}
              >
                <UserPlus size={16} /> Nouvel utilisateur
              </button>
            )}
            <button
              className="inline-flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded hover:bg-gray-50 text-sm"
              onClick={loadUsers}
              disabled={loading}
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Rafraîchir
            </button>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
          <div className="relative flex-1 min-w-[240px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary/50"
              placeholder="Rechercher par nom, email ou username"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div>
            <select
              className="w-full sm:w-48 px-3 py-2 border rounded-lg text-sm bg-white"
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
            >
              <option value="">Tous les rôles</option>
              {roleOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="sm:hidden flex gap-2">
            {canWrite && (
              <button
                className="inline-flex flex-1 items-center justify-center gap-2 px-3 py-2 bg-primary text-white rounded hover:bg-primary/90 text-sm shadow-sm"
                onClick={() => setShowCreateModal(true)}
              >
                <UserPlus size={16} /> Ajouter
              </button>
            )}
            <button
              className="inline-flex flex-1 items-center justify-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded hover:bg-gray-50 text-sm"
              onClick={loadUsers}
              disabled={loading}
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {lastUpdated && (
          <div className="text-xs text-gray-500">Mis à jour: {lastUpdated.toLocaleString()}</div>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 border border-red-200 bg-red-50 text-red-700 text-sm rounded">{error}</div>
      )}

      {/* Formulaire de création */}

      {/* Liste des utilisateurs */}
      <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-gray-700">
              <tr>
                <th className="px-3 py-2 text-left">Utilisateur</th>
                <th className="px-3 py-2 text-left">Rôle</th>
                <th className="px-3 py-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((u) => (
                <tr key={u.id} className="border-t hover:bg-gray-50/50">
                  <td className="px-3 py-3 align-top whitespace-nowrap">
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-9 rounded-full bg-primary/10 text-primary flex items-center justify-center font-semibold">
                        {initialsOf(`${u.first_name || ''} ${u.last_name || ''}`.trim(), u.email)}
                      </div>
                      <div>
                        <div className="text-gray-900 font-medium flex items-center gap-1">
                          <UserRound size={14} className="text-gray-400" /> {u.first_name} {u.last_name}
                        </div>
                        <div className="text-gray-500 text-xs flex items-center gap-1">
                          <Mail size={12} className="text-gray-400" /> {u.email}
                        </div>
                        <div className="text-gray-500 text-xs">{u.username}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-3 align-top">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${((u.role_name || '').toString().toLowerCase() === 'admin')
                      ? 'bg-primary/10 text-primary'
                      : ((u.role_name || '').toString().toLowerCase() === 'manager')
                        ? 'bg-violet-100 text-violet-700'
                        : 'bg-amber-100 text-amber-700'}`}>{((u.role_name || '').toString().toUpperCase())}</span>
                  </td>
                  <td className="px-3 py-3 align-top">
                    {canWrite && (
                      <div className="flex gap-2">
                        <button className="inline-flex items-center gap-1 px-3 py-1.5 text-xs bg-white border rounded-lg hover:bg-gray-50" onClick={() => startEdit(u)}>
                          <Edit size={14} /> Modifier
                        </button>
                        <button className="inline-flex items-center gap-1 px-3 py-1.5 text-xs bg-red-600 text-white rounded-lg hover:bg-red-700" onClick={() => deleteUser(u.id)}>
                          <Trash2 size={14} /> Supprimer
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {filteredUsers.length === 0 && (
                <tr>
                  <td className="px-3 py-6 text-center text-gray-500" colSpan={3}>Aucun utilisateur</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {canWrite && showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setShowCreateModal(false)}></div>
          <div className="relative bg-white w-full max-w-2xl rounded-lg shadow-lg p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2"><UserPlus size={18} /> Ajouter un utilisateur</h3>
              <button className="p-1 rounded hover:bg-gray-100" onClick={() => setShowCreateModal(false)}><X size={18} /></button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Email</label>
                <input name="email" value={form.email} onChange={onChange(setForm)} className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Mot de passe</label>
                <input type="password" name="password" value={form.password} onChange={onChange(setForm)} className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Nom d'utilisateur</label>
                <input name="username" value={form.username} onChange={onChange(setForm)} className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Prénom</label>
                <input name="first_name" value={form.first_name} onChange={onChange(setForm)} className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Nom</label>
                <input name="last_name" value={form.last_name} onChange={onChange(setForm)} className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Rôle</label>
                <select name="role_name" value={form.role_name} onChange={onChange(setForm)} className="w-full border rounded p-2 text-sm">
                  {roleOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button className="inline-flex items-center gap-2 px-3 py-2 rounded border bg-gray-100 hover:bg-gray-200" onClick={() => setShowCreateModal(false)}>
                <X size={16} /> Annuler
              </button>
              <button className="inline-flex items-center gap-2 px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700" onClick={createUser} disabled={creating}>
                <Save size={16} /> Créer
              </button>
            </div>
          </div>
        </div>
      )}

      {canWrite && showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => { setShowEditModal(false); setEditingId(null); }}></div>
          <div className="relative bg-white w-full max-w-2xl rounded-lg shadow-lg p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2"><Edit size={18} /> Modifier l'utilisateur</h3>
              <button className="p-1 rounded hover:bg-gray-100" onClick={() => { setShowEditModal(false); setEditingId(null); }}><X size={18} /></button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Email</label>
                <input name="email" value={editForm.email} onChange={onChange(setEditForm)} className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Nouveau mot de passe (optionnel)</label>
                <input name="password" type="password" value={editForm.password} onChange={onChange(setEditForm)} className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Nom d'utilisateur</label>
                <input name="username" value={editForm.username} onChange={onChange(setEditForm)} className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Prénom</label>
                <input name="first_name" value={editForm.first_name} onChange={onChange(setEditForm)} className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Nom</label>
                <input name="last_name" value={editForm.last_name} onChange={onChange(setEditForm)} className="w-full border rounded p-2 text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Rôle</label>
                <select name="role_name" value={editForm.role_name} onChange={onChange(setEditForm)} className="w-full border rounded p-2 text-sm">
                  {roleOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button className="inline-flex items-center gap-2 px-3 py-2 rounded border bg-gray-100 hover:bg-gray-200" onClick={() => { setShowEditModal(false); setEditingId(null); }}>
                <X size={16} /> Annuler
              </button>
              <button className="inline-flex items-center gap-2 px-3 py-2 rounded bg-blue-600 text-white hover:bg-blue-700" onClick={() => saveEdit(editingId)} disabled={loading}>
                <Save size={16} /> Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersManagement;
