import { type ReactNode, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import { Button } from './Button'

interface ModalProps {
    isOpen: boolean
    onClose: () => void
    title: string
    children: ReactNode
    footer?: ReactNode
}

export const Modal = ({ isOpen, onClose, title, children, footer }: ModalProps) => {
    // Prevent scroll when modal is open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden'
        } else {
            document.body.style.overflow = 'unset'
        }
        return () => {
            document.body.style.overflow = 'unset'
        }
    }, [isOpen])

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                    />

                    {/* Modal Content */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        transition={{ duration: 0.3, ease: 'easeOut' }}
                        className="relative w-full max-w-lg glass border border-white/10 rounded-[2rem] overflow-hidden shadow-2xl flex flex-col"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between p-6 border-b border-white/5">
                            <h3 className="text-xl font-bold text-white tracking-tight">{title}</h3>
                            <button
                                onClick={onClose}
                                className="p-2 rounded-full hover:bg-white/5 text-white/50 hover:text-white transition-colors"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        {/* Body */}
                        <div className="p-8 overflow-y-auto max-h-[70vh]">
                            {children}
                        </div>

                        {/* Footer */}
                        {footer && (
                            <div className="p-6 border-t border-white/5 flex justify-end gap-3 bg-white/5">
                                {footer}
                            </div>
                        ) || (
                                <div className="p-6 border-t border-white/5 flex justify-end bg-white/5">
                                    <Button variant="secondary" size="sm" onClick={onClose}>Close</Button>
                                </div>
                            )}
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    )
}
