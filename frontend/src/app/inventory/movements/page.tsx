'use client';

import React, { useEffect, useState } from 'react';
import { api } from "@/lib/api";
import { StockMovement } from '@/types/inventory';
import { StockMovementTable } from '@/components/inventory/StockMovementTable';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useToast } from "@/components/ui/use-toast";

export default function StockMovementsPage() {
    const router = useRouter();
    const { toast } = useToast();
    const [movements, setMovements] = useState<StockMovement[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchMovements = async () => {
        try {
            setLoading(true);
            const res = await api.get(`/api/inventory/movements/all?days=30`);
            if (res.ok) {
                const data = await res.json();
                setMovements(data.movements || []);
            } else {
                throw new Error("Failed to fetch movements");
            }
        } catch (e) {
            console.error(e);
            toast({
                title: "Error",
                description: "Failed to load movement logs.",
                variant: "destructive"
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMovements();
    }, []);

    return (
        <div className="flex flex-col space-y-6 md:p-8 p-4 pt-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="outline" size="icon" onClick={() => router.back()}>
                        <ArrowLeft className="h-4 w-4" />
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold">Global Stock Movements</h1>
                        <p className="text-muted-foreground">View all inventory transactions from the last 30 days.</p>
                    </div>
                </div>
                <Button variant="outline" size="sm" onClick={fetchMovements} disabled={loading}>
                    <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                </Button>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Movements Log</CardTitle>
                </CardHeader>
                <CardContent>
                    <StockMovementTable movements={movements} isLoading={loading} />
                </CardContent>
            </Card>
        </div>
    )
}
