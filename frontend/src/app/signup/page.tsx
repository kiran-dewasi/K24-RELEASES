"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Lock, Mail, User, Building, ArrowRight, CheckCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiRequest } from "@/lib/api";

export default function SignupPage() {
    const router = useRouter();
    const [formData, setFormData] = useState({
        full_name: "",
        company_name: "",
        username: "",
        email: "",
        password: ""
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        try {
            // Auto-generate username from email if empty (frontend convenience)
            const payload = {
                ...formData,
                username: formData.username || formData.email.split('@')[0]
            };

            console.log("IS TAURI:", typeof window !== 'undefined' && 
              !!(window as any).__TAURI_INTERNALS__)
            console.log("IS TAURI DEV:", process.env.NODE_ENV)
            console.log("CALLING URL:", process.env.NEXT_PUBLIC_BACKEND_URL)

            const data = await apiRequest("/api/auth/register", "POST", payload);

            // Auto-login logic
            if (data.access_token) {
                localStorage.setItem("k24_token", data.access_token);
                localStorage.setItem("k24_user", JSON.stringify(data.user));
                document.cookie = `k24_token=${data.access_token}; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;

                setSuccess(true);
                setTimeout(() => {
                    router.push("/daybook");
                }, 1500);
            } else {
                // If email verification is required (no token returned immediately)
                router.push("/login?registered=true");
            }

        } catch (err: any) {
            // Handle different error types properly
            let errorMessage = "Failed to create account";
            if (typeof err === 'string') {
                errorMessage = err;
            } else if (err?.message) {
                errorMessage = err.message;
            } else if (err?.detail) {
                errorMessage = err.detail;
            } else if (typeof err === 'object') {
                errorMessage = JSON.stringify(err);
            }
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4">
                <Card className="w-full max-w-md shadow-2xl p-8 text-center animate-in fade-in zoom-in duration-500">
                    <div className="flex justify-center mb-6">
                        <CheckCircle className="h-16 w-16 text-green-500 animate-bounce" />
                    </div>
                    <h2 className="text-2xl font-bold text-gray-800 mb-2">Account Created!</h2>
                    <p className="text-gray-500">Redirecting you to the dashboard...</p>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4">
            {/* Background decoration */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-0 right-0 w-96 h-96 bg-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
                <div className="absolute bottom-0 left-0 w-96 h-96 bg-blue-200 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
            </div>

            <Card className="w-full max-w-md shadow-2xl relative z-10">
                <CardContent className="p-8">
                    <motion.div
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-center mb-8"
                    >
                        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                            Join K24
                        </h1>
                        <p className="text-gray-500 mt-2">Create your intelligent financial assistant</p>
                    </motion.div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {error && (
                            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm animate-in slide-in-from-top-2">
                                {error}
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-medium mb-1 ml-1 text-gray-600">Full Name</label>
                                <div className="relative">
                                    <User className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                                    <input
                                        type="text"
                                        required
                                        className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        placeholder="John Doe"
                                        value={formData.full_name}
                                        onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1 ml-1 text-gray-600">Company</label>
                                <div className="relative">
                                    <Building className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                                    <input
                                        type="text"
                                        required
                                        className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        placeholder="Acme Inc."
                                        value={formData.company_name}
                                        onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                                    />
                                </div>
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs font-medium mb-1 ml-1 text-gray-600">Email Address</label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                                <input
                                    type="email"
                                    required
                                    className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="john@example.com"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs font-medium mb-1 ml-1 text-gray-600">Username</label>
                            <div className="relative">
                                <span className="absolute left-3 top-2.5 w-4 h-4 text-gray-400 text-xs font-mono">@</span>
                                <input
                                    type="text"
                                    className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="john_doe (optional)"
                                    value={formData.username}
                                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs font-medium mb-1 ml-1 text-gray-600">Password</label>
                            <div className="relative">
                                <Lock className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                                <input
                                    type="password"
                                    required
                                    className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="••••••••"
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                />
                            </div>
                        </div>

                        <Button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 mt-6"
                        >
                            {loading ? "Creating Account..." : "Create Account"}
                            {!loading && <ArrowRight className="w-4 h-4 ml-2" />}
                        </Button>
                    </form>

                    <div className="relative my-6">
                        <div className="absolute inset-0 flex items-center">
                            <div className="w-full border-t border-gray-200"></div>
                        </div>
                        <div className="relative flex justify-center text-xs">
                            <span className="px-2 bg-white text-gray-500">Already have an account?</span>
                        </div>
                    </div>

                    <Link href="/login">
                        <Button variant="outline" className="w-full text-sm">
                            Sign In
                        </Button>
                    </Link>

                    <p className="text-center text-[10px] text-gray-400 mt-6">
                        By creating an account, you agree to our Terms & Privacy Policy.
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
