"use client";

import { useEffect, useState } from "react";
import { check } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";

// Extend Window interface for Tauri
declare global {
  interface Window {
    __TAURI_INTERNALS__?: any;
  }
}

export default function AutoUpdater() {
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [updateInfo, setUpdateInfo] = useState<any>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    // Only run in Tauri environment
    if (!window.__TAURI_INTERNALS__) return;

    const checkForUpdates = async () => {
      try {
        const update = await check();
        if (update && update?.available) {
          setUpdateAvailable(true);
          setUpdateInfo(update);
        }
      } catch (error) {
        console.error("Failed to check for updates:", error);
      }
    };

    checkForUpdates();
  }, []);

  const downloadAndInstall = async () => {
    if (!updateInfo) return;
    try {
      setDownloading(true);
      await updateInfo.downloadAndInstall();
      await relaunch();
    } catch (error) {
      console.error("Failed to install update:", error);
      setDownloading(false);
    }
  };

  if (!updateAvailable) return null;

  return (
    <div className="fixed bottom-4 right-4 bg-white border border-gray-200 shadow-xl rounded-lg p-4 z-50 w-80 flex flex-col items-start gap-3">
      <div className="flex flex-col">
        <h3 className="text-sm font-semibold text-gray-900">New update available!</h3>
        <p className="text-xs text-gray-500 mt-1">Version {updateInfo?.version} is ready to run.</p>
      </div>
      <button 
        onClick={downloadAndInstall} 
        disabled={downloading}
        className="text-xs w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors"
      >
        {downloading ? "Downloading..." : "Click to install & restart"}
      </button>
    </div>
  );
}
