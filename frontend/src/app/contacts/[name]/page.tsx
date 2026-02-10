import ContactProfilePage from "@/components/pages/ContactProfilePage";

export async function generateStaticParams() {
    return [{ name: 'default' }];
}

export const dynamicParams = false;

export default function Page() {
    return <ContactProfilePage />;
}
