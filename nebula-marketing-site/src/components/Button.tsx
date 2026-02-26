import { ReactNode } from 'react'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { motion } from 'framer-motion'

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'ghost' | 'outline'
    size?: 'sm' | 'md' | 'lg'
    children: ReactNode
}

export const Button = ({
    variant = 'primary',
    size = 'md',
    className,
    children,
    ...props
}: ButtonProps) => {
    const variants = {
        primary: 'bg-gradient-to-r from-nebula-purple to-nebula-deep text-white shadow-lg shadow-nebula-purple/20 transition-all hover:scale-[1.02] active:scale-95',
        secondary: 'bg-white/10 text-white backdrop-blur-md hover:bg-white/20 transition-all',
        ghost: 'bg-transparent text-nebula-purple hover:bg-nebula-purple/10 transition-all',
        outline: 'border border-nebula-purple/30 text-nebula-purple hover:bg-nebula-purple/5 transition-all'
    }

    const sizes = {
        sm: 'px-4 py-1.5 text-sm font-medium rounded-full',
        md: 'px-6 py-2.5 text-base font-semibold rounded-full',
        lg: 'px-8 py-3.5 text-lg font-bold rounded-full'
    }

    return (
        <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className={cn(
                'inline-flex items-center justify-center cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed',
                variants[variant],
                sizes[size],
                className
            )}
            {...props as any}
        >
            {children}
        </motion.button>
    )
}
