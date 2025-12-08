import { useEffect, useState } from 'react';
import { Clock, CheckCircle, XCircle, Loader, Wifi, WifiOff, Zap, HardDrive } from 'lucide-react';
import { downloadsAPI } from '../services/api';
import { useWebSocket, useDownloadUpdates } from '../hooks/useWebSocket';
import toast from 'react-hot-toast';

export default function DownloadsPage() {
  const [activeDownloads, setActiveDownloads] = useState([]);
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('active');
  const [downloadProgress, setDownloadProgress] = useState({});

  // WebSocket connection
  const { isConnected } = useWebSocket(true);

  // Listen for real-time download updates
  useDownloadUpdates({
    onProgress: (data) => {
      setDownloadProgress(prev => ({
        ...prev,
        [data.download_id]: {
          progress: data.progress,
          speed_mbps: data.speed_mbps,
          eta_seconds: data.eta_seconds
        }
      }));
    },
    onCompleted: (data) => {
      toast.success(`✓ ${data.filename} completed!`);
      // Remove from progress tracking
      setDownloadProgress(prev => {
        const updated = { ...prev };
        delete updated[data.download_id];
        return updated;
      });
      // Reload downloads
      loadData();
    },
    onFailed: (data) => {
      toast.error(`✗ ${data.filename} failed`);
      // Remove from progress tracking
      setDownloadProgress(prev => {
        const updated = { ...prev };
        delete updated[data.download_id];
        return updated;
      });
      loadData();
    },
    onStarted: (data) => {
      toast(`📥 ${data.filename} started`, { duration: 2000 });
      loadData();
    }
  });

  useEffect(() => {
    loadData();
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

  const formatSpeed = (mbps) => {
    if (mbps >= 1000) {
      return `${(mbps / 1000).toFixed(1)} GB/s`;
    }
    return `${mbps.toFixed(1)} MB/s`;
  };

  const formatETA = (seconds) => {
    if (!seconds || seconds === 0) return '--';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  };

  const getStatusBadge = (status) => {
    const badges = {
      completed: { color: 'bg-green-500/20 text-green-400', icon: CheckCircle, label: 'COMPLETED' },
      downloading: { color: 'bg-blue-500/20 text-blue-400', icon: Loader, label: 'DOWNLOADING' },
      queued: { color: 'bg-yellow-500/20 text-yellow-400', icon: Clock, label: 'QUEUED' },
      pending: { color: 'bg-yellow-500/20 text-yellow-400', icon: Clock, label: 'PENDING' },
      waiting_space: { color: 'bg-orange-500/20 text-orange-400', icon: HardDrive, label: 'WAITING FOR SPACE' },
      failed: { color: 'bg-red-500/20 text-red-400', icon: XCircle, label: 'FAILED' },
      cancelled: { color: 'bg-gray-500/20 text-gray-400', icon: XCircle, label: 'CANCELLED' },
    };
    const badge = badges[status.toLowerCase()] || badges.pending;
    const Icon = badge.icon;
    return (
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        <Icon size={14} className={`mr-1 ${status === 'downloading' ? 'animate-spin' : ''}`} />
        {badge.label}
      </span>
    );
  };

  const ProgressBar = ({ downloadId }) => {
    const progress = downloadProgress[downloadId];

    if (!progress) return null;

    return (
      <div className="mt-2 space-y-1">
        {/* Progress Bar */}
        <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300 ease-out"
            style={{ width: `${progress.progress}%` }}
          >
            <div className="w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse" />
          </div>
        </div>

        {/* Stats */}
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>{progress.progress.toFixed(1)}%</span>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <Zap size={12} className="text-purple-400" />
              {formatSpeed(progress.speed_mbps)}
            </span>
            <span>ETA: {formatETA(progress.eta_seconds)}</span>
          </div>
        </div>
      </div>
    );
  };

  const DownloadRow = ({ download, showProgress }) => (
    <tr className="border-b border-slate-700/50 hover:bg-slate-700/30">
      <td className="py-4 px-4">
        <div className="text-white font-medium truncate max-w-md">{download.filename}</div>
        {download.movie_title && <div className="text-sm text-slate-400">{download.movie_title}</div>}
        {download.series_name && (
          <div className="text-sm text-slate-400">
            {download.series_name} {download.season && download.episode && `S${download.season}E${download.episode}`}
          </div>
        )}
        {showProgress && <ProgressBar downloadId={download.id} />}
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

        {/* WebSocket Status Indicator */}
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${
          isConnected
            ? 'bg-green-500/10 text-green-400 border border-green-500/20'
            : 'bg-red-500/10 text-red-400 border border-red-500/20'
        }`}>
          {isConnected ? (
            <>
              <Wifi size={16} />
              <span>Real-Time Updates</span>
            </>
          ) : (
            <>
              <WifiOff size={16} />
              <span>Disconnected</span>
            </>
          )}
        </div>
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
                activeDownloads.map((download) => (
                  <DownloadRow key={download.id} download={download} showProgress={true} />
                ))}
              {activeTab === 'history' &&
                history.map((download) => (
                  <DownloadRow key={download.id} download={download} showProgress={false} />
                ))}
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
