export async function generateStaticParams() {
    return [{ id: 'default' }];
}

export const dynamicParams = false;

export default function Layout({ children }: { children: React.ReactNode }) {
    return children;
}
