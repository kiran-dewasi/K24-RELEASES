"use client";

import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import {
    ArrowRight,
    Building2,
    CheckCircle,
    Loader2,
    Lock,
    Mail,
    Monitor,
    ShieldCheck,
    User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface ConnectDeviceProps {
    onAuthenticated: () => void;
}

type AuthMode = "login" | "signup";

type AuthResponse = {
    access_token: string;
    token_type: string;
    user: {
        id: number | string;
        email: string;
        username: string;
        full_name: string;
        role: string;
        company_id: number | null;
        tenant_id?: string | null;
    };
};

type DeviceRegisterResponse = {
    license_key: string;
    socket_token?: string;
    tenant_id?: string | null;
};

const CLOUD_API = "https://weare-production.up.railway.app";

const APP_VERSION = "1.0.1";

function deriveUsername(email: string) {
    const base = email.split("@")[0] || "k24user";
    return base.replace(/[^a-zA-Z0-9._-]/g, "") || "k24user";
}

function deriveFullName(email: string, companyName: string) {
    const local = email.split("@")[0] || "";
    const humanized = local
        .split(/[._-]+/)
        .filter(Boolean)
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ");

    return humanized || companyName || "K24 User";
}

function getOrCreateDeviceId() {
    const existing = localStorage.getItem("k24_device_id");
    if (existing) return existing;

    const deviceId = crypto.randomUUID();
    localStorage.setItem("k24_device_id", deviceId);
    return deviceId;
}

export default function ConnectDevice({ onAuthenticated }: ConnectDeviceProps) {
    const [activeTab, setActiveTab] = useState<AuthMode>("login");
    const [status, setStatus] = useState<"idle" | "submitting" | "success">("idle");
    const [error, setError] = useState("");

    const [loginForm, setLoginForm] = useState({
        email: "",
        password: "",
    });

    const [signupForm, setSignupForm] = useState({
        email: "",
        password: "",
        company_name: "",
        full_name: "",
    });

    useEffect(() => {
        document.body.style.overflow = "hidden";

        return () => {
            document.body.style.overflow = "unset";
        };
    }, []);

    const isSubmitting = status === "submitting";
    const isSuccess = status === "success";

    const signupPayload = useMemo(() => {
        const email = signupForm.email.trim();
        const companyName = signupForm.company_name.trim();
        const fullName = signupForm.full_name.trim() || deriveFullName(email, companyName);

        return {
            email,
            password: signupForm.password,
            company_name: companyName,
            full_name: fullName,
            username: deriveUsername(email),
        };
    }, [signupForm]);

    async function postJson<T>(path: string, body: Record<string, unknown>): Promise<T> {
        const response = await fetch(`${CLOUD_API}${path}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(body),
        });

        const data = await response
            .json()
            .catch(() => ({ detail: "Request failed" }));

        if (!response.ok) {
            throw new Error(
                typeof data?.detail === "string"
                    ? data.detail
                    : `Request failed with status ${response.status}`
            );
        }

        return data as T;
    }

    async function completeDeviceAuth(authData: AuthResponse) {
        const deviceId = getOrCreateDeviceId();
        const userId = String(authData.user.id);

        const deviceData = await postJson<DeviceRegisterResponse>("/api/devices/register", {
            device_id: deviceId,
            user_id: userId,
            app_version: APP_VERSION,
        });

        const tenantId = deviceData.tenant_id ?? authData.user.tenant_id ?? null;

        localStorage.setItem("k24_token", authData.access_token);
        localStorage.setItem("k24_license_key", deviceData.license_key);
        localStorage.setItem(
            "k24_user",
            JSON.stringify({
                user_id: userId,
                tenant_id: tenantId,
            })
        );
        localStorage.setItem("k24_user_id", userId);

        if (deviceData.socket_token) {
            localStorage.setItem("k24_socket_token", deviceData.socket_token);
        }

        document.cookie = `k24_token=${authData.access_token}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;

        setStatus("success");
        window.setTimeout(() => {
            onAuthenticated();
        }, 900);
    }

    function getErrorMessage(error: unknown, fallback: string) {
        if (error instanceof Error && error.message) {
            return error.message;
        }

        if (typeof error === "string" && error) {
            return error;
        }

        return fallback;
    }

    async function handleLoginSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError("");
        setStatus("submitting");

        try {
            const authData = await postJson<AuthResponse>("/api/auth/login", {
                email: loginForm.email.trim(),
                password: loginForm.password,
            });

            await completeDeviceAuth(authData);
        } catch (err: unknown) {
            setStatus("idle");
            setError(getErrorMessage(err, "Unable to sign in."));
        }
    }

    async function handleSignupSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError("");
        setStatus("submitting");

        try {
            const authData = await postJson<AuthResponse>("/api/auth/register", signupPayload);
            await completeDeviceAuth(authData);
        } catch (err: unknown) {
            setStatus("idle");
            setError(getErrorMessage(err, "Unable to create your account."));
        }
    }

    return (
        <div className="fixed inset-0 z-[99999] flex items-center justify-center overflow-auto bg-[#0f172a] text-white">
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute left-[-10%] top-[-20%] h-[60%] w-[60%] rounded-full bg-indigo-600/20 blur-[120px]" />
                <div className="absolute bottom-[-20%] right-[-10%] h-[60%] w-[60%] rounded-full bg-cyan-600/10 blur-[120px]" />
                <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-[0.03]" />
            </div>

            <div className="relative z-10 m-4 flex min-h-[640px] w-full max-w-5xl overflow-hidden rounded-3xl border border-white/5 bg-black/40 shadow-2xl ring-1 ring-white/10 backdrop-blur-xl">
                <div className="relative hidden w-5/12 flex-col justify-between bg-gradient-to-br from-indigo-950/50 to-slate-900/50 p-12 lg:flex">
                    <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent,rgba(0,0,0,0.8))]" />

                    <div className="relative z-10">
                        <div className="mb-6 flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500 shadow-lg shadow-indigo-500/20">
                            <Monitor className="h-6 w-6 text-white" />
                        </div>
                        <h1 className="mb-2 text-3xl font-bold tracking-tight text-white">
                            K24 Enterprise
                        </h1>
                        <p className="font-light text-indigo-200/80">
                            Intelligent Business Operating System
                        </p>
                    </div>

                    <div className="relative z-10 space-y-6">
                        <div className="flex items-start gap-4 rounded-xl border border-white/5 bg-white/5 p-4 backdrop-blur-sm">
                            <ShieldCheck className="mt-1 h-5 w-5 text-emerald-400" />
                            <div>
                                <h3 className="text-sm font-semibold text-white">
                                    Secure Internal Auth
                                </h3>
                                <p className="mt-1 text-xs text-slate-400">
                                    Sign in and bind this device without leaving the desktop app.
                                </p>
                            </div>
                        </div>
                        <div className="flex items-start gap-4 rounded-xl border border-white/5 bg-white/5 p-4 backdrop-blur-sm">
                            <Lock className="mt-1 h-5 w-5 text-cyan-400" />
                            <div>
                                <h3 className="text-sm font-semibold text-white">
                                    License Bound Per Device
                                </h3>
                                <p className="mt-1 text-xs text-slate-400">
                                    Each successful login issues a device license and stores it locally.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="relative z-10 font-mono text-xs text-slate-500">
                        Build v{APP_VERSION} | Guaranteed Stable
                    </div>
                </div>

                <div className="relative flex flex-1 items-center bg-white/5 p-6 sm:p-10 lg:p-12">
                    {isSuccess && (
                        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-emerald-950/90 backdrop-blur-sm">
                            <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/30">
                                <CheckCircle className="h-10 w-10 text-white" />
                            </div>
                            <h2 className="mb-2 text-2xl font-bold text-white">Device Authorized</h2>
                            <p className="text-emerald-200">Starting secure session...</p>
                        </div>
                    )}

                    <div className="mx-auto w-full max-w-md">
                        <div className="mb-8 text-center lg:text-left">
                            <h2 className="mb-2 text-2xl font-bold text-white">
                                Connect this device
                            </h2>
                            <p className="text-sm text-slate-400">
                                Sign in or create your K24 workspace right here. No browser redirect is
                                used.
                            </p>
                        </div>

                        {error && (
                            <div className="mb-6 rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                                {error}
                            </div>
                        )}

                        <Tabs
                            value={activeTab}
                            onValueChange={(value) => {
                                setError("");
                                setActiveTab(value as AuthMode);
                            }}
                            className="w-full"
                        >
                            <TabsList className="grid h-12 w-full grid-cols-2 rounded-xl border border-white/10 bg-black/30 p-1">
                                <TabsTrigger
                                    value="login"
                                    className="rounded-lg text-sm data-[state=active]:bg-indigo-600 data-[state=active]:text-white"
                                >
                                    Login
                                </TabsTrigger>
                                <TabsTrigger
                                    value="signup"
                                    className="rounded-lg text-sm data-[state=active]:bg-indigo-600 data-[state=active]:text-white"
                                >
                                    Signup
                                </TabsTrigger>
                            </TabsList>

                            <TabsContent value="login" className="mt-6">
                                <form onSubmit={handleLoginSubmit} className="space-y-4">
                                    <Field
                                        icon={<Mail className="h-5 w-5" />}
                                        label="Email Address"
                                        type="email"
                                        placeholder="you@company.com"
                                        value={loginForm.email}
                                        onChange={(value) =>
                                            setLoginForm((current) => ({ ...current, email: value }))
                                        }
                                    />
                                    <Field
                                        icon={<Lock className="h-5 w-5" />}
                                        label="Password"
                                        type="password"
                                        placeholder="Enter your password"
                                        value={loginForm.password}
                                        onChange={(value) =>
                                            setLoginForm((current) => ({ ...current, password: value }))
                                        }
                                    />

                                    <Button
                                        type="submit"
                                        disabled={isSubmitting}
                                        className="h-12 w-full rounded-xl bg-indigo-600 text-white shadow-lg shadow-indigo-900/50 hover:bg-indigo-500"
                                    >
                                        {isSubmitting && activeTab === "login" ? (
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        ) : (
                                            <ArrowRight className="mr-2 h-4 w-4" />
                                        )}
                                        Sign In and Register Device
                                    </Button>
                                </form>
                            </TabsContent>

                            <TabsContent value="signup" className="mt-6">
                                <form onSubmit={handleSignupSubmit} className="space-y-4">
                                    <Field
                                        icon={<Building2 className="h-5 w-5" />}
                                        label="Company Name"
                                        type="text"
                                        placeholder="Acme Pvt Ltd"
                                        value={signupForm.company_name}
                                        onChange={(value) =>
                                            setSignupForm((current) => ({
                                                ...current,
                                                company_name: value,
                                            }))
                                        }
                                    />
                                    <Field
                                        icon={<User className="h-5 w-5" />}
                                        label="Full Name"
                                        type="text"
                                        placeholder="Founder or admin name"
                                        value={signupForm.full_name}
                                        onChange={(value) =>
                                            setSignupForm((current) => ({
                                                ...current,
                                                full_name: value,
                                            }))
                                        }
                                    />
                                    <Field
                                        icon={<Mail className="h-5 w-5" />}
                                        label="Work Email"
                                        type="email"
                                        placeholder="you@company.com"
                                        value={signupForm.email}
                                        onChange={(value) =>
                                            setSignupForm((current) => ({ ...current, email: value }))
                                        }
                                    />
                                    <Field
                                        icon={<Lock className="h-5 w-5" />}
                                        label="Password"
                                        type="password"
                                        placeholder="Create a secure password"
                                        value={signupForm.password}
                                        onChange={(value) =>
                                            setSignupForm((current) => ({ ...current, password: value }))
                                        }
                                    />

                                    <p className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-slate-400">
                                        Username is generated automatically from your email to match the
                                        current backend schema.
                                    </p>

                                    <Button
                                        type="submit"
                                        disabled={isSubmitting}
                                        className="h-12 w-full rounded-xl bg-indigo-600 text-white shadow-lg shadow-indigo-900/50 hover:bg-indigo-500"
                                    >
                                        {isSubmitting && activeTab === "signup" ? (
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        ) : (
                                            <ArrowRight className="mr-2 h-4 w-4" />
                                        )}
                                        Create Account and Register Device
                                    </Button>
                                </form>
                            </TabsContent>
                        </Tabs>

                        <div className="mt-8 flex items-center justify-center gap-2 text-xs text-slate-600">
                            <Lock className="h-3 w-3" />
                            <span>Protected by K24 Secure Guard</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

interface FieldProps {
    icon: ReactNode;
    label: string;
    type: string;
    placeholder: string;
    value: string;
    onChange: (value: string) => void;
}

function Field({ icon, label, type, placeholder, value, onChange }: FieldProps) {
    return (
        <label className="block space-y-2">
            <span className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">
                {label}
            </span>
            <div className="group relative">
                <div className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 transition-colors group-focus-within:text-indigo-400">
                    {icon}
                </div>
                <input
                    type={type}
                    required
                    value={value}
                    onChange={(event) => onChange(event.target.value)}
                    placeholder={placeholder}
                    className="w-full rounded-xl border border-white/10 bg-black/20 py-3.5 pl-12 pr-4 text-sm text-white outline-none transition-all placeholder:text-slate-600 focus:border-indigo-500/50"
                />
            </div>
        </label>
    );
}
