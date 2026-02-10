import Customer360Page from "@/components/pages/Customer360Page";

export async function generateStaticParams() {
    return [{ id: 'default' }];
}

export const dynamicParams = false;

export default function Page() {
    return <Customer360Page />;
}
