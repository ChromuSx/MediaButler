import { useEffect, useState } from 'react';
import { Download, Clock, CheckCircle, XCircle, Loader } from 'lucide-react';
import { downloadsAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function DownloadsPage() {
  const [activeDownloads, setActiveDownloads] = useState([]);
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('active');

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [active, hist] = await Promise.all([
        downloadsAPI.getActive(),
        downloadsAPI.getHistory({ limit: 50 }),
      ]);
      setActiveDownloads(active);
      setHistory(hist.items);
    } catch (error) {
      toast.error('Failed to load downloads');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      COMPLETED: { color: 'bg-green-500/20 text-green-400', icon: CheckCircle },
      IN_PROGRESS: { color: 'bg-blue-500/20 text-blue-400', icon: Loader },
      QUEUED: { color: 'bg-yellow-500/20 text-yellow-400', icon: Clock },
      FAILED: { color: 'bg-red-500/20 text-red-400', icon: XCircle },
      CANCELLED: { color: 'bg-gray-500/20 text-gray-400', icon: XCircle },
    };
    const badge = badges[status] || badges.QUEUED;
    const Icon = badge.icon;
    return (
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        <Icon size={14} className="mr-1" />
        {status}
      </span>
    );
  };

  const DownloadRow = ({ download }) => (
    <tr className="border-b border-slate-700/50 hover:bg-slate-700/30">
      <td className="py-4 px-4">
        <div className="text-white font-medium truncate max-w-md">{download.filename}</div>
        {download.movie_title && <div className="text-sm text-slate-400">{download.movie_title}</div>}
        {download.series_name && (
          <div className="text-sm text-slate-400">
            {download.series_name} {download.season && download.episode && `S${download.season}E${download.episode}`}
          </div>
        )}
      </td>
      <td className="py-4 px-4 text-slate-300">{download.size_gb} GB</td>
      <td className="py-4 px-4">{getStatusBadge(download.status)}</td>
      <td className="py-4 px-4 text-slate-300">
        {new Date(download.created_at).toLocaleString()}
      </td>
    </tr>
  );

  if (isLoading) {
    return <div className="text-slate-400">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Downloads</h1>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-700">
        <div className="flex space-x-8">
          <button
            onClick={() => setActiveTab('active')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'active'
                ? 'border-primary-500 text-white'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            Active ({activeDownloads.length})
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`pb-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'history'
                ? 'border-primary-500 text-white'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            History ({history.length})
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-700/50">
              <tr>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">File</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">Size</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">Status</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-300">Date</th>
              </tr>
            </thead>
            <tbody>
              {activeTab === 'active' &&
                activeDownloads.map((download) => <DownloadRow key={download.id} download={download} />)}
              {activeTab === 'history' &&
                history.map((download) => <DownloadRow key={download.id} download={download} />)}
              {((activeTab === 'active' && activeDownloads.length === 0) ||
                (activeTab === 'history' && history.length === 0)) && (
                <tr>
                  <td colSpan="4" className="py-8 text-center text-slate-400">
                    No downloads found
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
