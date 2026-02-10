'use client'

import { useState, useTransition } from 'react'
import { UserProfile, BusinessProfile } from '@/types'
import { updateUserProfile, updateBusinessProfile } from '@/app/actions/profile'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar' // Assuming Avatar exists or I'll mock it
import { Loader2, Save, User, Building2 } from 'lucide-react'
// import { useToast } from '@/hooks/use-toast' // Assuming toast hook exists

// Mock Avatar if not present
const AvatarMock = ({ children, className }: any) => <div className={`rounded-full overflow-hidden ${className}`}>{children}</div>
const AvatarImageMock = ({ src }: any) => <img src={src} alt="Avatar" className="w-full h-full object-cover" />
const AvatarFallbackMock = ({ children }: any) => <div className="w-full h-full flex items-center justify-center bg-gray-100 text-gray-500">{children}</div>

export default function UserProfilePage({
    user,
    business
}: {
    user: UserProfile,
    business: BusinessProfile | null
}) {
    const [isPending, startTransition] = useTransition()
    // const { toast } = useToast() 

    // Local State
    const [formData, setFormData] = useState({
        full_name: user.full_name || '',
        whatsapp_number: user.whatsapp_number || '',
        company_name: business?.company_name || '',
        gstin: business?.gstin || '',
        auto_sync: business?.preferences?.auto_sync || false,
        notify_whatsapp: business?.preferences?.notify_whatsapp || false
    })

    const handleSave = () => {
        startTransition(async () => {
            try {
                // Update User
                await updateUserProfile(user.id, {
                    full_name: formData.full_name,
                    whatsapp_number: formData.whatsapp_number
                })

                // Update Business
                if (business) {
                    await updateBusinessProfile(user.id, {
                        company_name: formData.company_name,
                        gstin: formData.gstin,
                        preferences: {
                            auto_sync: formData.auto_sync,
                            notify_whatsapp: formData.notify_whatsapp
                        }
                    })
                }

                // toast({ title: "Success", description: "Profile updated successfully." })
                alert("Profile updated successfully.")
            } catch (error) {
                console.error(error)
                // toast({ title: "Error", description: "Failed to update profile.", variant: "destructive" })
                alert("Failed to update profile.")
            }
        })
    }

    return (
        <div className="grid gap-6 md:grid-cols-2 max-w-6xl mx-auto p-6">

            {/* Left Column: Personal Details */}
            <Card className="shadow-sm border-gray-200">
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <User className="w-5 h-5 text-blue-600" />
                        <CardTitle>Personal Details</CardTitle>
                    </div>
                    <CardDescription>Manage your personal information and contact details.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">

                    {/* Avatar Section */}
                    <div className="flex items-center gap-4">
                        <div className="h-20 w-20 rounded-full bg-gray-100 border-2 border-white shadow-md flex items-center justify-center overflow-hidden">
                            {user.avatar_url ? (
                                <img src={user.avatar_url} alt="Profile" className="w-full h-full object-cover" />
                            ) : (
                                <User className="w-8 h-8 text-gray-400" />
                            )}
                        </div>
                        <Button variant="outline" size="sm">Change Photo</Button>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="full_name">Full Name</Label>
                        <Input
                            id="full_name"
                            value={formData.full_name}
                            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                            placeholder="John Doe"
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="whatsapp">WhatsApp Number</Label>
                        <Input
                            id="whatsapp"
                            value={formData.whatsapp_number}
                            onChange={(e) => setFormData({ ...formData, whatsapp_number: e.target.value })}
                            placeholder="+91 98765 43210"
                        />
                        <p className="text-xs text-muted-foreground">Used for important notifications and updates.</p>
                    </div>

                </CardContent>
            </Card>

            {/* Right Column: Business Settings */}
            <Card className="shadow-sm border-gray-200">
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Building2 className="w-5 h-5 text-purple-600" />
                        <CardTitle>Business Settings</CardTitle>
                    </div>
                    <CardDescription>Configure your company details and preferences.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">

                    <div className="space-y-2">
                        <Label htmlFor="company_name">Company Name</Label>
                        <Input
                            id="company_name"
                            value={formData.company_name}
                            onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                            placeholder="Acme Corp"
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="gstin">GSTIN (Optional)</Label>
                        <Input
                            id="gstin"
                            value={formData.gstin}
                            onChange={(e) => setFormData({ ...formData, gstin: e.target.value })}
                            placeholder="22AAAAA0000A1Z5"
                            className="uppercase"
                        />
                    </div>

                    <div className="pt-4 space-y-4">
                        <h3 className="text-sm font-medium text-gray-900">Preferences</h3>

                        <div className="flex items-start space-x-3 p-3 border rounded-lg bg-gray-50/50">
                            <Checkbox
                                id="auto_sync"
                                checked={formData.auto_sync}
                                onCheckedChange={(checked) => setFormData({ ...formData, auto_sync: checked as boolean })}
                            />
                            <div className="grid gap-1.5 leading-none">
                                <Label htmlFor="auto_sync" className="font-medium">Auto-Sync with Tally</Label>
                                <p className="text-xs text-muted-foreground">
                                    Automatically sync vouchers every 15 minutes.
                                </p>
                            </div>
                        </div>

                        <div className="flex items-start space-x-3 p-3 border rounded-lg bg-gray-50/50">
                            <Checkbox
                                id="notify_whatsapp"
                                checked={formData.notify_whatsapp}
                                onCheckedChange={(checked) => setFormData({ ...formData, notify_whatsapp: checked as boolean })}
                            />
                            <div className="grid gap-1.5 leading-none">
                                <Label htmlFor="notify_whatsapp" className="font-medium">WhatsApp Notifications</Label>
                                <p className="text-xs text-muted-foreground">
                                    Receive daily summary reports on WhatsApp.
                                </p>
                            </div>
                        </div>
                    </div>

                </CardContent>
                <CardFooter className="flex justify-end pt-6">
                    <Button onClick={handleSave} disabled={isPending} className="w-full md:w-auto">
                        {isPending ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Saving...
                            </>
                        ) : (
                            <>
                                <Save className="mr-2 h-4 w-4" />
                                Save Changes
                            </>
                        )}
                    </Button>
                </CardFooter>
            </Card>
        </div>
    )
}
