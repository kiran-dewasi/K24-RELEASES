'use client';

import { useSearchParams, useRouter } from 'next/navigation';
import { Suspense } from 'react';
import { Loader2 } from 'lucide-react';
import ItemsListPage from './_list';
import Item360Page from '@/components/pages/InventoryItemPage';

function ItemsContent() {
    const searchParams = useSearchParams();
    const id = searchParams.get('id');
    // If ?id= present → show detail; otherwise → show list
    return id ? <Item360Page /> : <ItemsListPage />;
}

export default function Page() {
    return (
        <Suspense fallback={
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="animate-spin h-8 w-8 text-muted-foreground" />
            </div>
        }>
            <ItemsContent />
        </Suspense>
    );
}
