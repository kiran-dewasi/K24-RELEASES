"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Mail, ArrowLeft, CheckCircle } from "lucide-react";
import Link from "next/link";

const CLOUD_API = "https://weare-production.up.railway.app";

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState("");
    const [loading, setLoading] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        try {
            const data = await fetch(`${CLOUD_API}/api/auth/forgot-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email }),
            });

            if (!data.ok) {
                const err = await data.json().catch(() => ({}));
                throw new Error(err.detail || "Request failed");
            }

            setSent(true);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Network error. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    if (sent) {
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
                            <h1 className="text-2xl font-bold text-gray-900 mb-2">Check Your Email</h1>
                            <p className="text-gray-500 mb-6">
                                We've sent a password reset link to <strong>{email}</strong>
                            </p>
                            <p className="text-sm text-gray-400 mb-6">
                                Didn't receive the email? Check your spam folder or try again.
                            </p>
                            <Link href="/login">
                                <Button variant="outline" className="w-full">
                                    <ArrowLeft className="w-4 h-4 mr-2" />
                                    Back to Login
                                </Button>
                            </Link>
                        </motion.div>
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
                        <Link href="/login" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                            <ArrowLeft className="w-4 h-4 mr-1" />
                            Back to Login
                        </Link>

                        <h1 className="text-2xl font-bold text-gray-900 mb-2">Forgot Password?</h1>
                        <p className="text-gray-500 mb-6">
                            Enter your email address and we'll send you a link to reset your password.
                        </p>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            {error && (
                                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                                    {error}
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium mb-2">Email Address</label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        placeholder="john@example.com"
                                        required
                                    />
                                </div>
                            </div>

                            <Button
                                type="submit"
                                disabled={loading}
                                className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                            >
                                {loading ? "Sending..." : "Send Reset Link"}
                            </Button>
                        </form>
                    </motion.div>
                </CardContent>
            </Card>
        </div>
    );
}
