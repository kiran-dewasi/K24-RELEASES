import ReportDetailPage from "@/components/pages/ReportDetailPage";

export async function generateStaticParams() {
    return [
        { slug: 'sales-register' },
        { slug: 'purchase-register' },
        { slug: 'cash-flow' },
        { slug: 'balance-sheet' },
        { slug: 'profit-loss' },
        { slug: 'gst-summary' },
    ];
}

export const dynamicParams = false;

// In Next.js 15 App Router, params is a Promise — must be awaited in async server components.
export default async function Page({
    params,
}: {
    params: Promise<{ slug: string }>;
}) {
    const resolvedParams = await params;
    return <ReportDetailPage slug={resolvedParams.slug} />;
}
