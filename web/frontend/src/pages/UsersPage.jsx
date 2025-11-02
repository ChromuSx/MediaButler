import { useEffect, useState } from 'react';
import { Users as UsersIcon, UserPlus, Edit2, Trash2, Shield, Ban } from 'lucide-react';
import { usersAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);

  // Form state for adding new user
  const [newUser, setNewUser] = useState({
    user_id: '',
    telegram_username: '',
    is_admin: false,
    notes: ''
  });

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const data = await usersAPI.list();
      setUsers(data);
    } catch (error) {
      toast.error('Failed to load users');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddUser = async () => {
    if (!newUser.user_id) {
      toast.error('User ID is required');
      return;
    }

    try {
      await usersAPI.create({
        user_id: parseInt(newUser.user_id),
        telegram_username: newUser.telegram_username || null,
        is_admin: newUser.is_admin,
        notes: newUser.notes || null
      });
      toast.success('User added successfully');
      setShowAddModal(false);
      setNewUser({ user_id: '', telegram_username: '', is_admin: false, notes: '' });
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add user');
    }
  };

  const handleEditUser = async () => {
    if (!selectedUser) return;

    try {
      await usersAPI.update(selectedUser.user_id, {
        telegram_username: selectedUser.username,
        is_admin: selectedUser.is_admin,
        notes: selectedUser.notes
      });
      toast.success('User updated successfully');
      setShowEditModal(false);
      setSelectedUser(null);
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update user');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!confirm('Are you sure you want to remove this user?')) return;

    try {
      await usersAPI.delete(userId);
      toast.success('User removed successfully');
      loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove user');
    }
  };

  const openEditModal = (user) => {
    setSelectedUser({ ...user });
    setShowEditModal(true);
  };

  if (isLoading) {
    return <div className="text-slate-400">Loading users...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Authorized Users</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center text-slate-400">
            <UsersIcon size={20} className="mr-2" />
            <span>{users.length} total users</span>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
          >
            <UserPlus size={18} />
            Add User
          </button>
        </div>
      </div>

      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-700/50">
              <tr>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">User ID</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">Username</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-300">Downloads</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-300">Total Size</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">Last Active</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">Notes</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-slate-300">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.user_id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                  <td className="py-4 px-4 text-white font-mono">{user.user_id}</td>
                  <td className="py-4 px-4">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-medium">{user.username}</span>
                      {user.is_admin && (
                        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-purple-500/20 text-purple-400 rounded">
                          <Shield size={12} />
                          Admin
                        </span>
                      )}
                      {user.is_banned && (
                        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-red-500/20 text-red-400 rounded">
                          <Ban size={12} />
                          Banned
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-4 px-4 text-right text-slate-300">{user.total_downloads}</td>
                  <td className="py-4 px-4 text-right text-slate-300">{user.total_size_gb} GB</td>
                  <td className="py-4 px-4 text-slate-300">
                    {user.last_active ? new Date(user.last_active).toLocaleDateString() : 'Never'}
                  </td>
                  <td className="py-4 px-4 text-slate-400 text-sm max-w-xs truncate">
                    {user.notes || '-'}
                  </td>
                  <td className="py-4 px-4">
                    <div className="flex items-center justify-center gap-2">
                      <button
                        onClick={() => openEditModal(user)}
                        className="p-2 text-slate-400 hover:text-purple-400 hover:bg-slate-700 rounded transition-colors"
                        title="Edit user"
                      >
                        <Edit2 size={16} />
                      </button>
                      <button
                        onClick={() => handleDeleteUser(user.user_id)}
                        className="p-2 text-slate-400 hover:text-red-400 hover:bg-slate-700 rounded transition-colors"
                        title="Remove user"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-slate-400">
                    No users found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add User Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-6 w-full max-w-md border border-slate-700">
            <h2 className="text-xl font-bold text-white mb-4">Add New User</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Telegram User ID *
                </label>
                <input
                  type="number"
                  value={newUser.user_id}
                  onChange={(e) => setNewUser({ ...newUser, user_id: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-purple-500"
                  placeholder="123456789"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Telegram Username (optional)
                </label>
                <input
                  type="text"
                  value={newUser.telegram_username}
                  onChange={(e) => setNewUser({ ...newUser, telegram_username: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-purple-500"
                  placeholder="@username"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Notes (optional)
                </label>
                <textarea
                  value={newUser.notes}
                  onChange={(e) => setNewUser({ ...newUser, notes: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-purple-500"
                  rows="2"
                  placeholder="Optional notes about this user"
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_admin"
                  checked={newUser.is_admin}
                  onChange={(e) => setNewUser({ ...newUser, is_admin: e.target.checked })}
                  className="w-4 h-4 text-purple-600 bg-slate-700 border-slate-600 rounded focus:ring-purple-500"
                />
                <label htmlFor="is_admin" className="ml-2 text-sm text-slate-300">
                  Grant admin privileges
                </label>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={handleAddUser}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
              >
                Add User
              </button>
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setNewUser({ user_id: '', telegram_username: '', is_admin: false, notes: '' });
                }}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditModal && selectedUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-6 w-full max-w-md border border-slate-700">
            <h2 className="text-xl font-bold text-white mb-4">Edit User</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  User ID
                </label>
                <input
                  type="text"
                  value={selectedUser.user_id}
                  disabled
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-slate-400"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Telegram Username
                </label>
                <input
                  type="text"
                  value={selectedUser.username || ''}
                  onChange={(e) => setSelectedUser({ ...selectedUser, username: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-purple-500"
                  placeholder="@username"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Notes
                </label>
                <textarea
                  value={selectedUser.notes || ''}
                  onChange={(e) => setSelectedUser({ ...selectedUser, notes: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-purple-500"
                  rows="2"
                  placeholder="Optional notes about this user"
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="edit_is_admin"
                  checked={selectedUser.is_admin}
                  onChange={(e) => setSelectedUser({ ...selectedUser, is_admin: e.target.checked })}
                  className="w-4 h-4 text-purple-600 bg-slate-700 border-slate-600 rounded focus:ring-purple-500"
                />
                <label htmlFor="edit_is_admin" className="ml-2 text-sm text-slate-300">
                  Admin privileges
                </label>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={handleEditUser}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
              >
                Save Changes
              </button>
              <button
                onClick={() => {
                  setShowEditModal(false);
                  setSelectedUser(null);
                }}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
