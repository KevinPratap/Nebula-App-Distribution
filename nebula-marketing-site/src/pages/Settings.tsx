import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FadeIn } from '../components/Animations'
import { Button } from '../components/Button'
import { Modal } from '../components/Modal'
import { Save, User, Lock, Bell, Shield, CheckCircle2, AlertCircle } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { authService } from '../services/auth'
import { apiService } from '../services/api'

export default function Settings() {
    const { user, refreshUser } = useAuth()
    const [loading, setLoading] = useState(false)
    const [activeTab, setActiveTab] = useState('profile')

    // Modal States
    const [isPassModalOpen, setIsPassModalOpen] = useState(false)
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
    const [deleteConfirmation, setDeleteConfirmation] = useState('')

    // Status Feedback
    const [status, setStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null)

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setStatus(null)

        // Get form data
        const form = e.target as HTMLFormElement
        const displayNameInput = form.elements.namedItem('display_name') as HTMLInputElement

        if (displayNameInput && activeTab === 'profile') {
            const result = await authService.updateProfile(displayNameInput.value)
            if (result.success) {
                await refreshUser()
                setStatus({ type: 'success', message: "Profile updated successfully!" })
            } else {
                setStatus({ type: 'error', message: "Failed to update profile: " + result.error })
            }
        } else {
            setStatus({ type: 'success', message: "Settings saved! (Simulation)" })
        }

        setLoading(false)
        // Clear status after 3 seconds
        setTimeout(() => setStatus(null), 3000)
    }

    const handlePasswordChange = async () => {
        if (!newPassword || newPassword.length < 6) {
            setStatus({ type: 'error', message: "Password must be at least 6 characters." })
            return
        }
        if (newPassword !== confirmPassword) {
            setStatus({ type: 'error', message: "Passwords do not match." })
            return
        }

        setLoading(true)
        const result = await apiService.changePassword(newPassword)
        setLoading(false)

        if (!result.error) {
            setIsPassModalOpen(false)
            setNewPassword('')
            setConfirmPassword('')
            setStatus({ type: 'success', message: "Password updated successfully!" })
        } else {
            setStatus({ type: 'error', message: result.error || result.message })
        }

        setTimeout(() => setStatus(null), 3000)
    }

    const handleDeleteAccount = async () => {
        setLoading(true)
        const result = await apiService.deleteAccount()
        setLoading(false)

        if (!result.error) {
            // Logout and redirect is handled by server unsetting cookies, 
            // but we should clear local storage and redirect to be safe.
            localStorage.removeItem('nebula_user')
            window.location.href = '/'
        } else {
            setStatus({ type: 'error', message: result.error || "Failed to delete account" })
            setIsDeleteModalOpen(false)
        }
    }

    if (!user) return null

    return (
        <div className="min-h-screen pt-32 pb-20 px-6">
            <FadeIn>
                <div className="container mx-auto max-w-4xl">
                    <div className="flex justify-between items-end mb-10">
                        <div>
                            <h1 className="text-4xl font-bold mb-2">Account Settings</h1>
                            <p className="text-white/50">Manage your profile and preferences.</p>
                        </div>
                        <AnimatePresence>
                            {status && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, scale: 0.95 }}
                                    className={`flex items-center gap-2 px-4 py-2 rounded-2xl text-sm font-medium ${status.type === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'
                                        }`}
                                >
                                    {status.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                                    {status.message}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {/* Sidebar */}
                        <div className="md:col-span-1 space-y-2">
                            <SettingsTab
                                label="Profile"
                                icon={<User size={18} />}
                                active={activeTab === 'profile'}
                                onClick={() => setActiveTab('profile')}
                            />
                            <SettingsTab
                                label="Security"
                                icon={<Lock size={18} />}
                                active={activeTab === 'security'}
                                onClick={() => setActiveTab('security')}
                            />
                            <SettingsTab
                                label="Notifications"
                                icon={<Bell size={18} />}
                                active={activeTab === 'notifications'}
                                onClick={() => setActiveTab('notifications')}
                            />
                            <SettingsTab
                                label="Privacy"
                                icon={<Shield size={18} />}
                                active={activeTab === 'privacy'}
                                onClick={() => setActiveTab('privacy')}
                            />
                        </div>

                        {/* Content */}
                        <div className="md:col-span-2 glass p-8 rounded-3xl border border-white/10 min-h-[400px]">
                            <form onSubmit={handleSave} className="space-y-6">
                                {activeTab === 'profile' && (
                                    <FadeIn key="profile">
                                        <h2 className="text-2xl font-bold mb-6">Profile Information</h2>
                                        {/* Profile fields... */}
                                        <div className="space-y-2">
                                            <label className="text-sm font-medium text-white/70 ml-1">Display Name</label>
                                            <input
                                                type="text"
                                                name="display_name"
                                                defaultValue={user.display_name || ''}
                                                className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 px-4 text-white focus:outline-none focus:border-nebula-purple/50 transition-colors"
                                                placeholder="Enter your name"
                                            />
                                        </div>
                                        <div className="space-y-2 mt-4">
                                            <label className="text-sm font-medium text-white/70 ml-1">Email Address</label>
                                            <input
                                                type="email"
                                                defaultValue={user.email || ''}
                                                disabled
                                                className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 px-4 text-white/50 cursor-not-allowed"
                                            />
                                        </div>
                                    </FadeIn>
                                )}

                                {activeTab === 'security' && (
                                    <FadeIn key="security">
                                        <h2 className="text-2xl font-bold mb-6">Security Settings</h2>
                                        <div className="space-y-4">
                                            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 flex justify-between items-center transition-all hover:bg-white/10">
                                                <div>
                                                    <h3 className="font-bold">Two-Factor Authentication</h3>
                                                    <p className="text-sm text-white/50">Add an extra layer of security.</p>
                                                </div>
                                                <Button
                                                    type="button"
                                                    variant={user.two_factor_enabled ? "outline" : "secondary"}
                                                    size="sm"
                                                    onClick={async () => {
                                                        const result = await apiService.toggle2FA(!user.two_factor_enabled);
                                                        if (!result.error) {
                                                            await refreshUser();
                                                            setStatus({ type: 'success', message: result.message });
                                                        } else {
                                                            setStatus({ type: 'error', message: result.error || result.message });
                                                        }
                                                        setTimeout(() => setStatus(null), 3000);
                                                    }}
                                                >
                                                    {user.two_factor_enabled ? 'Disable' : 'Enable'}
                                                </Button>
                                            </div>
                                            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 flex justify-between items-center transition-all hover:bg-white/10">
                                                <div>
                                                    <h3 className="font-bold">Password</h3>
                                                    <p className="text-sm text-white/50">Update your account password.</p>
                                                </div>
                                                <Button
                                                    type="button"
                                                    variant="secondary"
                                                    size="sm"
                                                    onClick={() => setIsPassModalOpen(true)}
                                                >
                                                    Change
                                                </Button>
                                            </div>
                                        </div>
                                    </FadeIn>
                                )}

                                {activeTab === 'notifications' && (
                                    <FadeIn key="notifications">
                                        <h2 className="text-2xl font-bold mb-6">Notifications</h2>
                                        <div className="space-y-4">
                                            <label className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/5 cursor-pointer transition-colors">
                                                <input type="checkbox" defaultChecked className="accent-nebula-purple w-5 h-5 rounded" />
                                                <span className="text-white/80">Product updates and announcements</span>
                                            </label>
                                            <label className="flex items-center gap-3 p-3 rounded-xl hover:bg-white/5 cursor-pointer transition-colors">
                                                <input type="checkbox" defaultChecked className="accent-nebula-purple w-5 h-5 rounded" />
                                                <span className="text-white/80">Weekly meeting summaries</span>
                                            </label>
                                        </div>
                                    </FadeIn>
                                )}

                                {activeTab === 'privacy' && (
                                    <FadeIn key="privacy">
                                        <h2 className="text-2xl font-bold mb-6">Privacy Controls</h2>
                                        <div>
                                            <h3 className="text-lg font-bold mb-2">Data Usage</h3>
                                            <p className="text-sm text-white/50 leading-relaxed mb-4">
                                                We use your data strictly to improve your transcription accuracy. We do not sell your data to third parties.
                                            </p>
                                            <div className="pt-4 border-t border-white/5">
                                                <h3 className="text-red-400 font-bold mb-2 flex items-center gap-2">
                                                    <AlertCircle size={16} /> Danger Zone
                                                </h3>
                                                <p className="text-xs text-white/40 mb-4">
                                                    Permanently delete your account and all associated data. This action cannot be undone.
                                                </p>
                                                <Button
                                                    type="button"
                                                    variant="outline"
                                                    size="sm"
                                                    className="text-red-400 border-red-400/20 hover:bg-red-400/10"
                                                    onClick={() => setIsDeleteModalOpen(true)}
                                                >
                                                    Delete Account
                                                </Button>
                                            </div>
                                        </div>
                                    </FadeIn>
                                )}

                                {activeTab === 'profile' && (
                                    <div className="pt-6 border-t border-white/5 flex justify-end">
                                        <Button type="submit" disabled={loading}>
                                            {loading ? 'Saving...' : 'Save Changes'}
                                            <Save size={18} className="ml-2" />
                                        </Button>
                                    </div>
                                )}
                            </form>
                        </div>
                    </div>
                </div>
            </FadeIn>

            {/* Password Change Modal */}
            <Modal
                isOpen={isPassModalOpen}
                onClose={() => setIsPassModalOpen(false)}
                title="Update Password"
                footer={
                    <>
                        <Button variant="ghost" onClick={() => setIsPassModalOpen(false)}>Cancel</Button>
                        <Button onClick={handlePasswordChange} disabled={loading}>
                            {loading ? 'Updating...' : 'Update Password'}
                        </Button>
                    </>
                }
            >
                <div className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-white/70">New Password</label>
                        <input
                            type="password"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 px-4 text-white focus:outline-none focus:border-nebula-purple/50 transition-colors"
                            placeholder="Min 6 characters"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-white/70">Confirm Password</label>
                        <input
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 px-4 text-white focus:outline-none focus:border-nebula-purple/50 transition-colors"
                            placeholder="Repeat new password"
                        />
                    </div>
                </div>
            </Modal>

            {/* Account Deletion Confirmation Modal */}
            <Modal
                isOpen={isDeleteModalOpen}
                onClose={() => {
                    setIsDeleteModalOpen(false)
                    setDeleteConfirmation('')
                }}
                title="Delete Account?"
                footer={
                    <>
                        <Button variant="ghost" onClick={() => {
                            setIsDeleteModalOpen(false)
                            setDeleteConfirmation('')
                        }}>Cancel</Button>
                        <Button
                            className={`${deleteConfirmation === 'DELETE' ? 'bg-red-500 hover:bg-red-600' : 'bg-red-500/50 cursor-not-allowed'} text-white border-none`}
                            onClick={handleDeleteAccount}
                            disabled={loading || deleteConfirmation !== 'DELETE'}
                        >
                            {loading ? 'Deleting...' : 'Permanently Delete'}
                        </Button>
                    </>
                }
            >
                <div className="space-y-4">
                    <div className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                        <p className="font-bold flex items-center gap-2 mb-1">
                            <AlertCircle size={16} /> Warning: This is permanent
                        </p>
                        <p className="opacity-80">
                            Deleting your account will immediately remove all access to your Nebula credits and session history. This action cannot be reversed.
                        </p>
                    </div>

                    <div className="space-y-2">
                        <p className="text-sm text-white/60 px-1">
                            Type <span className="text-white font-bold">DELETE</span> below to confirm:
                        </p>
                        <input
                            type="text"
                            value={deleteConfirmation}
                            onChange={(e) => setDeleteConfirmation(e.target.value)}
                            className="w-full bg-white/5 border border-white/10 rounded-2xl py-3 px-4 text-white focus:outline-none focus:border-red-500/50 transition-colors placeholder:text-white/10"
                            placeholder="Type DELETE here"
                        />
                    </div>
                </div>
            </Modal>
        </div>
    )
}

function SettingsTab({ label, icon, active = false, onClick }: { label: string, icon: any, active?: boolean, onClick?: () => void }) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-medium transition-all ${active ? 'bg-nebula-purple/10 text-nebula-purple shadow-lg shadow-nebula-purple/10' : 'text-white/50 hover:bg-white/5 hover:text-white'
                }`}
        >
            {icon}
            {label}
        </button>
    )
}
