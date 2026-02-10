"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, ArrowUpRight, CheckCircle2, Search, Zap } from "lucide-react";

export default function DesignSystemPage() {
    return (
        <div className="min-h-screen p-8 space-y-12 pb-24">
            <div className="space-y-4">
                <h1 className="text-4xl font-bold tracking-tight text-foreground">K24 Design System</h1>
                <p className="text-xl text-muted-foreground w-full max-w-2xl">
                    A production-grade UI kit for fintech dashboards. Clean, trustworthy, and data-driven.
                </p>
            </div>

            <hr className="border-border" />

            {/* Typography Section */}
            <section className="space-y-6">
                <h2 className="text-2xl font-semibold mb-6">Typography</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-4 p-6 bg-card rounded-lg border shadow-sm">
                        <h1 className="text-3xl font-bold">H1. Dashboard Title (32px)</h1>
                        <h2 className="text-2xl font-semibold">H2. Section Header (24px)</h2>
                        <h3 className="text-xl font-medium">H3. Card Title (20px)</h3>
                        <h4 className="text-lg font-medium">H4. Sub-section (18px)</h4>
                        <p className="text-base">Body. Default text for paragraphs and general content. (16px)</p>
                        <p className="text-sm text-muted-foreground">Caption. Used for secondary text, timestamps, or helper text. (14px)</p>
                        <p className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">Overline / Label</p>
                    </div>
                    <div className="space-y-4 p-6 bg-card rounded-lg border shadow-sm">
                        <div className="prose">
                            <p>
                                The typography system uses <span className="font-semibold">Inter</span>. It is optimized for readability
                                in data-dense interfaces. We use a high contrast ratio for essential text (neutral-900)
                                and softer greys (neutral-500) for secondary information.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Colors Section */}
            <section className="space-y-6">
                <h2 className="text-2xl font-semibold mb-6">Color Palette</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    <div className="space-y-2">
                        <div className="h-24 rounded-lg bg-primary shadow-sm flex items-end p-2">
                            <span className="text-primary-foreground text-xs font-medium">Primary</span>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <div className="h-24 rounded-lg bg-secondary shadow-sm flex items-end p-2">
                            <span className="text-secondary-foreground text-xs font-medium">Secondary (Sync/Live)</span>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <div className="h-24 rounded-lg bg-destructive shadow-sm flex items-end p-2">
                            <span className="text-destructive-foreground text-xs font-medium">Destructive</span>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <div className="h-24 rounded-lg bg-accent shadow-sm flex items-end p-2">
                            <span className="text-accent-foreground text-xs font-medium">Accent</span>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <div className="h-24 rounded-lg bg-muted shadow-sm flex items-end p-2">
                            <span className="text-muted-foreground text-xs font-medium">Muted</span>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <div className="h-24 rounded-lg bg-card border shadow-sm flex items-end p-2">
                            <span className="text-card-foreground text-xs font-medium">Card Surface</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* Components Section */}
            <section className="space-y-8">
                <h2 className="text-2xl font-semibold mb-6">Components</h2>

                {/* Buttons */}
                <div className="space-y-4">
                    <h3 className="text-lg font-medium">Buttons</h3>
                    <div className="flex flex-wrap gap-4">
                        <Button>Primary Action</Button>
                        <Button variant="secondary">Secondary Action</Button>
                        <Button variant="outline">Outline</Button>
                        <Button variant="ghost">Ghost</Button>
                        <Button variant="destructive">Destructive</Button>
                        <Button disabled>Disabled</Button>
                        <Button size="sm">Small</Button>
                        <Button size="icon"><Zap className="h-4 w-4" /></Button>
                    </div>
                </div>

                {/* Badges */}
                <div className="space-y-4">
                    <h3 className="text-lg font-medium">Status Pills / Badges</h3>
                    <div className="flex flex-wrap gap-4">
                        <Badge>Default Badge</Badge>
                        <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 hover:bg-emerald-200 border-emerald-200">
                            Paid / Synced
                        </Badge>
                        <Badge variant="destructive" className="bg-red-100 text-red-800 hover:bg-red-200 border-red-200">
                            Overdue
                        </Badge>
                        <Badge variant="outline" className="text-amber-700 border-amber-300 bg-amber-50">
                            Attention Needed
                        </Badge>
                        <Badge variant="outline" className="text-blue-700 border-blue-300 bg-blue-50">
                            Draft
                        </Badge>
                    </div>
                </div>

                {/* Cards & Stats */}
                <div className="space-y-4">
                    <h3 className="text-lg font-medium">Cards & KPI Tiles</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
                                <span className="text-muted-foreground">INR</span>
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">₹45,231.89</div>
                                <p className="text-xs text-muted-foreground mt-1 text-emerald-600 flex items-center">
                                    <ArrowUpRight className="h-3 w-3 mr-1" /> +20.1% from last month
                                </p>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Active Subscriptions</CardTitle>
                                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">+2350</div>
                                <p className="text-xs text-muted-foreground mt-1">
                                    +180 new this month
                                </p>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">Pending Invoices</CardTitle>
                                <AlertCircle className="h-4 w-4 text-amber-500" />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">12</div>
                                <p className="text-xs text-muted-foreground mt-1 text-amber-600 font-medium">
                                    Requires attention
                                </p>
                            </CardContent>
                        </Card>
                    </div>
                </div>

                {/* Table */}
                <div className="space-y-4">
                    <h3 className="text-lg font-medium">Data Tables</h3>
                    <Card>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-[100px]">Invoice</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Method</TableHead>
                                    <TableHead className="text-right">Amount</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                <TableRow>
                                    <TableCell className="font-medium">INV001</TableCell>
                                    <TableCell>
                                        <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 border-emerald-200">
                                            Paid
                                        </Badge>
                                    </TableCell>
                                    <TableCell>Credit Card</TableCell>
                                    <TableCell className="text-right">₹2,500.00</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell className="font-medium">INV002</TableCell>
                                    <TableCell>
                                        <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                                            Pending
                                        </Badge>
                                    </TableCell>
                                    <TableCell>PayPal</TableCell>
                                    <TableCell className="text-right">₹1,250.00</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell className="font-medium">INV003</TableCell>
                                    <TableCell>
                                        <Badge variant="destructive" className="bg-red-50 text-red-700 border-red-200">
                                            Overdue
                                        </Badge>
                                    </TableCell>
                                    <TableCell>Bank Transfer</TableCell>
                                    <TableCell className="text-right">₹4,500.00</TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    </Card>
                </div>

                {/* Form Inputs */}
                <div className="space-y-4">
                    <h3 className="text-lg font-medium">Forms</h3>
                    <Card className="p-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <Label htmlFor="email">Email Address</Label>
                                <Input type="email" id="email" placeholder="kiran@example.com" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="amount">Amount</Label>
                                <Input type="number" id="amount" placeholder="0.00" />
                            </div>
                            <div className="space-y-2">
                                <Label>Options</Label>
                                <div className="flex items-center space-x-2 border p-3 rounded-md bg-muted/20">
                                    <Checkbox id="terms" />
                                    <label
                                        htmlFor="terms"
                                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                    >
                                        Accept terms and conditions
                                    </label>
                                </div>
                            </div>
                        </div>
                    </Card>
                </div>

                {/* Alerts */}
                <div className="space-y-4">
                    <h3 className="text-lg font-medium">Alerts</h3>
                    <div className="space-y-4">
                        <Alert>
                            <Zap className="h-4 w-4" />
                            <AlertTitle>Heads up!</AlertTitle>
                            <AlertDescription>
                                You can add components to your app using the cli.
                            </AlertDescription>
                        </Alert>
                        <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertTitle>Error</AlertTitle>
                            <AlertDescription>
                                Your session has expired. Please log in again.
                            </AlertDescription>
                        </Alert>
                        <Alert variant="success">
                            <CheckCircle2 className="h-4 w-4" />
                            <AlertTitle>Success</AlertTitle>
                            <AlertDescription>
                                Your invoice has been generated.
                            </AlertDescription>
                        </Alert>
                        <Alert variant="warning">
                            <AlertCircle className="h-4 w-4" />
                            <AlertTitle>Warning</AlertTitle>
                            <AlertDescription>
                                Your subscription will expire in 3 days.
                            </AlertDescription>
                        </Alert>
                    </div>
                </div>

                {/* AI Chat Shell Example */}
                <div className="space-y-4">
                    <h3 className="text-lg font-medium">AI Chat Input</h3>
                    <Card className="p-4 bg-muted/30">
                        <div className="relative">
                            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input
                                className="pl-10 h-12 bg-background shadow-sm border-indigo-100 focus-visible:ring-indigo-500"
                                placeholder="Ask K24 about your sales data..."
                            />
                            <Button size="sm" className="absolute right-2 top-2">
                                Ask
                            </Button>
                        </div>
                    </Card>
                </div>

            </section>
        </div>
    );
}
