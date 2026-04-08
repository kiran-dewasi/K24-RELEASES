"use client";

import { useEffect, useState } from "react";
import { isTauri } from "@tauri-apps/api/core";
import { relaunch } from "@tauri-apps/plugin-process";
import { check, type DownloadEvent, type Update } from "@tauri-apps/plugin-updater";
import { Download, RefreshCw, X } from "lucide-react";

const CHECK_INTERVAL_MS = 60 * 60 * 1000;

type UpdateState = "idle" | "checking" | "available" | "downloading" | "installing" | "error";

export default function AutoUpdater() {
  const [visible, setVisible] = useState(false);
  const [status, setStatus] = useState<UpdateState>("idle");
  const [message, setMessage] = useState("");
  const [downloadedBytes, setDownloadedBytes] = useState(0);
  const [totalBytes, setTotalBytes] = useState<number | null>(null);
  const [update, setUpdate] = useState<Update | null>(null);

  useEffect(() => {
    if (!isTauri()) {
      return;
    }

    let cancelled = false;

    const checkForUpdates = async () => {
      if (cancelled) {
        return;
      }

      setStatus((current) => (current === "idle" ? "checking" : current));

      try {
        const nextUpdate = await check();
        if (cancelled) {
          await nextUpdate?.close();
          return;
        }

        if (!nextUpdate) {
          setUpdate((existing) => {
            void existing?.close();
            return null;
          });
          setVisible(false);
          setMessage("");
          setDownloadedBytes(0);
          setTotalBytes(null);
          setStatus("idle");
          return;
        }

        setUpdate((existing) => {
          void existing?.close();
          return nextUpdate;
        });
        setVisible(true);
        setStatus("available");
        setMessage(`Version ${nextUpdate.version} is available. Save your work before installing.`);
      } catch (error) {
        const details = error instanceof Error ? error.message : String(error);
        console.error("Updater check failed", error);
        setVisible(true);
        setStatus("error");
        setMessage(`Unable to check for updates right now: ${details}`);
      }
    };

    void checkForUpdates();
    const interval = window.setInterval(() => {
      void checkForUpdates();
    }, CHECK_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
      setUpdate((existing) => {
        void existing?.close();
        return null;
      });
    };
  }, []);

  const handleProgress = (event: DownloadEvent) => {
    if (event.event === "Started") {
      setDownloadedBytes(0);
      setTotalBytes(event.data.contentLength ?? null);
      setStatus("downloading");
      setMessage("Downloading update package...");
      return;
    }

    if (event.event === "Progress") {
      setDownloadedBytes((bytes) => bytes + event.data.chunkLength);
      return;
    }

    setStatus("installing");
    setMessage("Installing update...");
  };

  const downloadAndInstall = async () => {
    if (!update) {
      return;
    }

    try {
      setVisible(true);
      setStatus("downloading");
      setMessage("Preparing download...");
      await update.downloadAndInstall(handleProgress);
      setStatus("installing");
      setMessage("Update installed. Restarting K24...");
      await relaunch();
    } catch (error) {
      const details = error instanceof Error ? error.message : String(error);
      console.error("Updater install failed", error);
      setStatus("error");
      setMessage(`Update failed: ${details}`);
    }
  };

  if (!visible) {
    return null;
  }

  const progressPercent =
    totalBytes && totalBytes > 0 ? Math.min(100, Math.round((downloadedBytes / totalBytes) * 100)) : null;
  const isBusy = status === "downloading" || status === "installing";
  const isError = status === "error";

  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 max-w-[calc(100vw-2rem)] rounded-xl border border-slate-200 bg-white/95 p-4 shadow-2xl backdrop-blur">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">
            {isError ? "Update check failed" : "K24 update ready"}
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            {update ? `Current update target: ${update.version}` : "Updater status"}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setVisible(false)}
          disabled={isBusy}
          className="rounded p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Dismiss updater notification"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <p className="text-sm text-slate-700">{message}</p>

      {progressPercent !== null && (
        <div className="mt-3">
          <div className="h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-blue-600 transition-[width] duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-slate-500">{progressPercent}% downloaded</p>
        </div>
      )}

      <div className="mt-4 flex gap-2">
        {!isError && (
          <button
            type="button"
            onClick={downloadAndInstall}
            disabled={!update || isBusy}
            className="flex w-full items-center justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isBusy ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
            {status === "installing" ? "Installing..." : isBusy ? "Downloading..." : "Install and restart"}
          </button>
        )}

        <button
          type="button"
          onClick={() => setVisible(false)}
          disabled={isBusy}
          className="rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Later
        </button>
      </div>
    </div>
  );
}
