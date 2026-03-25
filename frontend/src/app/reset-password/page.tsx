"use client";

import { useState, useEffect, Suspense } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Lock, CheckCircle, XCircle } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

const CLOUD_API = "https://weare-production.up.railway.app";

function ResetPasswordContent() {
    const router = useRouter();
    const searchParams = useSearchParams();

    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState("");

    // Get token from URL (Supabase adds it after email click)
    const accessToken = searchParams.get("access_token") || searchParams.get("token");

    useEffect(() => {
        if (!accessToken) {
            setError("Invalid or missing reset token. Please request a new password reset.");
        }
    }, [accessToken]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (password !== confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        if (password.length < 6) {
            setError("Password must be at least 6 characters");
            return;
        }

        setLoading(true);

        try {
            const data = await fetch(`${CLOUD_API}/api/auth/reset-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    token: accessToken,
                    new_password: password,
                }),
            });

            if (!data.ok) {
                const err = await data.json().catch(() => ({}));
                throw new Error(err.detail || "Request failed");
            }

            setSuccess(true);
            // Redirect to login after 3 seconds
            setTimeout(() => router.push("/login"), 3000);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Network error. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4">
                <Card className="w-full max-w-md shadow-2xl">
                    <CardContent className="p-8 text-center">
                        <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: "spring", stiffness: 200 }}
                        >
                            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                                <CheckCircle className="w-8 h-8 text-green-600" />
                            </div>
                            <h1 className="text-2xl font-bold text-gray-900 mb-2">Password Reset!</h1>
                            <p className="text-gray-500 mb-6">
                                Your password has been successfully reset. Redirecting to login...
                            </p>
                            <Link href="/login">
                                <Button className="w-full bg-gradient-to-r from-blue-600 to-purple-600">
                                    Go to Login
                                </Button>
                            </Link>
                        </motion.div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    if (!accessToken) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4">
                <Card className="w-full max-w-md shadow-2xl">
                    <CardContent className="p-8 text-center">
                        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
                            <XCircle className="w-8 h-8 text-red-600" />
                        </div>
                        <h1 className="text-2xl font-bold text-gray-900 mb-2">Invalid Link</h1>
                        <p className="text-gray-500 mb-6">
                            This password reset link is invalid or has expired.
                        </p>
                        <Link href="/forgot-password">
                            <Button className="w-full bg-gradient-to-r from-blue-600 to-purple-600">
                                Request New Link
                            </Button>
                        </Link>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4">
            <Card className="w-full max-w-md shadow-2xl">
                <CardContent className="p-8">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                    >
                        <h1 className="text-2xl font-bold text-gray-900 mb-2">Reset Your Password</h1>
                        <p className="text-gray-500 mb-6">
                            Enter your new password below.
                        </p>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            {error && (
                                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                                    {error}
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium mb-2">New Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                                    <input
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        placeholder="••••••••"
                                        required
                                        minLength={6}
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">Confirm Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                                    <input
                                        type="password"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        placeholder="••••••••"
                                        required
                                    />
                                </div>
                            </div>

                            <Button
                                type="submit"
                                disabled={loading}
                                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                            >
                                {loading ? "Resetting..." : "Reset Password"}
                            </Button>
                        </form>
                    </motion.div>
                </CardContent>
            </Card>
        </div>
    );
}

export default function ResetPasswordPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        }>
            <ResetPasswordContent />
        </Suspense>
    )
}
