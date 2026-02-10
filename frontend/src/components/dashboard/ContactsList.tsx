'use client'

import { useState, useEffect, useTransition } from 'react'
import { Contact } from '@/types'
import { getContacts, createContact, deleteContact } from '@/app/actions/contacts'
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from '@/components/ui/select' // Assuming Select exists
import { Search, Plus, Trash2, Loader2, ChevronLeft, ChevronRight } from 'lucide-react'

// Mock Select if not present (simple HTML select fallback inside the component if needed, but assuming shadcn)
// I'll assume standard HTML select for simplicity if shadcn Select is complex to mock without full file access

export default function ContactsList({ businessId }: { businessId: string }) {
    const [contacts, setContacts] = useState<Contact[]>([])
    const [loading, setLoading] = useState(true)
    const [search, setSearch] = useState('')
    const [page, setPage] = useState(1)
    const [totalCount, setTotalCount] = useState(0)
    const [isDialogOpen, setIsDialogOpen] = useState(false)
    const [isPending, startTransition] = useTransition()

    // New Contact Form State
    const [newContact, setNewContact] = useState({
        name: '',
        phone: '',
        type: 'Sundry Debtor' as 'Sundry Debtor' | 'Sundry Creditor',
        current_balance: 0,
        tally_ledger_name: ''
    })

    const fetchContacts = async () => {
        setLoading(true)
        try {
            const { data, count } = await getContacts(businessId, search, page)
            setContacts(data)
            setTotalCount(count || 0)
        } catch (error) {
            console.error(error)
        } finally {
            setLoading(false)
        }
    }

    // Debounce search
    useEffect(() => {
        const timer = setTimeout(() => {
            setPage(1) // Reset to page 1 on search
            fetchContacts()
        }, 500)
        return () => clearTimeout(timer)
    }, [search])

    // Fetch on page change
    useEffect(() => {
        fetchContacts()
    }, [page])

    const handleCreate = () => {
        startTransition(async () => {
            try {
                await createContact({
                    business_id: businessId,
                    ...newContact
                })
                setIsDialogOpen(false)
                setNewContact({ name: '', phone: '', type: 'Sundry Debtor', current_balance: 0, tally_ledger_name: '' })
                fetchContacts() // Refresh list
            } catch (error) {
                alert("Failed to create contact")
            }
        })
    }

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure you want to delete this contact?")) return
        try {
            await deleteContact(id)
            fetchContacts()
        } catch (error) {
            alert("Failed to delete contact")
        }
    }

    return (
        <div className="space-y-4 p-6 bg-white rounded-lg shadow-sm border border-gray-200">

            {/* Header & Actions */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="relative w-full sm:w-72">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search contacts..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="pl-8"
                    />
                </div>

                <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                    <DialogTrigger asChild>
                        <Button>
                            <Plus className="mr-2 h-4 w-4" />
                            Add Contact
                        </Button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Add New Contact</DialogTitle>
                            <DialogDescription>
                                Create a new customer or vendor profile.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="grid gap-4 py-4">
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="name" className="text-right">Name</Label>
                                <Input
                                    id="name"
                                    value={newContact.name}
                                    onChange={(e) => setNewContact({ ...newContact, name: e.target.value })}
                                    className="col-span-3"
                                />
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="phone" className="text-right">Phone</Label>
                                <Input
                                    id="phone"
                                    value={newContact.phone}
                                    onChange={(e) => setNewContact({ ...newContact, phone: e.target.value })}
                                    className="col-span-3"
                                />
                            </div>
                            <div className="grid grid-cols-4 items-center gap-4">
                                <Label htmlFor="type" className="text-right">Type</Label>
                                <select
                                    id="type"
                                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 col-span-3"
                                    value={newContact.type}
                                    onChange={(e) => setNewContact({ ...newContact, type: e.target.value as any })}
                                >
                                    <option value="Sundry Debtor">Sundry Debtor (Customer)</option>
                                    <option value="Sundry Creditor">Sundry Creditor (Vendor)</option>
                                </select>
                            </div>
                        </div>
                        <DialogFooter>
                            <Button onClick={handleCreate} disabled={isPending}>
                                {isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                                Create Contact
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>

            {/* Data Table */}
            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Name</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>Phone</TableHead>
                            <TableHead className="text-right">Balance</TableHead>
                            <TableHead className="w-[50px]"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {loading ? (
                            <TableRow>
                                <TableCell colSpan={5} className="h-24 text-center">
                                    <Loader2 className="mx-auto h-6 w-6 animate-spin text-gray-400" />
                                </TableCell>
                            </TableRow>
                        ) : contacts.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                                    No contacts yet. Create from Tally sync or add manually.
                                </TableCell>
                            </TableRow>
                        ) : (
                            contacts.map((contact) => (
                                <TableRow key={contact.id}>
                                    <TableCell className="font-medium">{contact.name}</TableCell>
                                    <TableCell>
                                        <Badge variant={contact.type === 'Sundry Debtor' ? 'default' : 'destructive'} className={contact.type === 'Sundry Debtor' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}>
                                            {contact.type === 'Sundry Debtor' ? 'Debtor' : 'Creditor'}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>{contact.phone || '-'}</TableCell>
                                    <TableCell className="text-right font-mono">
                                        ₹{(contact.current_balance ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                    </TableCell>
                                    <TableCell>
                                        <Button variant="ghost" size="icon" onClick={() => handleDelete(contact.id)}>
                                            <Trash2 className="h-4 w-4 text-gray-500 hover:text-red-600" />
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-2">
                <div className="text-sm text-muted-foreground">
                    Showing {contacts.length} of {totalCount} entries
                </div>
                <div className="flex items-center space-x-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1 || loading}
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <div className="text-sm font-medium">Page {page}</div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => p + 1)}
                        disabled={contacts.length < 10 || loading} // Simple check, ideally check totalCount
                    >
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                </div>
            </div>

        </div>
    )
}
