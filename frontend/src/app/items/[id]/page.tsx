import { ClientRedirect } from './client-redirect';

export async function generateStaticParams() {
    return [{ id: 'default' }];
}

export const dynamicParams = false;

export default function Page() {
    return <ClientRedirect />;
}
