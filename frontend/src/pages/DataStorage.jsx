import React, { useCallback, useEffect, useState } from 'react';
import {
  Database,
  HardDrive,
  Download,
  Upload,
  RotateCcw,
  Camera,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  FolderOpen,
  WifiOff,
} from 'lucide-react';
import { apiClient, API_BASE_URL } from '../api';

/**
 * Local storage and backup control panel.
 *
 * Everything on this page operates on files on this machine. Nothing is
 * uploaded anywhere, which is why the application works with networking off.
 */
export function DataStorage() {
  const [info, setInfo] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [infoRes, snapRes] = await Promise.all([
        apiClient.getStorageInfo(),
        apiClient.getSnapshots(),
      ]);
      if (infoRes && infoRes.success) setInfo(infoRes.data);
      if (snapRes && snapRes.success) setSnapshots(snapRes.data || []);
      setError(null);
    } catch (err) {
      setError('Could not read storage information. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const act = async (name, fn) => {
    setBusy(name);
    setMessage(null);
    setError(null);
    try {
      const result = await fn();
      if (result && result.success === false) {
        setError(result.error || 'Operation failed.');
      } else {
        setMessage(result && result.message ? result.message : 'Done.');
      }
      await refresh();
    } catch (err) {
      setError('Operation failed.');
    } finally {
      setBusy(null);
    }
  };

  const handleRestore = (snapshot) => {
    const confirmed = window.confirm(
      `Restore the database from:\n\n${snapshot.filename}\n` +
      `Taken: ${new Date(snapshot.created_at).toLocaleString()}\n\n` +
      'All changes made since that snapshot will be lost. A safety snapshot of ' +
      'the current state is taken first.\n\nRestart the application afterwards.'
    );
    if (!confirmed) return;
    act('restore', () => apiClient.restoreSnapshot(snapshot.filename));
  };

  const handleImport = (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      let payload;
      try {
        payload = JSON.parse(reader.result);
      } catch {
        setError('That file is not valid JSON.');
        return;
      }
      const confirmed = window.confirm(
        `Import ${file.name}?\n\nExisting patients are kept and only new records are added.\n` +
        'Medicines already present are skipped.'
      );
      if (confirmed) act('import', () => apiClient.importData(payload, false));
    };
    reader.readAsText(file);
    event.target.value = '';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-gray-500">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Reading storage information...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-800">Data &amp; backups</h1>
        <p className="mt-1 text-sm text-gray-600">
          All records are stored locally on this computer. Nothing is sent to any server.
        </p>
      </div>

      {/* Offline assurance */}
      <div className="flex items-start gap-3 rounded-lg border-l-4 border-emerald-500 bg-emerald-50 p-4">
        <WifiOff className="mt-0.5 h-5 w-5 flex-shrink-0 text-emerald-600" />
        <div className="text-sm text-emerald-900">
          <p className="font-semibold">Fully offline</p>
          <p className="mt-0.5">
            This application makes no internet requests. It has no telemetry, no cloud sync
            and no external content, and it will run normally with networking disabled.
          </p>
        </div>
      </div>

      {message && (
        <div className="flex items-start gap-3 rounded-lg border-l-4 border-emerald-500 bg-emerald-50 p-4">
          <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-emerald-600" />
          <p className="text-sm text-emerald-800">{message}</p>
        </div>
      )}
      {error && (
        <div className="flex items-start gap-3 rounded-lg border-l-4 border-red-500 bg-red-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Where the data lives */}
      {info && (
        <div className="rounded-lg bg-white p-6 shadow">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-800">
            <HardDrive className="h-5 w-5 text-gray-500" /> Where your data is stored
          </h2>
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-gray-500">Database file</p>
              <p className="break-all font-mono text-xs text-gray-800">{info.database_path}</p>
            </div>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <div className="rounded-lg bg-gray-50 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-500">Size</p>
                <p className="font-semibold text-gray-800">{info.database_size_readable}</p>
              </div>
              <div className="rounded-lg bg-gray-50 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-500">Patients</p>
                <p className="font-semibold text-gray-800">{info.counts.patients}</p>
              </div>
              <div className="rounded-lg bg-gray-50 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-500">Medicines</p>
                <p className="font-semibold text-gray-800">{info.counts.medicines}</p>
              </div>
              <div className="rounded-lg bg-gray-50 p-3">
                <p className="text-xs uppercase tracking-wide text-gray-500">Prescriptions</p>
                <p className="font-semibold text-gray-800">{info.counts.prescriptions}</p>
              </div>
            </div>
            <p className="text-xs text-gray-500">
              Backups are written to <span className="break-all font-mono">{info.backup_directory}</span>
            </p>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-lg bg-white p-5 shadow">
          <Camera className="mb-2 h-6 w-6 text-blue-500" />
          <h3 className="font-semibold text-gray-800">Snapshot now</h3>
          <p className="mb-3 mt-1 text-xs text-gray-600">
            Captures the current state of all data. The last 10 snapshots are kept
            automatically.
          </p>
          <button
            onClick={() => act('snapshot', () => apiClient.createSnapshot())}
            disabled={busy === 'snapshot'}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {busy === 'snapshot' ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Camera className="h-4 w-4" />
            )}
            Take snapshot
          </button>
        </div>

        <div className="rounded-lg bg-white p-5 shadow">
          <Download className="mb-2 h-6 w-6 text-emerald-500" />
          <h3 className="font-semibold text-gray-800">Export</h3>
          <p className="mb-3 mt-1 text-xs text-gray-600">
            Writes a portable JSON file containing every record. Keep it as an offline
            archive or move it to another computer.
          </p>
          <a
            href={`${API_BASE_URL}/storage/export?download=1`}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm text-white hover:bg-emerald-700"
          >
            <Download className="h-4 w-4" /> Download export
          </a>
        </div>

        <div className="rounded-lg bg-white p-5 shadow">
          <Upload className="mb-2 h-6 w-6 text-purple-500" />
          <h3 className="font-semibold text-gray-800">Import</h3>
          <p className="mb-3 mt-1 text-xs text-gray-600">
            Load a previously exported JSON file. Additive: existing patients are kept
            and new records are merged in.
          </p>
          <label className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-purple-600 px-3 py-2 text-sm text-white hover:bg-purple-700">
            {busy === 'import' ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            Choose file
            <input type="file" accept=".json" className="hidden" onChange={handleImport} />
          </label>
        </div>
      </div>

      {/* Snapshots */}
      <div className="rounded-lg bg-white shadow">
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-800">
            <Database className="h-5 w-5 text-gray-500" /> Saved snapshots
          </h2>
          <span className="text-xs text-gray-500">{snapshots.length} available</span>
        </div>

        {snapshots.length === 0 ? (
          <p className="px-6 py-10 text-center text-sm text-gray-500">
            No snapshots yet. One is taken automatically each time the application starts.
          </p>
        ) : (
          <ul className="divide-y">
            {snapshots.map((snapshot) => (
              <li
                key={snapshot.filename}
                className="flex flex-wrap items-center justify-between gap-3 px-6 py-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-900">
                    {snapshot.filename}
                  </p>
                  <p className="text-xs text-gray-500">
                    {new Date(snapshot.created_at).toLocaleString()} &middot; {snapshot.size_readable}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleRestore(snapshot)}
                    disabled={busy === 'restore'}
                    className="flex items-center gap-1 rounded bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 disabled:opacity-50"
                  >
                    {busy === 'restore' ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <RotateCcw className="h-3 w-3" />
                    )}
                    Restore
                  </button>
                  <span
                    className="flex items-center gap-1 text-xs text-gray-400"
                    title={snapshot.path}
                  >
                    <FolderOpen className="h-3 w-3" />
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-lg border-amber-200 bg-amber-50 p-4">
        <p className="flex items-start gap-2 text-xs text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>
            Restoring a snapshot replaces the live database. A safety snapshot of the
            current state is taken automatically first, so a restore can itself be undone.
            Restart the application after restoring to be certain all data is reloaded.
          </span>
        </p>
      </div>
    </div>
  );
}

export default DataStorage;
