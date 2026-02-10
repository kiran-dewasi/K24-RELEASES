import Item360Page from "@/components/pages/InventoryItemPage";

export async function generateStaticParams() {
    return [{ id: 'default' }];
}

export const dynamicParams = false;

export default function Page() {
    return <Item360Page />;
}
