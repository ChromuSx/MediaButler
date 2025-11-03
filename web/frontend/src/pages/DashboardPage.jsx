import { useEffect, useState } from 'react';
import { Download, CheckCircle, XCircle, Users, HardDrive, Activity, Wifi, WifiOff } from 'lucide-react';
import { LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { statsAPI } from '../services/api';
import { useWebSocket, useStatsUpdates, useDownloadUpdates } from '../hooks/useWebSocket';
import toast from 'react-hot-toast';

export default function DashboardPage() {
  const [overviewStats, setOverviewStats] = useState(null);
  const [downloadsTrend, setDownloadsTrend] = useState([]);
  const [mediaTypeStats, setMediaTypeStats] = useState(null);
  const [topUsers, setTopUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // WebSocket connection
  const { isConnected } = useWebSocket(true);

  // Listen for stats updates via WebSocket
  useStatsUpdates((data) => {
    setOverviewStats(prev => ({
      ...prev,
      ...data
    }));
  });

  // Listen for download events
  useDownloadUpdates({
    onCompleted: (data) => {
      toast.success(`✓ Download completed: ${data.filename}`);
      loadData(); // Refresh all stats
    },
    onFailed: (data) => {
      toast.error(`✗ Download failed: ${data.filename}`);
      loadData();
    },
    onStarted: (data) => {
      toast(`⬇ Download started: ${data.filename}`, {
        icon: '📥',
        duration: 2000
      });
    }
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [overview, trend, mediaTypes, users] = await Promise.all([
        statsAPI.getOverview(),
        statsAPI.getDownloadsTrend(7),
        statsAPI.getMediaTypes(),
        statsAPI.getTopUsers(5),
      ]);

      setOverviewStats(overview);
      setDownloadsTrend(trend);
      setMediaTypeStats(mediaTypes);
      setTopUsers(users);
    } catch (error) {
      toast.error('Failed to load statistics');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading dashboard...</div>
      </div>
    );
  }

  const StatCard = ({ title, value, subtitle, icon: Icon, color }) => (
    <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-slate-400">{title}</h3>
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon size={20} className="text-white" />
        </div>
      </div>
      <div className="text-3xl font-bold text-white mb-1">{value}</div>
      {subtitle && <div className="text-sm text-slate-500">{subtitle}</div>}
    </div>
  );

  const pieData = mediaTypeStats
    ? [
        { name: 'Movies', value: mediaTypeStats.movies, color: '#3b82f6' },
        { name: 'TV Shows', value: mediaTypeStats.tv_shows, color: '#8b5cf6' },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* WebSocket Connection Status */}
      <div className="flex items-center justify-end">
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${
          isConnected
            ? 'bg-green-500/10 text-green-400 border border-green-500/20'
            : 'bg-red-500/10 text-red-400 border border-red-500/20'
        }`}>
          {isConnected ? (
            <>
              <Wifi size={16} />
              <span>Live Updates Active</span>
            </>
          ) : (
            <>
              <WifiOff size={16} />
              <span>Disconnected</span>
            </>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <StatCard
          title="Total Downloads"
          value={overviewStats?.total_downloads || 0}
          subtitle={`${overviewStats?.successful_downloads || 0} completed`}
          icon={Download}
          color="bg-primary-600"
        />
        <StatCard
          title="Success Rate"
          value={
            overviewStats?.total_downloads > 0
              ? `${Math.round((overviewStats.successful_downloads / overviewStats.total_downloads) * 100)}%`
              : '0%'
          }
          subtitle={`${overviewStats?.failed_downloads || 0} failed`}
          icon={CheckCircle}
          color="bg-green-600"
        />
        <StatCard
          title="Active Downloads"
          value={overviewStats?.active_downloads || 0}
          subtitle={`${overviewStats?.queue_length || 0} in queue`}
          icon={Activity}
          color="bg-orange-600"
        />
        <StatCard
          title="Total Users"
          value={overviewStats?.total_users || 0}
          subtitle="Registered users"
          icon={Users}
          color="bg-purple-600"
        />
        <StatCard
          title="Storage Used"
          value={`${overviewStats?.total_size_gb?.toFixed(1) || 0} GB`}
          subtitle={`${overviewStats?.available_space_gb?.toFixed(1) || 0} GB available`}
          icon={HardDrive}
          color="bg-cyan-600"
        />
        <StatCard
          title="Avg File Size"
          value={`${overviewStats?.avg_file_size_gb?.toFixed(1) || 0} GB`}
          subtitle="Per completed download"
          icon={Download}
          color="bg-indigo-600"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Downloads Trend */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">Downloads Trend (7 Days)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={downloadsTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                labelStyle={{ color: '#cbd5e1' }}
              />
              <Legend />
              <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} name="Downloads" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Media Types Distribution */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h3 className="text-lg font-semibold text-white mb-4">Media Types Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-white">{mediaTypeStats?.movies || 0}</div>
              <div className="text-sm text-slate-400">Movies ({mediaTypeStats?.movies_gb?.toFixed(1) || 0} GB)</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-white">{mediaTypeStats?.tv_shows || 0}</div>
              <div className="text-sm text-slate-400">TV Shows ({mediaTypeStats?.tv_shows_gb?.toFixed(1) || 0} GB)</div>
            </div>
          </div>
        </div>
      </div>

      {/* Top Users */}
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <h3 className="text-lg font-semibold text-white mb-4">Top Users</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">User</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Downloads</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Size</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-400">Success Rate</th>
              </tr>
            </thead>
            <tbody>
              {topUsers.map((user) => (
                <tr key={user.user_id} className="border-b border-slate-700/50">
                  <td className="py-3 px-4 text-white">{user.username}</td>
                  <td className="py-3 px-4 text-right text-white">{user.total_downloads}</td>
                  <td className="py-3 px-4 text-right text-slate-300">{user.total_size_gb} GB</td>
                  <td className="py-3 px-4 text-right text-slate-300">{user.success_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
