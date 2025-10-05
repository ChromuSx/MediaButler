import { useEffect, useState } from 'react';
import { Save } from 'lucide-react';
import { settingsAPI } from '../services/api';
import toast from 'react-hot-toast';

export default function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await settingsAPI.get();
      setSettings(data);
    } catch (error) {
      toast.error('Failed to load settings');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await settingsAPI.update(settings);
      toast.success('Settings saved successfully');
    } catch (error) {
      toast.error('Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <div className="text-slate-400">Loading settings...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-slate-600 text-white rounded-lg transition-colors"
        >
          <Save size={18} className="mr-2" />
          {isSaving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      <div className="space-y-6">
        {/* Paths */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">Paths</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Movies Path</label>
              <input
                type="text"
                value={settings?.paths?.movies_path || ''}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    paths: { ...settings.paths, movies_path: e.target.value },
                  })
                }
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">TV Shows Path</label>
              <input
                type="text"
                value={settings?.paths?.tv_path || ''}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    paths: { ...settings.paths, tv_path: e.target.value },
                  })
                }
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Download Path</label>
              <input
                type="text"
                value={settings?.paths?.download_path || ''}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    paths: { ...settings.paths, download_path: e.target.value },
                  })
                }
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
        </div>

        {/* Limits */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">Limits</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Max Concurrent Downloads
              </label>
              <input
                type="number"
                value={settings?.limits?.max_concurrent_downloads || 3}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    limits: { ...settings.limits, max_concurrent_downloads: parseInt(e.target.value) },
                  })
                }
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Minimum Space (GB)
              </label>
              <input
                type="number"
                step="0.1"
                value={settings?.limits?.min_space_gb || 10}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    limits: { ...settings.limits, min_space_gb: parseFloat(e.target.value) },
                  })
                }
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
        </div>

        {/* TMDB */}
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <h2 className="text-lg font-semibold text-white mb-4">TMDB Integration</h2>
          <div className="space-y-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                checked={settings?.tmdb?.enabled || false}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    tmdb: { ...settings.tmdb, enabled: e.target.checked },
                  })
                }
                className="w-4 h-4 text-primary-600 bg-slate-700 border-slate-600 rounded focus:ring-primary-500"
              />
              <label className="ml-2 text-sm text-slate-300">Enable TMDB Integration</label>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Language</label>
              <input
                type="text"
                value={settings?.tmdb?.language || 'en-US'}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    tmdb: { ...settings.tmdb, language: e.target.value },
                  })
                }
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
