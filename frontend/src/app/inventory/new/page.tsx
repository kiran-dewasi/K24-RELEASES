'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { ArrowLeft, Save } from 'lucide-react';
import { useToast } from "@/components/ui/use-toast";

export default function AddItemPage() {
    const router = useRouter();
    const { toast } = useToast();

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        toast({
            title: "Coming Soon",
            description: "Item creation via API is currently limited. Please create in Tally for now.",
        });
        // Logic to POST to /api/inventory would go here
    };

    return (
        <div className="flex flex-col space-y-6 md:p-8 p-4 pt-6 max-w-4xl mx-auto">
            <div className="flex items-center gap-4">
                <Button variant="outline" size="icon" onClick={() => router.back()}>
                    <ArrowLeft className="h-4 w-4" />
                </Button>
                <div>
                    <h1 className="text-2xl font-bold">Add New Item</h1>
                    <p className="text-muted-foreground">Create a new stock item in the inventory master.</p>
                </div>
            </div>

            <form onSubmit={handleSubmit}>
                <Card>
                    <CardHeader>
                        <CardTitle>Basic Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid gap-2">
                            <Label htmlFor="name">Item Name</Label>
                            <Input id="name" placeholder="e.g. Cotton Yarn 40s" required />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="grid gap-2">
                                <Label htmlFor="category">Category</Label>
                                <Select defaultValue="primary">
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select Category" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="primary">Primary</SelectItem>
                                        <SelectItem value="raw_material">Raw Materials</SelectItem>
                                        <SelectItem value="finished_goods">Finished Goods</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="grid gap-2">
                                <Label htmlFor="units">Units</Label>
                                <Select defaultValue="nos">
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select Unit" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="nos">Nos (Numbers)</SelectItem>
                                        <SelectItem value="kgs">Kgs (Kilograms)</SelectItem>
                                        <SelectItem value="mtr">Mtr (Meters)</SelectItem>
                                        <SelectItem value="box">Box</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="grid gap-2">
                            <Label htmlFor="desc">Description</Label>
                            <Textarea id="desc" placeholder="Item description, specifications..." />
                        </div>
                    </CardContent>

                    <div className="border-t p-6 bg-muted/10 md:rounded-b-lg flex justify-end gap-3">
                        <Button variant="ghost" type="button" onClick={() => router.back()}>Cancel</Button>
                        <Button type="submit">
                            <Save className="mr-2 h-4 w-4" /> Save Item
                        </Button>
                    </div>
                </Card>
            </form>
        </div>
    )
}
