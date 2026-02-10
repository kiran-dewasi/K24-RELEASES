import ReportDetailPage from "@/components/pages/ReportDetailPage";

export async function generateStaticParams() {
    return [{ slug: 'default' }];
}

export const dynamicParams = false;

export default function Page() {
    return <ReportDetailPage />;
}
