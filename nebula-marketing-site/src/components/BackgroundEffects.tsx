import { motion } from 'framer-motion';
import { useMemo } from 'react';

export const BackgroundEffects = () => {
    return (
        <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden select-none">
            <Starfield />
            <NeuralGrid />
            <NebulaMesh />
        </div>
    );
};

const Starfield = () => {
    const stars = useMemo(() => {
        return Array.from({ length: 80 }).map((_, i) => ({
            id: i,
            top: `${Math.random() * 100}%`,
            left: `${Math.random() * 100}%`,
            size: Math.random() * 2 + 1,
            delay: Math.random() * 5,
            duration: Math.random() * 3 + 2,
        }));
    }, []);

    return (
        <div className="absolute inset-0 z-0">
            {stars.map((star) => (
                <motion.div
                    key={star.id}
                    className="absolute bg-white rounded-full opacity-20"
                    style={{
                        top: star.top,
                        left: star.left,
                        width: star.size,
                        height: star.size,
                    }}
                    animate={{
                        opacity: [0.1, 0.4, 0.1],
                        scale: [1, 1.2, 1],
                    }}
                    transition={{
                        duration: star.duration,
                        repeat: Infinity,
                        delay: star.delay,
                        ease: "easeInOut",
                    }}
                />
            ))}
        </div>
    );
};

const NeuralGrid = () => {
    return (
        <div
            className="absolute inset-0 z-1"
            style={{
                backgroundImage: `linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px), 
                                 linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px)`,
                backgroundSize: '80px 80px',
                maskImage: 'radial-gradient(circle at center, black 0%, transparent 80%)'
            }}
        >
            <motion.div
                className="absolute inset-0 bg-gradient-to-br from-nebula-purple/5 to-transparent"
                animate={{
                    opacity: [0.3, 0.5, 0.3],
                }}
                transition={{
                    duration: 8,
                    repeat: Infinity,
                    ease: "linear"
                }}
            />
        </div>
    );
};

const NebulaMesh = () => {
    return (
        <div className="absolute inset-0 z-0 opacity-40">
            <motion.div
                className="absolute -top-[20%] -left-[10%] w-[60%] h-[60%] rounded-full bg-nebula-purple/20 blur-[120px]"
                animate={{
                    x: [0, 50, 0],
                    y: [0, 30, 0],
                    scale: [1, 1.1, 1],
                }}
                transition={{
                    duration: 15,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />
            <motion.div
                className="absolute -bottom-[10%] -right-[10%] w-[50%] h-[50%] rounded-full bg-nebula-blue/20 blur-[120px]"
                animate={{
                    x: [0, -40, 0],
                    y: [0, -20, 0],
                    scale: [1, 1.2, 1],
                }}
                transition={{
                    duration: 18,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />
            <motion.div
                className="absolute top-[20%] right-[20%] w-[40%] h-[40%] rounded-full bg-nebula-purple/10 blur-[100px]"
                animate={{
                    opacity: [0.3, 0.6, 0.3],
                    scale: [0.8, 1, 0.8],
                }}
                transition={{
                    duration: 12,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />
        </div>
    );
};
