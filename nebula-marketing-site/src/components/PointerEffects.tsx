import { useEffect, useState } from 'react';
import { motion, useSpring } from 'framer-motion';

export const CursorFollower = () => {
    const [isPointer, setIsPointer] = useState(false);

    const mouseX = useSpring(0, { stiffness: 500, damping: 28 });
    const mouseY = useSpring(0, { stiffness: 500, damping: 28 });

    useEffect(() => {
        const handleMouseMove = (x: number, y: number, target: HTMLElement | null) => {
            mouseX.set(x);
            mouseY.set(y);

            if (!target) return;

            // Optimization: Avoid getComputedStyle which triggers layout reflow
            const isClickable = target.closest('button, a, [role="button"], input[type="submit"]');
            setIsPointer(!!isClickable);
        };

        const onMove = (e: MouseEvent) => handleMouseMove(e.clientX, e.clientY, e.target as HTMLElement);

        window.addEventListener('mousemove', onMove);
        return () => window.removeEventListener('mousemove', onMove);
    }, [mouseX, mouseY]);

    return (
        <>
            {/* Outer Circle */}
            <motion.div
                style={{
                    x: mouseX,
                    y: mouseY,
                    translateX: '-50%',
                    translateY: '-50%',
                }}
                className="fixed top-0 left-0 w-8 h-8 rounded-full border border-nebula-purple/50 pointer-events-none z-[9999] mix-blend-difference hidden md:block"
                animate={{
                    scale: isPointer ? 1.5 : 1,
                    backgroundColor: isPointer ? 'rgba(159, 122, 234, 0.2)' : 'rgba(159, 122, 234, 0)',
                }}
            />
            {/* Inner Dot for precision */}
            <motion.div
                style={{
                    x: mouseX,
                    y: mouseY,
                    translateX: '-50%',
                    translateY: '-50%',
                }}
                className="fixed top-0 left-0 w-1.5 h-1.5 rounded-full bg-white pointer-events-none z-[99999] hidden md:block"
                animate={{
                    scale: isPointer ? 0.5 : 1,
                }}
            />
        </>
    );
};
