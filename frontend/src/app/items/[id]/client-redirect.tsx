'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export function ClientRedirect() {
    const router = useRouter();
    useEffect(() => {
        router.replace('/items');
    }, [router]);
    return (
        <div className="flex h-screen items-center justify-center">
            <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
        </div>
    );
}
