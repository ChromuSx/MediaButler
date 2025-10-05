import { useEffect, useState } from 'react';
import { Users as UsersIcon } from 'lucide-react';
import { usersAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

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

  if (isLoading) {
    return <div className="text-slate-400">Loading users...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Users</h1>
        <div className="flex items-center text-slate-400">
          <UsersIcon size={20} className="mr-2" />
          <span>{users.length} total users</span>
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
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.user_id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                  <td className="py-4 px-4 text-white">{user.user_id}</td>
                  <td className="py-4 px-4">
                    <div className="text-white font-medium">{user.username}</div>
                    {user.is_admin && (
                      <span className="inline-block px-2 py-1 text-xs bg-purple-500/20 text-purple-400 rounded mt-1">
                        Admin
                      </span>
                    )}
                  </td>
                  <td className="py-4 px-4 text-right text-slate-300">{user.total_downloads}</td>
                  <td className="py-4 px-4 text-right text-slate-300">{user.total_size_gb} GB</td>
                  <td className="py-4 px-4 text-slate-300">
                    {user.last_active ? new Date(user.last_active).toLocaleDateString() : 'Never'}
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-slate-400">
                    No users found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
