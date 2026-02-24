"use client";

import {
    createContext, useContext, useState, useEffect,
    useCallback, type ReactNode
} from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Thread {
    id: string;
    title: string;
    preview: string;
    createdAt: string;
    updatedAt: string;
    messageCount: number;
}

interface ChatContextValue {
    threads: Thread[];
    activeThreadId: string;
    setActiveThreadId: (id: string) => void;
    upsertThread: (thread: Thread) => void;
    deleteThread: (id: string) => void;
    startNewThread: () => string;
    refreshThreads: () => void;
}

// ─── Storage helpers ──────────────────────────────────────────────────────────

const THREADS_KEY = "k24_chat_threads";
const ACTIVE_KEY = "k24_thread_id";

function loadThreads(): Thread[] {
    try { return JSON.parse(localStorage.getItem(THREADS_KEY) ?? "[]"); } catch { return []; }
}
function persistThreads(threads: Thread[]) {
    localStorage.setItem(THREADS_KEY, JSON.stringify(threads));
}
function makeId() { return crypto.randomUUID(); }

// ─── Context ──────────────────────────────────────────────────────────────────

const ChatContext = createContext<ChatContextValue>({
    threads: [],
    activeThreadId: "",
    setActiveThreadId: () => { },
    upsertThread: () => { },
    deleteThread: () => { },
    startNewThread: () => "",
    refreshThreads: () => { },
});

// ─── Provider ─────────────────────────────────────────────────────────────────

export function ChatProvider({ children }: { children: ReactNode }) {
    const [threads, setThreads] = useState<Thread[]>([]);
    const [activeThreadId, setActiveThreadIdState] = useState<string>("");

    // Load from localStorage on mount
    useEffect(() => {
        setThreads(loadThreads());
        const stored = localStorage.getItem(ACTIVE_KEY);
        if (stored) {
            setActiveThreadIdState(stored);
        } else {
            const id = makeId();
            localStorage.setItem(ACTIVE_KEY, id);
            setActiveThreadIdState(id);
        }
    }, []);

    const refreshThreads = useCallback(() => {
        setThreads(loadThreads());
    }, []);

    const setActiveThreadId = useCallback((id: string) => {
        localStorage.setItem(ACTIVE_KEY, id);
        setActiveThreadIdState(id);
    }, []);

    const upsertThread = useCallback((thread: Thread) => {
        setThreads(prev => {
            const idx = prev.findIndex(t => t.id === thread.id);
            const updated = idx >= 0
                ? prev.map(t => t.id === thread.id ? thread : t)
                : [thread, ...prev];
            persistThreads(updated);
            return updated;
        });
    }, []);

    const deleteThread = useCallback((id: string) => {
        setThreads(prev => {
            const updated = prev.filter(t => t.id !== id);
            persistThreads(updated);
            return updated;
        });
    }, []);

    const startNewThread = useCallback((): string => {
        const id = makeId();
        localStorage.setItem(ACTIVE_KEY, id);
        setActiveThreadIdState(id);
        return id;
    }, []);

    return (
        <ChatContext.Provider value={{
            threads, activeThreadId, setActiveThreadId,
            upsertThread, deleteThread, startNewThread, refreshThreads,
        }}>
            {children}
        </ChatContext.Provider>
    );
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useChat() {
    return useContext(ChatContext);
}
