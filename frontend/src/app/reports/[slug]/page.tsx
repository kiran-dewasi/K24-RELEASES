import ReportDetailPage from "@/components/pages/ReportDetailPage";

export async function generateStaticParams() {
    return [
        { slug: 'default' },
        { slug: 'sales-register' },
        { slug: 'purchase-register' },
        { slug: 'cash-flow' },
        { slug: 'balance-sheet' },
        { slug: 'profit-loss' },
        { slug: 'gst-summary' },
    ];
}

export const dynamicParams = false;

export default function Page() {
    return <ReportDetailPage />;
}
