'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

/** Stub redirect — real item pages are at /items?id=... */
function RedirectPage() {
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

export async function generateStaticParams() {
    return [{ id: 'default' }];
}

export const dynamicParams = false;

export default function Page() {
    return <RedirectPage />;
}
